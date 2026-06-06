import os
import sys
import asyncio
from typing import Dict, Any

# Playwright on Windows requires ProactorEventLoop to manage browser subprocesses
if sys.platform == 'win32':
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except AttributeError:
        pass

# Ensure packages can be imported correctly from the current workspace root
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Imports from existing directories
try:
    from bill_parser.receipt_parser import ReceiptParser
    from gst_validator.main import get_gst_details
    from amount_calculator.validator import ReceiptMathematicalValidator
    from bill_validator.validator import BillSynthesisValidator
except ImportError as ie:
    # Handle import errors gracefully if running from a different context
    print(f"Import Error: {ie}")
    raise

async def process_receipt(image_path: str) -> dict:
    """
    Wires together bill_parser, gst_validator, amount_calculator, and bill_validator
    into a single, high-performance, asynchronous pipeline.
    
    Args:
        image_path (str): Absolute or relative path to the receipt image.
        
    Returns:
        dict: Final synthesis JSON payload or error payload.
    """
    try:
        # Step 1: Image Parsing (Sequential)
        try:
            # ReceiptParser.parse_image is synchronous, so we run it in an executor or call directly
            # Since it makes external network calls, running in executor keeps the event loop non-blocking
            loop = asyncio.get_running_loop()
            bill_parser_json = await loop.run_in_executor(None, ReceiptParser.parse_image, image_path)
            
            if not bill_parser_json or not isinstance(bill_parser_json, dict):
                return {
                    "is_bill_valid": False,
                    "status_message": "Discrepancy in the Bill: Image parsing returned empty or invalid schema.",
                    "discrepancy_details": ["Image parsing failed or returned empty JSON object."]
                }
        except Exception as e:
            # If the parser throws an error, halt execution and return a failure payload immediately
            return {
                "is_bill_valid": False,
                "status_message": f"Discrepancy in the Bill: Image parsing failed. Error: {str(e)}",
                "discrepancy_details": [f"Image parsing failed: {str(e)}"]
            }

        # Extract the gst_number from the parsed JSON
        gst_number = bill_parser_json.get("gst_number")

        # Step 2 & Step 3: API Call and Math Audit (Parallel Execution)
        # Use asyncio.gather to run the GST validation and the math computation concurrently.
        
        async def run_gst_validation(gstin: Any) -> dict:
            # Edge Case: If gst_number is null or missing, bypass the GST API call
            if not gstin or str(gstin).strip().lower() in ["null", "none", "n/a", "nan", ""]:
                return {
                    "Registration Type": "Unregistered",
                    "Business Name": "Unregistered",
                    "PAN": gstin[2:12].upper() if (gstin and len(str(gstin)) >= 12) else None
                }
            
            # Otherwise, call clear tax API wrapper from gst_validator
            try:
                return await get_gst_details(str(gstin))
            except Exception as e:
                # If API call fails (portal down, invalid GSTIN, scraper error), fallback gracefully
                # to a default Unregistered/Unknown payload so the pipeline does not completely halt
                return {
                    "Registration Type": "Unregistered",
                    "Business Name": f"Unknown (GST API Error: {str(e)})",
                    "PAN": str(gstin)[2:12].upper() if len(str(gstin)) >= 12 else None
                }

        async def run_math_audit(data: dict) -> dict:
            # Run the mathematical verification module (synchronous computation)
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, ReceiptMathematicalValidator.validate_amounts, data)

        # Run both tasks concurrently without blocking each other
        gst_validator_json, amount_calculator_json = await asyncio.gather(
            run_gst_validation(gst_number),
            run_math_audit(bill_parser_json)
        )

        # Step 4: Final Synthesis (Sequential)
        final_validation_json = BillSynthesisValidator.validate_bill(
            gst_validator_json,
            bill_parser_json,
            amount_calculator_json
        )

        return final_validation_json

    except Exception as e:
        # Standardized HTTP 500 equivalent JSON error response if the pipeline breaks unexpectedly
        return {
            "status_code": 500,
            "error": "Internal Server Error",
            "message": f"Unexpected pipeline failure: {str(e)}",
            "details": {
                "type": type(e).__name__,
                "description": str(e)
            }
        }

if __name__ == "__main__":
    # Test the pipeline with a sample image path
    test_image = r"D:\Project\Receipt_validator\temp_img\images_receipt.jpeg"
    
    if not os.path.exists(test_image):
        print(f"Warning: Test image not found at {test_image}. Please make sure the image exists to test.")
        # Try to find mock receipt from test suite
        test_image = "mock_receipt_orchestrator.jpg"
        from amount_calculator.test_validator import TestReceiptMathematicalValidator
        # Create a mock receipt image programmatically for test
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (500, 400), color="white")
        draw = ImageDraw.Draw(img)
        text_lines = [
            "==================================",
            "          MOCK RESTAURANT         ",
            "==================================",
            "GSTIN: 23AABFH6030L1ZN",
            "Date: 24/07/2021",
            "Table No: 34",
            "----------------------------------",
            "Item          Qty       Amount    ",
            "----------------------------------",
            "Masala Dosa   2.0       120.00    ",
            "Filter Coffee 1.0        30.00    ",
            "----------------------------------",
            "Subtotal:               150.00    ",
            "CGST 2.5%:                3.75    ",
            "SGST 2.5%:                3.75    ",
            "----------------------------------",
            "Total Payable:          157.50    ",
            "=================================="
        ]
        y = 10
        for line in text_lines:
            draw.text((20, y), line, fill="black")
            y += 20
        img.save(test_image)
        print(f"Created programmatically mock receipt image at: {test_image}")

    print(f"Starting pipeline execution for receipt image: {test_image}...\n")
    
    result = asyncio.run(process_receipt(test_image))
    
    print("\n--- FINAL SYNTHESIS PIPELINE RESULT ---")
    import json
    print(json.dumps(result, indent=2))
    print("---------------------------------------")
    
    # Cleanup mock if generated
    if os.path.exists("mock_receipt_orchestrator.jpg"):
        os.remove("mock_receipt_orchestrator.jpg")
