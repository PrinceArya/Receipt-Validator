from typing import Dict, Any, List

class BillSynthesisValidator:
    @staticmethod
    def validate_bill(
        gst_profile_json: Dict[str, Any],
        receipt_data_json: Dict[str, Any],
        math_audit_json: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluates GST profile registration type, receipt data, and math validation results
        to determine the final validity of the bill.
        
        Args:
            gst_profile_json (dict): Extracted GST portal data.
            receipt_data_json (dict): Extracted receipt data.
            math_audit_json (dict): Mathematical validation results.
            
        Returns:
            dict: Final decision JSON payload.
        """
        is_bill_valid = True
        status_message = "Bill is Valid."
        discrepancy_details = []

        # Check 1: The Math Tolerance Check
        # Calculate the absolute difference between mathematically derived total and the printed total
        audit = math_audit_json.get("audit_results", math_audit_json)
        calculated_bill_amount = float(audit.get("calculated_bill_amount") or 0.0)
        extracted_bill_amount = float(audit.get("extracted_bill_amount") or 0.0)

        if abs(calculated_bill_amount - extracted_bill_amount) > 5.0:
            is_bill_valid = False
            status_message = "Invalid Bill"
            discrepancy_details.append("Discrepancy in the Bill: Substantial mathematical mismatch between calculated items and extracted total.")
            return {
                "is_bill_valid": is_bill_valid,
                "status_message": status_message,
                "discrepancy_details": discrepancy_details
            }

        # Check 2: The Composition Scheme Fraud Check
        # A seller registered under the Composition/Composite scheme is legally barred from collecting GST
        registration_type = str(gst_profile_json.get("Registration Type") or "").strip().lower()
        if registration_type in ["composite", "composition"]:
            taxes = receipt_data_json.get("taxes", [])
            for tax in taxes:
                tax_type = str(tax.get("tax_type") or "").strip().upper()
                amount = float(tax.get("amount") or 0.0)
                if tax_type in ["CGST", "SGST", "IGST"] and amount > 0.0:
                    is_bill_valid = False
                    status_message = "Invalid Bill"
                    discrepancy_details.append("Discrepancy in the Bill: Illegal tax collection. Seller is under Composition scheme but charged GST.")
                    return {
                        "is_bill_valid": is_bill_valid,
                        "status_message": status_message,
                        "discrepancy_details": discrepancy_details
                    }

        # Check 3: GST validation / missing checks
        gst_number = receipt_data_json.get("gst_number")
        is_gst_missing = not gst_number or str(gst_number).strip().lower() in ["null", "none", "n/a", "nan", "not found", ""]
        
        taxes = receipt_data_json.get("taxes", [])
        has_cgst_sgst = False
        for tax in taxes:
            tax_type = str(tax.get("tax_type") or "").strip().upper()
            amount = float(tax.get("amount") or 0.0)
            if tax_type in ["CGST", "SGST", "IGST"] and amount > 0.0:
                has_cgst_sgst = True

        if is_gst_missing:
            if has_cgst_sgst:
                discrepancy_details.append("GST number is missing")
        else:
            # Check GST Structural Validity and Portal Registry
            validation_errors = receipt_data_json.get("validation_errors", [])
            is_gstin_valid_portal = gst_profile_json.get("is_gstin_valid", True)
            
            if validation_errors or not is_gstin_valid_portal:
                is_bill_valid = False
                status_message = "Invalid Bill"
                discrepancy_details.append("GST number is invalid")
                return {
                    "is_bill_valid": is_bill_valid,
                    "status_message": status_message,
                    "discrepancy_details": discrepancy_details
                }

        # Default Action: Valid Bill (or valid with missing GST warning)
        return {
            "is_bill_valid": is_bill_valid,
            "status_message": status_message,
            "discrepancy_details": discrepancy_details
        }
