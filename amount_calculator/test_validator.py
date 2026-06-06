import unittest
from validator import ReceiptMathematicalValidator

class TestReceiptMathematicalValidator(unittest.TestCase):
    def test_standard_math_validation_valid_with_rounding(self):
        # Test case matching the exact example in the rules.md
        receipt_data = {
            "total_amount": 1315.0,
            "bill_amount": 1381.0,
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
            "taxes": [
                {"tax_type": "CGST", "percentage": 2.5, "amount": 32.88},
                {"tax_type": "SGST", "percentage": 2.5, "amount": 32.88}
            ]
        }
        
        result = ReceiptMathematicalValidator.validate_amounts(receipt_data)
        audit = result["audit_results"]
        
        self.assertEqual(audit["calculated_subtotal"], 1315.0)
        self.assertEqual(audit["extracted_subtotal"], 1315.0)
        self.assertEqual(audit["calculated_bill_amount"], 1380.76)
        self.assertEqual(audit["extracted_bill_amount"], 1381.0)
        self.assertTrue(audit["is_math_valid"])
        self.assertEqual(len(audit["discrepancy_warnings"]), 1)
        self.assertIn("Rounding discrepancy in bill amount", audit["discrepancy_warnings"][0])

    def test_tax_deduplication(self):
        # Receipt contains duplicate tax rows (e.g., duplicate SGST entries)
        receipt_data = {
            "total_amount": 100.0,
            "bill_amount": 105.0,
            "line_items": [
                {"qty": 1, "amount": 100.0}
            ],
            "taxes": [
                {"tax_type": "CGST", "percentage": 2.5, "amount": 2.5},
                {"tax_type": "SGST", "percentage": 2.5, "amount": 2.5},
                {"tax_type": "SGST", "percentage": 2.5, "amount": 2.5}  # Duplicate entry
            ]
        }
        
        result = ReceiptMathematicalValidator.validate_amounts(receipt_data)
        audit = result["audit_results"]
        
        # We should only have one CGST and one SGST entry
        self.assertEqual(len(audit["calculated_taxes"]), 2)
        tax_types = [t["tax_type"] for t in audit["calculated_taxes"]]
        self.assertIn("CGST", tax_types)
        self.assertIn("SGST", tax_types)
        self.assertEqual(audit["calculated_bill_amount"], 105.0)
        self.assertTrue(audit["is_math_valid"])
        self.assertEqual(len(audit["discrepancy_warnings"]), 0)

    def test_math_validation_invalid_outside_tolerance(self):
        # Case where math discrepancy is larger than 1.0 tolerance
        receipt_data = {
            "total_amount": 100.0,
            "bill_amount": 120.0,  # Extracted is way off
            "line_items": [
                {"qty": 1, "amount": 100.0}
            ],
            "taxes": [
                {"tax_type": "CGST", "percentage": 2.5, "amount": 2.5},
                {"tax_type": "SGST", "percentage": 2.5, "amount": 2.5}
            ]
        }
        
        result = ReceiptMathematicalValidator.validate_amounts(receipt_data)
        audit = result["audit_results"]
        
        self.assertEqual(audit["calculated_bill_amount"], 105.0)
        self.assertEqual(audit["extracted_bill_amount"], 120.0)
        self.assertFalse(audit["is_math_valid"])
        self.assertEqual(len(audit["discrepancy_warnings"]), 1)
        self.assertIn("Math mismatch in bill amount", audit["discrepancy_warnings"][0])

    def test_math_validation_with_missing_fields(self):
        # Zero defaults for empty inputs
        receipt_data = {}
        result = ReceiptMathematicalValidator.validate_amounts(receipt_data)
        audit = result["audit_results"]
        
        self.assertEqual(audit["calculated_subtotal"], 0.0)
        self.assertEqual(audit["calculated_bill_amount"], 0.0)
        self.assertTrue(audit["is_math_valid"])
        self.assertEqual(len(audit["discrepancy_warnings"]), 0)

if __name__ == "__main__":
    unittest.main()
