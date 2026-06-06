import math
from typing import List, Dict, Any, Optional

class ReceiptMathematicalValidator:
    @staticmethod
    def validate_amounts(receipt_data: Dict[str, Any], tolerance: float = 1.0) -> Dict[str, Any]:
        """
        Independently recalculates all subtotals, taxes, and grand totals,
        comparing them against extracted values to detect arithmetic anomalies.
        
        Args:
            receipt_data (dict): Parsed receipt JSON data.
            tolerance (float): Maximum absolute difference allowed for validation to remain valid.
            
        Returns:
            dict: JSON audit object matching the required schema.
        """
        # 1. Input parsing
        line_items = receipt_data.get("line_items", [])
        extracted_subtotal = float(receipt_data.get("total_amount") or 0.0)
        taxes = receipt_data.get("taxes", [])
        extracted_bill_amount = float(receipt_data.get("bill_amount") or 0.0)

        # 2. Calculate Base Subtotal
        # Formula: calculated_subtotal = Sum(item.amount for item in line_items)
        calculated_subtotal = 0.0
        for item in line_items:
            # Safely get item amount (prefer amount directly as per instruction)
            amount = float(item.get("amount") or 0.0)
            calculated_subtotal += amount
            
        # Round subtotal to 2 decimal places
        calculated_subtotal = round(calculated_subtotal, 2)

        # 3. Deduplicate and Calculate Taxes
        # Extract unique tax entries from the taxes array by tax_type (case-insensitive, trimmed)
        unique_taxes: Dict[str, Dict[str, Any]] = {}
        for tax in taxes:
            raw_tax_type = tax.get("tax_type")
            if not raw_tax_type:
                continue
            tax_type_clean = str(raw_tax_type).strip().upper()
            
            # If we haven't seen this tax type yet, store it
            if tax_type_clean not in unique_taxes:
                percentage = tax.get("percentage")
                if percentage is not None:
                    try:
                        percentage = float(percentage)
                    except (ValueError, TypeError):
                        percentage = None
                
                extracted_amount = float(tax.get("amount") or 0.0)
                unique_taxes[tax_type_clean] = {
                    "tax_type": tax_type_clean,
                    "percentage": percentage,
                    "extracted_amount": round(extracted_amount, 2)
                }

        # Calculate tax amounts on calculated_subtotal
        calculated_taxes_list = []
        total_calculated_tax = 0.0
        
        for tax_key in sorted(unique_taxes.keys()):
            tax_info = unique_taxes[tax_key]
            pct = tax_info["percentage"]
            
            # If percentage is null (None) or zero, use the absolute tax while computing the bill amount
            if pct is None or pct == 0.0:
                calc_tax_amount = tax_info["extracted_amount"]
            else:
                # Formula: calculated_tax_amount = calculated_subtotal * (percentage / 100)
                calc_tax_amount = calculated_subtotal * (pct / 100.0)
            
            calc_tax_amount = round(calc_tax_amount, 2)
            
            total_calculated_tax += calc_tax_amount
            
            calculated_taxes_list.append({
                "tax_type": tax_info["tax_type"],
                "calculated_amount": calc_tax_amount,
                "extracted_amount": tax_info["extracted_amount"]
            })

        # 4. Calculate Grand Total
        # Formula: calculated_bill_amount = calculated_subtotal + Sum(all unique calculated_tax_amounts)
        calculated_bill_amount = round(calculated_subtotal + total_calculated_tax, 2)

        # 5. Validation Check
        is_math_valid = True
        discrepancy_warnings = []

        # Validate Subtotal
        subtotal_diff = abs(calculated_subtotal - extracted_subtotal)
        if subtotal_diff > 0.001:
            if subtotal_diff <= tolerance:
                discrepancy_warnings.append(
                    f"Rounding discrepancy in subtotal: calculated {calculated_subtotal:.2f}, "
                    f"extracted {extracted_subtotal:.2f} (difference {subtotal_diff:.2f} <= {tolerance})"
                )
            else:
                is_math_valid = False
                discrepancy_warnings.append(
                    f"Math mismatch in subtotal: calculated {calculated_subtotal:.2f}, "
                    f"extracted {extracted_subtotal:.2f} (difference {subtotal_diff:.2f} > {tolerance})"
                )

        # Validate Tax Amounts
        for calc_tax in calculated_taxes_list:
            tax_type = calc_tax["tax_type"]
            calc_amt = calc_tax["calculated_amount"]
            ext_amt = calc_tax["extracted_amount"]
            tax_diff = abs(calc_amt - ext_amt)
            if tax_diff > 0.001:
                if tax_diff <= tolerance:
                    discrepancy_warnings.append(
                        f"Rounding discrepancy in tax {tax_type}: calculated {calc_amt:.2f}, "
                        f"extracted {ext_amt:.2f} (difference {tax_diff:.2f} <= {tolerance})"
                    )
                else:
                    is_math_valid = False
                    discrepancy_warnings.append(
                        f"Math mismatch in tax {tax_type}: calculated {calc_amt:.2f}, "
                        f"extracted {ext_amt:.2f} (difference {tax_diff:.2f} > {tolerance})"
                    )

        # Validate Grand Total (Bill Amount)
        bill_diff = abs(calculated_bill_amount - extracted_bill_amount)
        if bill_diff > 0.001:
            if bill_diff <= tolerance:
                discrepancy_warnings.append(
                    f"Rounding discrepancy in bill amount: calculated {calculated_bill_amount:.2f}, "
                    f"extracted {extracted_bill_amount:.2f} (difference {bill_diff:.2f} <= {tolerance})"
                )
            else:
                is_math_valid = False
                discrepancy_warnings.append(
                    f"Math mismatch in bill amount: calculated {calculated_bill_amount:.2f}, "
                    f"extracted {extracted_bill_amount:.2f} (difference {bill_diff:.2f} > {tolerance})"
                )

        return {
            "audit_results": {
                "calculated_subtotal": calculated_subtotal,
                "extracted_subtotal": extracted_subtotal,
                "calculated_taxes": calculated_taxes_list,
                "calculated_bill_amount": calculated_bill_amount,
                "extracted_bill_amount": extracted_bill_amount,
                "is_math_valid": is_math_valid,
                "discrepancy_warnings": discrepancy_warnings
            }
        }
