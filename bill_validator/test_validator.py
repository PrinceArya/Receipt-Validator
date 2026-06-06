import unittest
from validator import BillSynthesisValidator

class TestBillSynthesisValidator(unittest.TestCase):
    def test_happy_path_valid_bill(self):
        # Valid math, regular taxpayer
        gst_profile = {"Registration Type": "Regular", "Business Name": "Test Business"}
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
        
        self.assertTrue(result["is_bill_valid"])
        self.assertEqual(result["status_message"], "Bill is Valid.")
        self.assertEqual(result["discrepancy_details"], [])

    def test_math_mismatch_fails_outside_five_rupees_tolerance(self):
        # Math mismatch > 5.0
        gst_profile = {"Registration Type": "Regular"}
        receipt_data = {"taxes": []}
        math_audit = {
            "calculated_bill_amount": 100.0,
            "extracted_bill_amount": 110.0  # diff = 10.0 > 5.0
        }

        result = BillSynthesisValidator.validate_bill(gst_profile, receipt_data, math_audit)
        
        self.assertFalse(result["is_bill_valid"])
        self.assertEqual(
            result["status_message"],
            "Invalid Bill"
        )
        self.assertEqual(len(result["discrepancy_details"]), 1)
        self.assertIn("Substantial mathematical mismatch", result["discrepancy_details"][0])

    def test_math_mismatch_passes_within_five_rupees_tolerance(self):
        # Math mismatch <= 5.0
        gst_profile = {"Registration Type": "Regular"}
        receipt_data = {"taxes": []}
        math_audit = {
            "calculated_bill_amount": 100.0,
            "extracted_bill_amount": 104.5  # diff = 4.5 <= 5.0
        }

        result = BillSynthesisValidator.validate_bill(gst_profile, receipt_data, math_audit)
        
        self.assertTrue(result["is_bill_valid"])
        self.assertEqual(result["status_message"], "Bill is Valid.")

    def test_composition_scheme_charging_gst_fails(self):
        # Composition scheme, CGST/SGST/IGST > 0 -> Invalid
        gst_profile = {"Registration Type": "Composite"}  # or "Composition"
        receipt_data = {
            "taxes": [
                {"tax_type": "CGST", "amount": 10.0},
                {"tax_type": "SGST", "amount": 10.0}
            ]
        }
        math_audit = {
            "calculated_bill_amount": 100.0,
            "extracted_bill_amount": 100.0
        }

        result = BillSynthesisValidator.validate_bill(gst_profile, receipt_data, math_audit)
        
        self.assertFalse(result["is_bill_valid"])
        self.assertEqual(
            result["status_message"],
            "Invalid Bill"
        )
        self.assertEqual(len(result["discrepancy_details"]), 1)
        self.assertIn("Illegal tax collection", result["discrepancy_details"][0])

    def test_composition_scheme_charging_zero_gst_passes(self):
        # Composition scheme, tax amount = 0 -> Valid
        gst_profile = {"Registration Type": "composition"}
        receipt_data = {
            "taxes": [
                {"tax_type": "CGST", "amount": 0.0},
                {"tax_type": "SGST", "amount": 0.0}
            ]
        }
        math_audit = {
            "calculated_bill_amount": 100.0,
            "extracted_bill_amount": 100.0
        }

        result = BillSynthesisValidator.validate_bill(gst_profile, receipt_data, math_audit)
        
        self.assertTrue(result["is_bill_valid"])
        self.assertEqual(result["status_message"], "Bill is Valid.")

if __name__ == "__main__":
    unittest.main()
