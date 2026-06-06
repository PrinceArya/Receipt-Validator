import unittest
import asyncio
from unittest.mock import patch, MagicMock
from main import process_receipt

class TestOrchestratorPipeline(unittest.TestCase):
    def setUp(self):
        # Configure standard event loop policies for asyncio testing if needed
        self.loop = asyncio.get_event_loop()

    @patch("main.ReceiptParser.parse_image")
    @patch("main.get_gst_details")
    @patch("main.ReceiptMathematicalValidator.validate_amounts")
    @patch("main.BillSynthesisValidator.validate_bill")
    def test_pipeline_happy_path(self, mock_validate_bill, mock_validate_amounts, mock_get_gst_details, mock_parse_image):
        # Setup mocks
        mock_parse_image.return_value = {
            "gst_number": "23AABFH6030L1ZN",
            "date": "24/07/2021",
            "table_number": "34"
        }
        
        async def mock_gst_api(gstin):
            return {"Registration Type": "Regular", "Business Name": "DineOut Cafe"}
        mock_get_gst_details.side_effect = mock_gst_api
        
        mock_validate_amounts.return_value = {
            "audit_results": {
                "calculated_bill_amount": 1380.76,
                "extracted_bill_amount": 1381.0,
                "is_math_valid": True
            }
        }
        
        mock_validate_bill.return_value = {
            "is_bill_valid": True,
            "status_message": "Bill is Valid.",
            "discrepancy_details": []
        }

        # Run process_receipt pipeline
        result = self.loop.run_until_complete(process_receipt("dummy_image.jpg"))

        # Verify mocks were called correctly
        mock_parse_image.assert_called_once_with("dummy_image.jpg")
        mock_get_gst_details.assert_called_once_with("23AABFH6030L1ZN")
        mock_validate_amounts.assert_called_once_with(mock_parse_image.return_value)
        mock_validate_bill.assert_called_once()

        # Verify output
        self.assertTrue(result["is_bill_valid"])
        self.assertEqual(result["status_message"], "Bill is Valid.")

    @patch("main.ReceiptParser.parse_image")
    @patch("main.get_gst_details")
    @patch("main.ReceiptMathematicalValidator.validate_amounts")
    @patch("main.BillSynthesisValidator.validate_bill")
    def test_pipeline_missing_gstin_bypasses_api(self, mock_validate_bill, mock_validate_amounts, mock_get_gst_details, mock_parse_image):
        # Setup mocks: gst_number is None/missing
        mock_parse_image.return_value = {
            "gst_number": None,
            "date": "24/07/2021"
        }
        
        mock_validate_amounts.return_value = {
            "audit_results": {"calculated_bill_amount": 100.0, "extracted_bill_amount": 100.0}
        }
        
        mock_validate_bill.return_value = {
            "is_bill_valid": True,
            "status_message": "Bill is Valid.",
            "discrepancy_details": []
        }

        # Run pipeline
        result = self.loop.run_until_complete(process_receipt("dummy_image.jpg"))

        # Verify get_gst_details WAS NOT called because gst_number is None (bypassed)
        mock_get_gst_details.assert_not_called()
        mock_validate_amounts.assert_called_once_with(mock_parse_image.return_value)
        mock_validate_bill.assert_called_once()
        
        self.assertTrue(result["is_bill_valid"])

    @patch("main.ReceiptParser.parse_image")
    def test_pipeline_image_parsing_failure(self, mock_parse_image):
        # Setup mock to raise exception during image parsing
        mock_parse_image.side_effect = Exception("OpenRouter API failure")

        # Run pipeline
        result = self.loop.run_until_complete(process_receipt("dummy_image.jpg"))

        # Verify output halts execution and returns a failure payload
        self.assertFalse(result["is_bill_valid"])
        self.assertIn("Image parsing failed", result["status_message"])
        self.assertIn("OpenRouter API failure", result["discrepancy_details"][0])

if __name__ == "__main__":
    unittest.main()
