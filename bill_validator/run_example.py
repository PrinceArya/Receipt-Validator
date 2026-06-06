import json
from validator import BillSynthesisValidator

def run_scenarios():
    print("--- SCENARIO 1: Valid Bill (Regular Taxpayer, Math within Tolerance) ---")
    gst_profile = {"Registration Type": "Regular", "Business Name": "DineOut Cafe"}
    receipt_data = {
        "taxes": [
            {"tax_type": "CGST", "percentage": 2.5, "amount": 32.88},
            {"tax_type": "SGST", "percentage": 2.5, "amount": 32.88}
        ]
    }
    math_audit = {
        "calculated_bill_amount": 1380.76,
        "extracted_bill_amount": 1381.0
    }
    result = BillSynthesisValidator.validate_bill(gst_profile, receipt_data, math_audit)
    print(json.dumps(result, indent=2))

    print("\n--- SCENARIO 2: Math Discrepancy Failure (> 5.0 units) ---")
    gst_profile = {"Registration Type": "Regular"}
    receipt_data = {"taxes": []}
    math_audit = {
        "calculated_bill_amount": 100.0,
        "extracted_bill_amount": 106.5
    }
    result = BillSynthesisValidator.validate_bill(gst_profile, receipt_data, math_audit)
    print(json.dumps(result, indent=2))

    print("\n--- SCENARIO 3: Composition Scheme Tax Fraud ---")
    gst_profile = {"Registration Type": "Composition", "Business Name": "Local Store"}
    receipt_data = {
        "taxes": [
            {"tax_type": "CGST", "percentage": 2.5, "amount": 12.50}
        ]
    }
    math_audit = {
        "calculated_bill_amount": 512.50,
        "extracted_bill_amount": 512.50
    }
    result = BillSynthesisValidator.validate_bill(gst_profile, receipt_data, math_audit)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    run_scenarios()
