import os
import sys
import shutil
import asyncio
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse

# Playwright on Windows requires ProactorEventLoop to manage browser subprocesses
if sys.platform == 'win32':
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except AttributeError:
        pass

# Ensure packages can be imported correctly from the current workspace root
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Imports from existing directories
try:
    from bill_parser.receipt_parser import ReceiptParser
    from gst_validator.main import get_gst_details
    from amount_calculator.validator import ReceiptMathematicalValidator
    from bill_validator.validator import BillSynthesisValidator
except ImportError as ie:
    # Handle import errors gracefully if running from a different context
    print(f"Import Error: {ie}")
    raise

# ==========================================
# Initialize FastAPI Application
# ==========================================
app = FastAPI(
    title="Receipt Validator Orchestrator App",
    description="Full-stack endpoint serving React SPA static files and validation pipeline",
    version="1.0.0"
)

async def process_receipt(image_path: str) -> dict:
    """
    Wires together bill_parser, gst_validator, amount_calculator, and bill_validator
    into a single, high-performance, asynchronous pipeline.
    
    Args:
        image_path (str): Absolute or relative path to the receipt image.
        
    Returns:
        dict: Final synthesis JSON payload or error payload.
    """
    try:
        # Step 1: Image Parsing (Sequential)
        try:
            # ReceiptParser.parse_image is synchronous, so we run it in an executor or call directly
            # Since it makes external network calls, running in executor keeps the event loop non-blocking
            loop = asyncio.get_running_loop()
            bill_parser_json = await loop.run_in_executor(None, ReceiptParser.parse_image, image_path)
            
            if not bill_parser_json or not isinstance(bill_parser_json, dict):
                return {
                    "is_bill_valid": False,
                    "status_message": "Discrepancy in the Bill: Image parsing returned empty or invalid schema.",
                    "discrepancy_details": ["Image parsing failed or returned empty JSON object."]
                }
        except Exception as e:
            # If the parser throws an error, halt execution and return a failure payload immediately
            return {
                "is_bill_valid": False,
                "status_message": f"Discrepancy in the Bill: Image parsing failed. Error: {str(e)}",
                "discrepancy_details": [f"Image parsing failed: {str(e)}"]
            }

        # Extract the gst_number from the parsed JSON
        gst_number = bill_parser_json.get("gst_number")

        # Step 2 & Step 3: API Call and Math Audit (Parallel Execution)
        # Use asyncio.gather to run the GST validation and the math computation concurrently.
        
        async def run_gst_validation(gstin: Any) -> dict:
            # Edge Case: If gst_number is null or missing, bypass the GST API call
            if not gstin or str(gstin).strip().lower() in ["null", "none", "n/a", "nan", ""]:
                return {
                    "Registration Type": "Unregistered",
                    "Business Name": "Unregistered",
                    "PAN": gstin[2:12].upper() if (gstin and len(str(gstin)) >= 12) else None
                }
            
            # Otherwise, call clear tax API wrapper from gst_validator
            try:
                return await get_gst_details(str(gstin))
            except Exception as e:
                # If API call fails (portal down, invalid GSTIN, scraper error), fallback gracefully
                # to a default Unregistered/Unknown payload so the pipeline does not completely halt
                return {
                    "Registration Type": "Unregistered",
                    "Business Name": f"Unknown (GST API Error: {str(e)})",
                    "PAN": str(gstin)[2:12].upper() if len(str(gstin)) >= 12 else None
                }

        async def run_math_audit(data: dict) -> dict:
            # Run the mathematical verification module (synchronous computation)
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, ReceiptMathematicalValidator.validate_amounts, data)

        # Run both tasks concurrently without blocking each other
        gst_validator_json, amount_calculator_json = await asyncio.gather(
            run_gst_validation(gst_number),
            run_math_audit(bill_parser_json)
        )

        import json
        print(f"DEBUG PIPELINE: bill_parser_json = {json.dumps(bill_parser_json, indent=2)}")
        print(f"DEBUG PIPELINE: amount_calculator_json = {json.dumps(amount_calculator_json, indent=2)}")

        # Step 4: Final Synthesis (Sequential)
        final_validation_json = BillSynthesisValidator.validate_bill(
            gst_validator_json,
            bill_parser_json,
            amount_calculator_json
        )

        # Combine synthesis and details for UI rendering
        return {
            **final_validation_json,
            "receipt_data": bill_parser_json,
            "gst_profile": gst_validator_json,
            "math_audit": amount_calculator_json.get("audit_results", amount_calculator_json)
        }

    except Exception as e:
        # Standardized HTTP 500 equivalent JSON error response if the pipeline breaks unexpectedly
        return {
            "status_code": 500,
            "error": "Internal Server Error",
            "message": f"Unexpected pipeline failure: {str(e)}",
            "details": {
                "type": type(e).__name__,
                "description": str(e)
            }
        }

# ==========================================
# API Routes
# ==========================================

@app.post("/api/process")
async def upload_and_process_receipt(file: UploadFile = File(...)):
    """
    Accepts a receipt image via multipart file upload, saves it,
    runs the validation pipeline, and returns the final synthesized validation results.
    """
    temp_dir = "temp_img"
    os.makedirs(temp_dir, exist_ok=True)
    temp_file_path = os.path.join(temp_dir, f"upload_{file.filename}")
    
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        result = await process_receipt(temp_file_path)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline processing failed: {str(e)}")
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@app.post("/api/process-path")
async def process_receipt_by_path(image_path: str = Form(...)):
    """
    Runs the receipt validation pipeline on a local file path.
    """
    if not os.path.exists(image_path):
        raise HTTPException(status_code=400, detail=f"Target file path '{image_path}' does not exist.")
    return await process_receipt(image_path)

@app.get("/api/gst/{gstin}")
async def get_gst(
    gstin: str = Path(..., description="15-character Goods and Services Tax Identification Number")
):
    """
    Exposes direct scraper access to get GST registration details by scraping ClearTax.
    """
    if len(gstin) != 15:
        raise HTTPException(status_code=400, detail="GSTIN must be exactly 15 characters long.")
    try:
        return await get_gst_details(gstin)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# Static Files & Frontend Routing
# ==========================================

# Mount static React SPA assets
frontend_assets_dir = os.path.join("frontend", "dist", "assets")
if os.path.exists(frontend_assets_dir):
    app.mount("/assets", StaticFiles(directory=frontend_assets_dir), name="assets")

@app.get("/")
async def serve_index():
    index_path = os.path.join("frontend", "dist", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("React build index.html not found.", status_code=404)

@app.get("/{catchall:path}")
async def serve_spa(catchall: str):
    # Return 404 for missing /api routes
    if catchall.startswith("api/"):
        raise HTTPException(status_code=404, detail="API route not found.")
        
    index_path = os.path.join("frontend", "dist", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("React build index.html not found.", status_code=404)

# Keep standard main block for standalone testing and run verification
if __name__ == "__main__":
    import uvicorn
    # Standalone execution - launch server
    print("Launching orchestrator FastAPI app server...")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
