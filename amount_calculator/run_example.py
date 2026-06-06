import json
from validator import ReceiptMathematicalValidator

def run_example():
    # Sample receipt data matching the example in rules.md
    sample_receipt = {
        "total_amount": 1315.0,
        "bill_amount": 1381.0,
        "line_items": [
            {"description": "VEG MANCHAW SOUP", "qty": 1, "amount": 119.0},
            {"description": "VEG SWEET CORN SOUP", "qty": 1, "amount": 119.0},
            {"description": "DAL TADKA", "qty": 1, "amount": 215.0},
            {"description": "JEERA RICE", "qty": 1, "amount": 145.0},
            {"description": "PLAIN PAPAD", "qty": 2, "amount": 80.0},
            {"description": "BAKED VEG WITH VEG", "qty": 1, "amount": 270.0},
            {"description": "MUSHROOM MATTAR", "qty": 1, "amount": 265.0},
            {"description": "BUTTER TANDOORI ROTI", "qty": 1, "amount": 27.0},
            {"description": "MISSI ROTI", "qty": 1, "amount": 30.0},
            {"description": "GARLIC NAAN", "qty": 1, "amount": 45.0}
        ],
        "taxes": [
            {"tax_type": "CGST", "percentage": 2.5, "amount": 32.88},
            {"tax_type": "SGST", "percentage": 2.5, "amount": 32.88},
            {"tax_type": "CGST", "percentage": 2.5, "amount": 32.88}  # Duplicate CGST entry to test deduplication
        ]
    }

    print("--- SAMPLE EXTRACTED RECEIPT DATA ---")
    print(json.dumps(sample_receipt, indent=2))
    print("\nRunning validator...\n")

    # Run the validation
    audit_results = ReceiptMathematicalValidator.validate_amounts(sample_receipt)

    print("--- MATHEMATICAL AUDIT RESULTS ---")
    print(json.dumps(audit_results, indent=2))

if __name__ == "__main__":
    run_example()
