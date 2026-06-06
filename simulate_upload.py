import requests
import json

def test_upload():
    url = "http://127.0.0.1:8000/api/process"
    file_path = r"D:\Project\Receipt_validator\temp_img\images_receipt.jpeg"
    
    print(f"Uploading {file_path} to {url}...")
    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f, "image/jpeg")}
        response = requests.post(url, files=files)
        
    print(f"Status Code: {response.status_code}")
    print("Response JSON:")
    print(json.dumps(response.json(), indent=2))

if __name__ == "__main__":
    import os
    test_upload()
