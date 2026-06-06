import json
import sys
from receipt_parser import ReceiptParser

# Reconfigure stdout to use UTF-8 to prevent encoding errors on terminal outputs
sys.stdout.reconfigure(encoding='utf-8')

def main():
    image_path = r"D:\Project\Receipt_validator\temp_img\images_receipt.jpeg"
    print(f"Parsing receipt image: {image_path}...\n")
    
    try:
        result = ReceiptParser.parse_image(image_path)
        print("--- EXTRACTED DATA SCHEMA ---")
        print(json.dumps(result, indent=2))
        print("-----------------------------")
    except Exception as e:
        print(f"ERROR: Failed to parse receipt: {str(e)}")

if __name__ == "__main__":
    main()
