import os
import base64
import json
import mimetypes
from typing import List, Optional, Union
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator
from openai import OpenAI, APIError

# ==========================================
# Target JSON Schema Pydantic Definitions
# ==========================================

class LineItem(BaseModel):
    description: str = Field(description="Name/Item name")
    qty: Union[int, float] = Field(description="Quantity (integer or float)")
    amount: float = Field(description="Total price amount for this line item")

class TaxItem(BaseModel):
    tax_type: str = Field(description="Tax type (e.g. CGST, SGST, IGST)")
    percentage: float = Field(description="Tax percentage (e.g. 2.5)")
    amount: float = Field(description="Tax amount")

class ReceiptSchema(BaseModel):
    gst_number: Optional[str] = Field(None, description="GST number or null if not found/invalid")
    pan_number: Optional[str] = Field(None, description="PAN number extracted from characters 3-12 of valid GSTIN, or null")
    validation_errors: List[str] = Field(default_factory=list, description="Descriptive error flags if GSTIN structure is invalid")
    date: Optional[str] = Field(None, description="Receipt date (DD/MM/YYYY or normalized ISO format) or null")
    table_number: Union[str, int] = Field("NAN", description="Table number or 'NAN' if not available")
    line_items: List[LineItem] = Field(default_factory=list, description="List of line items")
    total_amount: float = Field(description="Subtotal before taxes")
    taxes: List[TaxItem] = Field(default_factory=list, description="List of taxes")
    bill_amount: float = Field(description="Final grand total payable")

    @field_validator('table_number', mode='before')
    @classmethod
    def validate_table_number(cls, v):
        if v is None:
            return "NAN"
        return v


# ==========================================
# Helper Function to Clean Markdown Fences
# ==========================================

def clean_json_string(text: str) -> str:
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


# ==========================================
# Core Parser Class
# ==========================================

class ReceiptParser:
    @classmethod
    def parse_image(cls, image_path: str) -> dict:
        """
        Accepts a receipt image file path, encodes it, calls OpenRouter using
        google/gemma-4-31b model, validates the output, and returns structured data.
        """
        # 1. Load dotenv and Validate Environment setup
        load_dotenv()
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("Environment setup failed: 'OPENROUTER_API_KEY' is missing in environment variables.")

        # Validate image file exists
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Receipt image file not found at: {image_path}")

        # 2. Image Ingestion & Base64 Encoding
        mime_type, _ = mimetypes.guess_type(image_path)
        if not mime_type:
            mime_type = "image/jpeg"

        with open(image_path, "rb") as f:
            base64_data = base64.b64encode(f.read()).decode("utf-8")

        # 3. OpenAI Client initialization with OpenRouter endpoint
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            timeout=90.0  # Provide generous timeout for multimodal reasoning
        )

        system_prompt = (
            "You are a precise document intelligence parser specializing in receipt scanning. "
            "You must return ONLY a valid JSON object matching the schema. Do not include any markdown fences, "
            "code blocks, or explanations."
        )

        schema_instruction = (
            "Extract the receipt details into a JSON object matching this exact schema:\n"
            "{\n"
            '  "gst_number": "string or null if not found (The raw 15-character GST number exactly as written on the receipt if present. Ensure you capture all 15 characters; do not truncate the final checksum character.)",\n'
            '  "date": "string (DD/MM/YYYY format or normalized ISO format) or null",\n'
            '  "table_number": "string, integer, or \'NAN\' if not available",\n'
            '  "line_items": [\n'
            "    {\n"
            '      "description": "string (Name/Item name)",\n'
            '      "qty": "integer or float",\n'
            '      "amount": "float"\n'
            "    }\n"
            "  ],\n"
            '  "total_amount": "float (Subtotal before taxes)",\n'
            '  "taxes": [\n'
            "    {\n"
            '      "tax_type": "string (e.g., CGST, SGST, IGST)",\n'
            '      "percentage": "float (e.g., 2.5)",\n'
            '      "amount": "float"\n'
            "    }\n"
            "  ],\n"
            '  "bill_amount": "float (Final grand total payable)"\n'
            "}\n"
            "Do not include any keys outside of this schema."
        )

        # 4. API Request & JSON Output Enforcement
        try:
            response = client.chat.completions.create(
                model="google/gemma-4-31b-it",
                response_format={"type": "json_object"},
                temperature=0.0,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": schema_instruction
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{base64_data}"
                                }
                            }
                        ]
                    }
                ]
            )

            raw_content = response.choices[0].message.content
            if not raw_content:
                raise ValueError("The AI model returned an empty response.")

            # Sanitization and JSON parsing
            clean_content = clean_json_string(raw_content)
            parsed_json = json.loads(clean_content)

            # Python-side GSTIN validation to avoid LLM hallucination
            raw_gst = parsed_json.get("gst_number")
            gst_clean = None
            pan_clean = None
            validation_errors = []

            # Handle case where model might return string representations of null/none/nan/not found
            if raw_gst and str(raw_gst).strip().lower() not in ["null", "none", "n/a", "nan", "not found", ""]:
                raw_gst_str = str(raw_gst)
                import re
                cleaned_gst = re.sub(r'[^a-zA-Z0-9]', '', raw_gst_str).upper()
                
                # Validation regex
                pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'
                if re.match(pattern, cleaned_gst):
                    state_code = cleaned_gst[0:2]
                    if state_code.isdigit() and (1 <= int(state_code) <= 37):
                        gst_clean = cleaned_gst
                        pan_clean = cleaned_gst[2:12]
                    else:
                        validation_errors.append("INVALID_STATE_CODE")
                else:
                    if len(cleaned_gst) != 15:
                        validation_errors.append("INVALID_GST_LENGTH")
                    elif len(cleaned_gst) > 13 and cleaned_gst[13] != 'Z':
                        validation_errors.append("MISSING_DEFAULT_Z_CHARACTER")
                    else:
                        validation_errors.append("INVALID_GST_STRUCTURE")
            
            # Apply validated values back to the parsed dict
            parsed_json["gst_number"] = gst_clean
            parsed_json["pan_number"] = pan_clean
            parsed_json["validation_errors"] = validation_errors

            # 5. Schema Validation & Normalization
            validated_receipt = ReceiptSchema(**parsed_json)
            return validated_receipt.model_dump()

        except APIError as ae:
            # Handle API timeouts, rate limits, bad gateway, etc.
            status_code = getattr(ae, "status_code", "unknown")
            raise RuntimeError(f"OpenRouter API Error (Status {status_code}): {ae.message}") from ae
        except json.JSONDecodeError as je:
            raise ValueError(f"Model output is not valid JSON. Raw output:\n{raw_content}") from je
        except Exception as e:
            raise RuntimeError(f"Failed to parse receipt image: {str(e)}") from e
