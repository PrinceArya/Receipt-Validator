import sys
import asyncio
from fastapi import FastAPI, HTTPException, Path
from playwright.async_api import async_playwright

# Playwright on Windows requires ProactorEventLoop to manage browser subprocesses
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

app = FastAPI(
    title="GSTIN Verification API",
    description="REST API to verify GSTINs by scraping ClearTax",
    version="1.0.0"
)

@app.get("/api/gst/{gstin}")
async def get_gst_details(
    gstin: str = Path(..., description="15-character Goods and Services Tax Identification Number")
):
    # 1. Validate length is exactly 15
    if len(gstin) != 15:
        raise HTTPException(
            status_code=400,
            detail="GSTIN must be exactly 15 characters long."
        )

    # 2. Scrape ClearTax using Playwright
    async with async_playwright() as p:
        browser = None
        try:
            # Launch headless Chromium
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Navigate to target URL
            await page.goto("https://cleartax.in/gst-number-search/", timeout=30000)
            
            # Fill the search input
            await page.fill("input#input", gstin)
            
            # Press enter to search
            await page.press("input#input", "Enter")
            
            # Poll for results or error message (max 6 seconds)
            success = False
            invalid = False
            for _ in range(24):
                # Check for result headers
                h4s = await page.query_selector_all("h4")
                if len(h4s) > 0:
                    for h4 in h4s:
                        txt = (await h4.inner_text()).strip().upper()
                        if txt in ["PAN", "BUSINESS NAME", "ADDRESS"]:
                            success = True
                            break
                if success:
                    break
                
                # Check for invalid message
                body_text = await page.inner_text("body")
                if "Invalid GSTIN / UID" in body_text:
                    invalid = True
                    break
                    
                await asyncio.sleep(0.25)
            
            if invalid:
                raise HTTPException(
                    status_code=404,
                    detail=f"GSTIN '{gstin}' is invalid or not found on the portal."
                )
                
            if not success:
                raise HTTPException(
                    status_code=500,
                    detail="Scraping failed: timeout waiting for results."
                )
            
            # Extract data from DOM
            extracted = {}
            h4s = await page.query_selector_all("h4")
            for h4 in h4s:
                label = (await h4.inner_text()).strip().upper()
                parent = await h4.query_selector("xpath=..")
                if parent:
                    small = await parent.query_selector("small")
                    if small:
                        val = (await small.inner_text()).strip()
                        extracted[label] = val
            
            # Format response matching the required JSON schema
            pan = gstin[2:12].upper()
            
            return {
                "Business Name": extracted.get("BUSINESS NAME", ""),
                "PAN": pan,
                "Address": extracted.get("ADDRESS", ""),
                "Entity Type": extracted.get("ENTITY TYPE", ""),
                "Nature of business": extracted.get("NATURE OF BUSINESS", ""),
                "Registration Type": extracted.get("REGISTRATION TYPE", ""),
                "Registration Date": extracted.get("REGISTRATION DATE", "")
            }
            
        except HTTPException:
            # Re-raise HTTPExceptions (400, 404, etc.)
            raise
        except Exception as e:
            # Handle any timeouts or DOM errors gracefully
            raise HTTPException(
                status_code=500,
                detail=f"Scraping failed: {str(e)}"
            )
        finally:
            if browser:
                await browser.close()
