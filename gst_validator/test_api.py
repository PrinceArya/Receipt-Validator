import subprocess
import time
import sys
import httpx

def run_tests():
    # Start uvicorn server in a subprocess
    print("Starting FastAPI app under uvicorn...")
    proc = subprocess.Popen(
        [r"D:\workspace\virtual_env\Scripts\python.exe", "-m", "uvicorn", "main:app", "--port", "8000"],
        cwd=r"d:\Project\Receipt_validator\GST_validator"
    )
    
    # Wait for server to boot up
    time.sleep(3)
    
    success = True
    client = httpx.Client(timeout=30.0)
    
    try:
        # Test 1: Invalid length (10 chars instead of 15)
        print("\n--- Running Test 1: Invalid length (1234567890) ---")
        res1 = client.get("http://127.0.0.1:8000/api/gst/1234567890")
        print(f"Status: {res1.status_code}")
        print(f"Response: {res1.json()}")
        if res1.status_code != 400:
            print("ERROR: Test 1 failed (expected status 400).")
            success = False
        else:
            print("SUCCESS: Test 1 passed.")

        # Test 2: Invalid GSTIN (not found in database)
        print("\n--- Running Test 2: Invalid GSTIN / Not Found (27AABCU9603R1ZM) ---")
        res2 = client.get("http://127.0.0.1:8000/api/gst/27AABCU9603R1ZM")
        print(f"Status: {res2.status_code}")
        print(f"Response: {res2.json()}")
        if res2.status_code != 404:
            print("ERROR: Test 2 failed (expected status 404).")
            success = False
        else:
            print("SUCCESS: Test 2 passed.")

        # Test 3: Valid active GSTIN (29AAAAP0267H1ZK)
        print("\n--- Running Test 3: Valid GSTIN (29AAAAP0267H1ZK) ---")
        res3 = client.get("http://127.0.0.1:8000/api/gst/29AAAAP0267H1ZK")
        print(f"Status: {res3.status_code}")
        print(f"Response: {res3.json()}")
        if res3.status_code != 200:
            print("ERROR: Test 3 failed (expected status 200).")
            success = False
        else:
            data = res3.json()
            required_keys = ["Business Name", "PAN", "Address", "Entity Type", "Nature of business", "Registration Type", "Registration Date"]
            keys_ok = all(k in data for k in required_keys)
            if not keys_ok:
                print("ERROR: Test 3 failed (missing required keys in schema).")
                success = False
            elif data["PAN"] != "AAAAP0267H":
                print(f"ERROR: Test 3 failed (PAN mismatch: {data['PAN']}).")
                success = False
            else:
                print("SUCCESS: Test 3 passed.")

        # Test 4: Valid Corporate GSTIN (29AAICA3918J1CP)
        print("\n--- Running Test 4: Valid Corporate GSTIN (29AAICA3918J1CP) ---")
        res4 = client.get("http://127.0.0.1:8000/api/gst/29AAICA3918J1CP")
        print(f"Status: {res4.status_code}")
        print(f"Response: {res4.json()}")
        if res4.status_code != 200:
            print("ERROR: Test 4 failed (expected status 200).")
            success = False
        else:
            data = res4.json()
            if data["Business Name"] != "AMAZON SELLER SERVICES PVT LTD":
                print(f"ERROR: Test 4 failed (Business Name mismatch: {data['Business Name']}).")
                success = False
            elif data["PAN"] != "AAICA3918J":
                print(f"ERROR: Test 4 failed (PAN mismatch: {data['PAN']}).")
                success = False
            else:
                print("SUCCESS: Test 4 passed.")

    except Exception as e:
        print("ERROR: Exception during test run:", str(e))
        success = False
    finally:
        client.close()
        print("\nStopping FastAPI server...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            
    if success:
        print("\nALL TESTS PASSED SUCCESSFULLY!")
        sys.exit(0)
    else:
        print("\nSOME TESTS FAILED.")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
