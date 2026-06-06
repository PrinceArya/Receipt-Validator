import os
import sys
import asyncio
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Imports
from bill_parser.receipt_parser import ReceiptParser
from gst_validator.main import get_gst_details
from amount_calculator.validator import ReceiptMathematicalValidator
from bill_validator.validator import BillSynthesisValidator

async def run_pipeline_test(image_path: str):
    print("=========================================================")
    print(f" TESTING RECEIPT VALIDATION PIPELINE ON IMAGE")
    print(f" Path: {image_path}")
    print("=========================================================\n")

    if not os.path.exists(image_path):
        print(f"Error: Target receipt image not found at: {image_path}")
        return

    # STEP 1: Parse the receipt image using bill_parser
    print("Step 1: Parsing receipt image via bill_parser...")
    try:
        bill_parser_json = ReceiptParser.parse_image(image_path)
        print("\n--- [Step 1 Output] bill_parser_json ---")
        print(json.dumps(bill_parser_json, indent=2))
    except Exception as e:
        print(f"Step 1 Failed: {e}")
        return

    gst_number = bill_parser_json.get("gst_number")
    print(f"\nExtracted GSTIN: {repr(gst_number)}")

    # STEP 2 & 3: Run ClearTax scraper and Math Audit concurrently
    print("\nStep 2 & 3: Running GST Scraper and Mathematical validation in parallel...")
    
    async def get_gst_data(gstin):
        if not gstin or str(gstin).strip().lower() in ["null", "none", ""]:
            print("GSTIN is missing/null. Bypassing portal check.")
            return {"Registration Type": "Unregistered", "Business Name": "Unregistered"}
        try:
            return await get_gst_details(str(gstin))
        except Exception as e:
            print(f"GST Scraper failed: {e}")
            return {"Registration Type": "Unregistered", "Business Name": f"Unknown (Error: {str(e)})"}

    async def get_math_data(data):
        return ReceiptMathematicalValidator.validate_amounts(data)

    gst_validator_json, amount_calculator_json = await asyncio.gather(
        get_gst_data(gst_number),
        get_math_data(bill_parser_json)
    )

    print("\n--- [Step 2 Output] gst_validator_json ---")
    print(json.dumps(gst_validator_json, indent=2))

    print("\n--- [Step 3 Output] amount_calculator_json ---")
    print(json.dumps(amount_calculator_json, indent=2))

    # STEP 4: Synthesis Validation
    print("\nStep 4: Synthesizing results via bill_validator...")
    final_validation_json = BillSynthesisValidator.validate_bill(
        gst_validator_json,
        bill_parser_json,
        amount_calculator_json
    )

    print("\n--- [Step 4 Output] final_validation_json ---")
    print(json.dumps(final_validation_json, indent=2))
    print("=========================================================")

if __name__ == "__main__":
    target_image = r"D:\Project\Receipt_validator\temp_img\images_receipt.jpeg"
    asyncio.run(run_pipeline_test(target_image))
