document.addEventListener("DOMContentLoaded", () => {
    // ----------------------------------------------------------------
    // Element Selectors
    // ----------------------------------------------------------------
    
    // Tab controls
    const tabUpload = document.getElementById("tab-upload");
    const tabCamera = document.getElementById("tab-camera");
    const uploadContent = document.getElementById("upload-content");
    const cameraContent = document.getElementById("camera-content");

    // File Upload selectors
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");

    // Camera selectors
    const video = document.getElementById("video");
    const canvas = document.getElementById("canvas");
    const cameraFallback = document.getElementById("camera-fallback");
    const btnStartCamera = document.getElementById("btn-start-camera");
    const btnCapture = document.getElementById("btn-capture");

    // Preview selectors
    const previewBox = document.getElementById("preview-box");
    const imagePreview = document.getElementById("image-preview");
    const btnSubmit = document.getElementById("btn-submit");

    // State panels
    const stateIdle = document.getElementById("state-idle");
    const stateLoading = document.getElementById("state-loading");
    const resultsContainer = document.getElementById("results-container");

    // Loader Steps selectors
    const stepOCR = document.getElementById("step-ocr");
    const stepGST = document.getElementById("step-gst");
    const stepMath = document.getElementById("step-math");
    const stepSynth = document.getElementById("step-synth");

    // Results presentation selectors
    const statusCard = document.getElementById("status-card");
    const statusIcon = document.getElementById("status-icon");
    const statusTitle = document.getElementById("status-title");
    const statusMessage = document.getElementById("status-message");
    const warningsBox = document.getElementById("warnings-box");
    const warningsList = document.getElementById("warnings-list");
    const tableItemsBody = document.querySelector("#table-items tbody");
    const valSubtotal = document.getElementById("val-subtotal");
    const valTaxes = document.getElementById("val-taxes");
    const valGrandTotal = document.getElementById("val-grand-total");
    const rawJsonOutput = document.getElementById("raw-json-output");

    // Detail Tabs
    const detailTabs = document.querySelectorAll(".detail-tab-btn");
    const detailContents = document.querySelectorAll(".detail-content");

    // State variables
    let selectedFileBlob = null;
    let cameraStream = null;

    // ----------------------------------------------------------------
    // Tab Switching
    // ----------------------------------------------------------------
    tabUpload.addEventListener("click", () => {
        tabUpload.classList.add("active");
        tabCamera.classList.remove("active");
        uploadContent.classList.add("active");
        cameraContent.classList.remove("active");
        stopCamera();
    });

    tabCamera.addEventListener("click", () => {
        tabCamera.classList.add("active");
        tabUpload.classList.remove("active");
        cameraContent.classList.add("active");
        uploadContent.classList.remove("active");
    });

    // ----------------------------------------------------------------
    // Drag & Drop / File Input
    // ----------------------------------------------------------------
    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.classList.add("dragover");
    });

    dropZone.addEventListener("dragleave", () => {
        dropZone.classList.remove("dragover");
    });

    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.classList.remove("dragover");
        if (e.dataTransfer.files.length > 0) {
            handleFile(e.dataTransfer.files[0]);
        }
    });

    dropZone.addEventListener("click", (e) => {
        if (e.target !== fileInput && !e.target.closest("label")) {
            fileInput.click();
        }
    });

    fileInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            handleFile(e.target.files[0]);
        }
    });

    function handleFile(file) {
        if (!file.type.startsWith("image/")) {
            alert("Please select a valid receipt image file.");
            return;
        }
        selectedFileBlob = file;
        
        // Render preview image
        const reader = new FileReader();
        reader.onload = (e) => {
            imagePreview.src = e.target.result;
            previewBox.classList.remove("hidden");
        };
        reader.readAsDataURL(file);
    }

    // ----------------------------------------------------------------
    // Camera Handlers (WebRTC)
    // ----------------------------------------------------------------
    btnStartCamera.addEventListener("click", async () => {
        try {
            if (cameraStream) {
                stopCamera();
            }
            cameraStream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: "environment" },
                audio: false
            });
            video.srcObject = cameraStream;
            video.classList.remove("hidden");
            cameraFallback.classList.add("hidden");
            btnCapture.disabled = false;
            btnStartCamera.innerText = "Restart Camera";
        } catch (err) {
            console.error("Error accessing camera: ", err);
            cameraFallback.innerText = "Camera access denied or unsupported.";
            cameraFallback.classList.remove("hidden");
            video.classList.add("hidden");
        }
    });

    btnCapture.addEventListener("click", () => {
        if (!cameraStream) return;
        
        // Draw video frame onto canvas
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const ctx = canvas.getContext("2d");
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        // Convert canvas capture to Blob file
        canvas.toBlob((blob) => {
            selectedFileBlob = new File([blob], "capture.jpg", { type: "image/jpeg" });
            imagePreview.src = canvas.toDataURL("image/jpeg");
            previewBox.classList.remove("hidden");
        }, "image/jpeg");

        stopCamera();
    });

    function stopCamera() {
        if (cameraStream) {
            cameraStream.getTracks().forEach(track => track.stop());
            cameraStream = null;
        }
        video.srcObject = null;
        btnCapture.disabled = true;
        btnStartCamera.innerText = "Start Camera";
    }

    // ----------------------------------------------------------------
    // Submission & Pipeline Animation
    // ----------------------------------------------------------------
    btnSubmit.addEventListener("click", async () => {
        if (!selectedFileBlob) {
            alert("No receipt image selected.");
            return;
        }

        // 1. Reset states
        stateIdle.classList.add("hidden");
        resultsContainer.classList.add("hidden");
        stateLoading.classList.remove("hidden");
        
        resetPipelineSteps();

        // 2. Build form payload
        const formData = new FormData();
        formData.append("file", selectedFileBlob);

        // 3. Run Pipeline Loader Step Animations sequentially
        // Step 1: OCR starting
        setStepActive(stepOCR);

        try {
            // Initiate parallel network request to backend
            const fetchPromise = fetch("/api/process", {
                method: "POST",
                body: formData
            });

            // Simulate local parsing progress
            await delay(1200);
            setStepDone(stepOCR);
            
            setStepActive(stepGST);
            await delay(1500);
            setStepDone(stepGST);

            setStepActive(stepMath);
            await delay(1000);
            setStepDone(stepMath);

            setStepActive(stepSynth);

            const response = await fetchPromise;
            if (!response.ok) {
                throw new Error(`HTTP Error status ${response.status}`);
            }

            const data = await response.json();
            setStepDone(stepSynth);
            await delay(400);

            // 4. Render validation outputs
            renderResults(data);

        } catch (err) {
            console.error("Pipeline failure: ", err);
            renderError(err.message);
        } finally {
            stateLoading.classList.add("hidden");
        }
    });

    // ----------------------------------------------------------------
    // Helpers
    // ----------------------------------------------------------------
    function delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    function resetPipelineSteps() {
        [stepOCR, stepGST, stepMath, stepSynth].forEach(step => {
            step.className = "step";
        });
    }

    function setStepActive(stepElement) {
        stepElement.classList.add("active");
    }

    function setStepDone(stepElement) {
        stepElement.classList.remove("active");
        stepElement.classList.add("done");
    }

    // ----------------------------------------------------------------
    // Rendering Results
    // ----------------------------------------------------------------
    function renderResults(payload) {
        resultsContainer.classList.remove("hidden");

        // Format raw json
        rawJsonOutput.textContent = JSON.stringify(payload, null, 2);

        // Determine if it is a synthesis pipeline output (contains is_bill_valid)
        // or a default raw parser output
        let isValid = false;
        let statusMsg = "Analysis Failed";
        let warnings = [];

        if (payload.status_code === 500) {
            renderError(payload.message || "Pipeline crashed.");
            return;
        }

        // If it is the synthesis response
        if (payload.hasOwnProperty("is_bill_valid")) {
            isValid = payload.is_bill_valid;
            statusMsg = payload.status_message;
            warnings = payload.discrepancy_details || [];
        }

        // Update main badge
        if (isValid) {
            statusCard.className = "status-card valid";
            statusIcon.innerHTML = `
                <svg width="24" height="24" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                    <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
            `;
            statusTitle.innerText = "Receipt Verified Valid";
            statusMessage.innerText = statusMsg;
        } else {
            statusCard.className = "status-card invalid";
            statusIcon.innerHTML = `
                <svg width="24" height="24" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
            `;
            statusTitle.innerText = "Audit Failed / Discrepancy Found";
            statusMessage.innerText = statusMsg;
        }

        // Render warnings
        if (warnings.length > 0) {
            warningsList.innerHTML = "";
            warnings.forEach(warn => {
                const li = document.createElement("li");
                li.innerText = warn;
                warningsList.appendChild(li);
            });
            warningsBox.classList.remove("hidden");
        } else {
            warningsBox.classList.add("hidden");
        }

        // Render summary items
        renderSummaryDetails(payload);
    }

    function renderSummaryDetails(payload) {
        tableItemsBody.innerHTML = "";
        
        // Dynamically extract line items from the response
        let lineItems = [];
        if (payload.receipt_data && payload.receipt_data.line_items) {
            lineItems = payload.receipt_data.line_items;
        }

        // Fallback to demo items if no receipt data present
        if (lineItems.length === 0) {
            lineItems = [
                { description: "VEG MANCHAW SOUP (Demo)", qty: 1, amount: 119.0 },
                { description: "DAL TADKA (Demo)", qty: 1, amount: 215.0 },
                { description: "JEERA RICE (Demo)", qty: 1, amount: 145.0 },
                { description: "PLAIN PAPAD (Demo)", qty: 2, amount: 80.0 }
            ];
        }

        lineItems.forEach(item => {
            const desc = item.description || item.desc || "Unknown Item";
            const qty = item.qty || 1;
            const amt = item.amount || item.amt || 0.0;
            
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td>${desc}</td>
                <td class="text-right">${qty}</td>
                <td class="text-right">₹${parseFloat(amt).toFixed(2)}</td>
            `;
            tableItemsBody.appendChild(tr);
        });

        // Dynamically compute/read calculation values
        let subtotalVal = 1315.0;
        let taxVal = 65.76;
        let grandTotalVal = 1380.76;

        if (payload.math_audit) {
            subtotalVal = payload.math_audit.calculated_subtotal || 0.0;
            grandTotalVal = payload.math_audit.calculated_bill_amount || 0.0;
            
            if (payload.math_audit.calculated_taxes) {
                taxVal = payload.math_audit.calculated_taxes.reduce((sum, t) => sum + (t.calculated_amount || 0.0), 0.0);
            } else {
                taxVal = 0.0;
            }
        }

        // Set math values on UI
        valSubtotal.innerText = `₹${parseFloat(subtotalVal).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
        valTaxes.innerText = `₹${parseFloat(taxVal).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
        valGrandTotal.innerText = `₹${parseFloat(grandTotalVal).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
    }

    function renderError(message) {
        resultsContainer.classList.remove("hidden");
        statusCard.className = "status-card invalid";
        statusIcon.innerHTML = `
            <svg width="24" height="24" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
        `;
        statusTitle.innerText = "Pipeline Execution Failure";
        statusMessage.innerText = message;
        warningsBox.classList.add("hidden");
        tableItemsBody.innerHTML = "<tr><td colspan='3' class='text-muted'>No data available due to validation crash.</td></tr>";
        valSubtotal.innerText = "-";
        valTaxes.innerText = "-";
        valGrandTotal.innerText = "-";
        rawJsonOutput.textContent = JSON.stringify({ error: message }, null, 2);
    }

    // ----------------------------------------------------------------
    // Detail Tabs Interaction
    // ----------------------------------------------------------------
    detailTabs.forEach(tab => {
        tab.addEventListener("click", () => {
            detailTabs.forEach(t => t.classList.remove("active"));
            detailContents.forEach(c => c.classList.remove("active"));

            tab.classList.add("active");
            const targetId = tab.getAttribute("data-target");
            document.getElementById(targetId).classList.add("active");
        });
    });
});
