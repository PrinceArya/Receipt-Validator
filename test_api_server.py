import os
import unittest
from fastapi.testclient import TestClient
from unittest.mock import patch

# Import the FastAPI app
from main import app

class TestFastAPIApp(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_serve_react_index(self):
        # Fetching root / should return index.html contents
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Receipt Audit Portal", response.text)

    def test_serve_assets(self):
        # Fetching app.js should return app.js contents
        response = self.client.get("/assets/app.js")
        self.assertEqual(response.status_code, 200)
        self.assertIn("DOMContentLoaded", response.text)

    @patch("main.get_gst_details")
    def test_api_gst_endpoint(self, mock_get_gst_details):
        # Mocking external scraper details
        mock_get_gst_details.return_value = {
            "Business Name": "Test Business",
            "Registration Type": "Regular"
        }

        response = self.client.get("/api/gst/23AABFH6030L1ZN")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["Business Name"], "Test Business")
        self.assertEqual(data["Registration Type"], "Regular")

    @patch("main.process_receipt")
    def test_api_process_endpoint(self, mock_process_receipt):
        # Mocking pipeline processor
        mock_process_receipt.return_value = {
            "is_bill_valid": True,
            "status_message": "Bill is Valid."
        }

        # Create a dummy file in memory to upload
        dummy_file = ("dummy.jpg", b"fake_image_bytes", "image/jpeg")
        
        response = self.client.post(
            "/api/process",
            files={"file": dummy_file}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["is_bill_valid"], True)
        self.assertEqual(data["status_message"], "Bill is Valid.")

if __name__ == "__main__":
    unittest.main()
