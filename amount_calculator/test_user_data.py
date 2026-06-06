import json
from validator import ReceiptMathematicalValidator

def test_user_data():
    user_receipt = {
        "gst_number": "23AABFH6030L1ZN",
        "pan_number": "AABFH6030L",
        "validation_errors": [],
        "date": "24/07/2021",
        "table_number": "34",
        "line_items": [
            {"description": "VEG MANCHAW SO", "qty": 1, "amount": 119.0},
            {"description": "VEG SWEET CORN", "qty": 1, "amount": 119.0},
            {"description": "DAL TADKA", "qty": 1, "amount": 215.0},
            {"description": "JEERA RICE", "qty": 1, "amount": 145.0},
            {"description": "PLAIN PAPAD", "qty": 2, "amount": 80.0},
            {"description": "BAKED VEG WITH", "qty": 1, "amount": 270.0},
            {"description": "MUSHROOM MATTA", "qty": 1, "amount": 265.0},
            {"description": "BUTTER TANDOOR", "qty": 1, "amount": 27.0},
            {"description": "MISSI ROTI", "qty": 1, "amount": 30.0},
            {"description": "GARLIC NAAN", "qty": 1, "amount": 45.0}
        ],
        "total_amount": 1315.0,
        "taxes": [
            {"tax_type": "CGST", "percentage": 2.5, "amount": 32.88},
            {"tax_type": "SGST", "percentage": 2.5, "amount": 32.88}
        ],
        "bill_amount": 1381.0
    }

    # Run the validation
    audit_results = ReceiptMathematicalValidator.validate_amounts(user_receipt)

    print("--- MATHEMATICAL AUDIT RESULTS ---")
    print(json.dumps(audit_results, indent=2))

if __name__ == "__main__":
    test_user_data()
