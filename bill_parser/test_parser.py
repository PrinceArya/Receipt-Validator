import os
import sys
from PIL import Image, ImageDraw
from receipt_parser import ReceiptParser

# Reconfigure stdout to use utf-8
sys.stdout.reconfigure(encoding='utf-8')

def create_mock_receipt_image(path: str):
    """
    Creates a simple mock receipt image programmatically using Pillow.
    """
    print(f"Generating mock receipt image at: {path}")
    # Create white canvas
    img = Image.new("RGB", (500, 400), color="white")
    draw = ImageDraw.Draw(img)
    
    # Draw receipt lines
    text_lines = [
        "==================================",
        "          MOCK RESTAURANT         ",
        "==================================",
        "GSTIN: 29AAAAP0267H1ZK",
        "Date: 06/06/2026",
        "Table No: 5",
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
        
    img.save(path)
    print("Mock receipt image created successfully.")

def test_missing_api_key():
    print("\n--- Running Test: Missing API Key ---")
    # Rename .env temporarily so load_dotenv() doesn't reload it
    env_exists = os.path.exists(".env")
    if env_exists:
        os.rename(".env", ".env.bak")
        
    parent_env_exists = os.path.exists("../.env")
    if parent_env_exists:
        os.rename("../.env", "../.env.bak")
        
    # Backup original key
    original_key = os.environ.get("OPENROUTER_API_KEY")
    if "OPENROUTER_API_KEY" in os.environ:
        del os.environ["OPENROUTER_API_KEY"]
        
    try:
        ReceiptParser.parse_image("non_existent_file.jpg")
        print("ERROR: Expected ValueError for missing API key, but none was raised.")
        return False
    except ValueError as ve:
        print(f"SUCCESS: Got expected ValueError: {ve}")
        return True
    except Exception as e:
        print(f"ERROR: Got unexpected exception: {type(e).__name__}: {e}")
        return False
    finally:
        # Restore key
        if original_key is not None:
            os.environ["OPENROUTER_API_KEY"] = original_key
        # Restore .env
        if env_exists and os.path.exists(".env.bak"):
            os.rename(".env.bak", ".env")
        if parent_env_exists and os.path.exists("../.env.bak"):
            os.rename("../.env.bak", "../.env")

def test_missing_image_file():
    print("\n--- Running Test: Missing Image File ---")
    try:
        ReceiptParser.parse_image("this_file_does_not_exist_xyz.jpg")
        print("ERROR: Expected FileNotFoundError for missing image, but none was raised.")
        return False
    except FileNotFoundError as fnf:
        print(f"SUCCESS: Got expected FileNotFoundError: {fnf}")
        return True

def test_integration():
    print("\n--- Running Test: Integration Parsing ---")
    mock_image_path = "mock_receipt.jpg"
    create_mock_receipt_image(mock_image_path)
    
    try:
        result = ReceiptParser.parse_image(mock_image_path)
        print("\nExtracted Data Schema:")
        import json
        print(json.dumps(result, indent=2))
        
        # Verify schema keys
        required_keys = ["gst_number", "date", "table_number", "line_items", "total_amount", "taxes", "bill_amount"]
        keys_ok = all(k in result for k in required_keys)
        if not keys_ok:
            print("ERROR: Extracted dictionary is missing required keys.")
            return False
            
        print("SUCCESS: JSON schema validated successfully.")
        return True
    except Exception as e:
        print(f"ERROR: End-to-end integration failed: {str(e)}")
        return False
    finally:
        # Clean up mock file
        if os.path.exists(mock_image_path):
            os.remove(mock_image_path)
            print(f"Cleaned up mock receipt image: {mock_image_path}")

def run_all_tests():
    success = True
    success &= test_missing_api_key()
    success &= test_missing_image_file()
    success &= test_integration()
    
    if success:
        print("\nALL TESTS PASSED SUCCESSFULLY!")
        sys.exit(0)
    else:
        print("\nSOME TESTS FAILED.")
        sys.exit(1)

if __name__ == "__main__":
    run_all_tests()
