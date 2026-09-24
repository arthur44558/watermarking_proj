/**
 * upload.js - Handles file selection, drag-and-drop, client-side preview, metadata, and dynamic capacity calculation.
 */

const Upload = (function () {
  let coverFile = null;
  let watermarkFile = null;
  let coverImg = null;
  let wmImg = null;
  let carrierCapacityBytes = 0;
  let estimatedPayloadBytes = 0;

  // DOM elements
  const coverInput = document.getElementById("coverFileInput");
  const wmInput = document.getElementById("wmFileInput");
  const coverCanvas = document.getElementById("coverCanvas");
  const wmCanvas = document.getElementById("watermarkCanvas");
  const coverPlaceholder = document.getElementById("coverPlaceholder");
  const wmPlaceholder = document.getElementById("wmPlaceholder");
  const coverBadgeContainer = document.getElementById("coverBadgeContainer");
  const wmBadgeContainer = document.getElementById("wmBadgeContainer");
  const coverFileName = document.getElementById("coverFileName");
  const wmFileName = document.getElementById("wmFileName");
  const coverFileSize = document.getElementById("coverFileSize");
  const coverPartition = document.getElementById("coverPartition");
  const coverDims = document.getElementById("coverDims");
  const coverBadgeDims = document.getElementById("coverBadgeDims");
  const wmBadgeDims = document.getElementById("wmBadgeDims");

  // Dynamic watermark metadata elements
  const wmModeFormat = document.getElementById("wmModeFormat");
  const wmDimensions = document.getElementById("wmDimensions");
  const wmPayloadSize = document.getElementById("wmPayloadSize");
  const carrierCapacity = document.getElementById("carrierCapacity");
  const wmUtilization = document.getElementById("wmUtilization");
  const wmStatusHint = document.getElementById("wmStatusHint");

  const runBtn = document.getElementById("runWatermarkBtn");
  const coverDropZone = document.getElementById("coverDropZone");
  const wmDropZone = document.getElementById("wmDropZone");
  const activeModeBadge = document.getElementById("activeModeBadge");
  const runBtnText = document.getElementById("runBtnText");

  function formatBytes(bytes) {
    if (!bytes || bytes === 0) return "0 B";
    if (bytes < 1024) return bytes + " B";
    const kb = bytes / 1024;
    return kb > 1024 ? (kb / 1024).toFixed(2) + " MB" : kb.toFixed(1) + " KB";
  }

  function updateRunButtonState() {
    if (!runBtn) return;

    if (coverFile && watermarkFile) {
      runBtn.disabled = false;
      if (runBtnText) runBtnText.textContent = "Run Watermarking";
      if (activeModeBadge) {
        activeModeBadge.textContent = "EMBED + VERIFY";
        activeModeBadge.className =
          "font-mono text-[9px] px-1.5 py-0.5 rounded font-semibold bg-primary-fixed text-primary border border-primary/20";
      }
    } else if (coverFile && !watermarkFile) {
      runBtn.disabled = false;
      if (runBtnText) runBtnText.textContent = "Extract Watermark";
      if (activeModeBadge) {
        activeModeBadge.textContent = "EXTRACT ONLY";
        activeModeBadge.className =
          "font-mono text-[9px] px-1.5 py-0.5 rounded font-semibold bg-secondary-container text-on-secondary-fixed border border-secondary/20";
      }
    } else {
      runBtn.disabled = true;
      if (runBtnText) runBtnText.textContent = "Run Watermarking";
      if (activeModeBadge) {
        activeModeBadge.textContent = "Standby";
        activeModeBadge.className =
          "font-mono text-[9px] px-1.5 py-0.5 rounded font-semibold bg-surface-container border border-slate-200 text-secondary";
      }
    }
  }

  function updateCapacityDisplay() {
    if (!coverImg) {
      if (carrierCapacity) carrierCapacity.textContent = "—";
      if (wmUtilization) wmUtilization.textContent = "—";
      return;
    }

    const w = coverImg.naturalWidth || coverImg.width;
    const h = coverImg.naturalHeight || coverImg.height;
    const blocksH = Math.floor(h / 8);
    const blocksW = Math.floor(w / 8);
    const totalBlocks = blocksH * blocksW;

    // 16 bits (2 bytes) per block in Y (Luminance)
    const yCapacityBytes = Math.max(0, totalBlocks * 2 - 32);
    carrierCapacityBytes = yCapacityBytes;

    if (carrierCapacity) {
      carrierCapacity.textContent = `${formatBytes(yCapacityBytes)} (Luminance)`;
    }

    if (estimatedPayloadBytes > 0 && carrierCapacityBytes > 0) {
      const utilPercent = ((estimatedPayloadBytes / carrierCapacityBytes) * 100).toFixed(1);
      if (estimatedPayloadBytes > carrierCapacityBytes) {
        const deficit = estimatedPayloadBytes - carrierCapacityBytes;
        if (wmUtilization) {
          wmUtilization.innerHTML = `<span class="text-amber-800 font-semibold">${utilPercent}% (+${formatBytes(deficit)})</span>`;
        }
        if (wmStatusHint) {
          wmStatusHint.innerHTML = `<span class="text-amber-700 font-medium">Exceeds lossless capacity. Auto-compression &amp; scaling will optimize it to fit.</span>`;
        }
      } else {
        if (wmUtilization) {
          wmUtilization.textContent = `${utilPercent}% (${formatBytes(estimatedPayloadBytes)} / ${formatBytes(carrierCapacityBytes)})`;
        }
        if (wmStatusHint) {
          wmStatusHint.textContent = `Payload fits cleanly into carrier DCT capacity.`;
        }
      }
    } else {
      if (wmUtilization) wmUtilization.textContent = "—";
    }
  }

  function handleCoverFile(file) {
    if (!file || !file.type.startsWith("image/")) {
      alert("Please select a valid image file for the cover image.");
      return;
    }
    coverFile = file;
    coverFileName.textContent = file.name;
    coverFileSize.textContent = formatBytes(file.size);

    // Clear stale results on input change
    if (window.Results && Results.resetResults) {
      Results.resetResults();
    }

    const reader = new FileReader();
    reader.onload = function (e) {
      const img = new Image();
      img.onload = function () {
        const w = img.naturalWidth || img.width;
        const h = img.naturalHeight || img.height;
        coverImg = img;

        coverCanvas.width = w;
        coverCanvas.height = h;
        const ctx = coverCanvas.getContext("2d");
        ctx.clearRect(0, 0, w, h);
        ctx.drawImage(img, 0, 0);

        coverCanvas.style.display = "block";
        coverPlaceholder.style.display = "none";
        coverBadgeContainer.classList.remove("hidden");
        coverBadgeContainer.classList.add("flex");
        coverBadgeDims.textContent = `${w} × ${h} px`;
        coverDims.textContent = `${w}×${h}`;

        const blocksH = Math.floor(h / 8);
        const blocksW = Math.floor(w / 8);
        const totalBlocks = blocksH * blocksW;
        coverPartition.textContent = `8×8 (${totalBlocks.toLocaleString()} blks)`;

        updateCapacityDisplay();

        // Forward to results original canvas
        if (window.Results && Results.setOriginalPreview) {
          Results.setOriginalPreview(img, w, h);
        }

        updateRunButtonState();
      };
      img.src = e.target.result;
    };
    reader.readAsDataURL(file);
  }

  function handleWatermarkFile(file) {
    if (!file || !file.type.startsWith("image/")) {
      alert("Please select a valid image file for the watermark.");
      return;
    }
    watermarkFile = file;
    wmFileName.textContent = file.name;

    // Clear stale results on input change
    if (window.Results && Results.resetResults) {
      Results.resetResults();
    }

    const reader = new FileReader();
    reader.onload = function (e) {
      const img = new Image();
      img.onload = function () {
        const w = img.naturalWidth || img.width;
        const h = img.naturalHeight || img.height;
        wmImg = img;

        wmCanvas.width = w;
        wmCanvas.height = h;
        const ctx = wmCanvas.getContext("2d");
        ctx.clearRect(0, 0, w, h);
        ctx.drawImage(img, 0, 0);

        wmCanvas.style.display = "block";
        wmPlaceholder.style.display = "none";
        wmBadgeContainer.classList.remove("hidden");
        wmBadgeContainer.classList.add("flex");
        const ext = (file.name.split(".").pop() || "IMG").toUpperCase();
        wmBadgeDims.textContent = `${ext} • ${w} × ${h}`;

        // Determine color mode by sampling image pixels
        let isGrayscale = true;
        try {
          const sampleData = ctx.getImageData(0, 0, Math.min(w, 64), Math.min(h, 64)).data;
          for (let i = 0; i < sampleData.length; i += 4) {
            const r = sampleData[i];
            const g = sampleData[i + 1];
            const b = sampleData[i + 2];
            if (Math.abs(r - g) > 2 || Math.abs(g - b) > 2) {
              isGrayscale = false;
              break;
            }
          }
        } catch (err) {
          isGrayscale = false;
        }

        const colorModeStr = isGrayscale ? "Grayscale" : "RGB Color";
        if (wmModeFormat) wmModeFormat.textContent = `${ext} • ${colorModeStr}`;
        if (wmDimensions) wmDimensions.textContent = `${w} × ${h} px`;

        // Estimate compressed payload bytes from file size (PNG/JPEG already compressed)
        estimatedPayloadBytes = file.size;
        if (wmPayloadSize) {
          wmPayloadSize.textContent = `${formatBytes(file.size)} (raw/file)`;
        }

        updateCapacityDisplay();
        updateRunButtonState();
      };
      img.src = e.target.result;
    };
    reader.readAsDataURL(file);
  }

  function setupDragDrop(zone, onFile) {
    if (!zone) return;
    ["dragenter", "dragover"].forEach((evtName) => {
      zone.addEventListener(evtName, (e) => {
        e.preventDefault();
        zone.classList.add("border-primary", "bg-primary-fixed/20");
      });
    });
    ["dragleave", "drop"].forEach((evtName) => {
      zone.addEventListener(evtName, (e) => {
        e.preventDefault();
        zone.classList.remove("border-primary", "bg-primary-fixed/20");
      });
    });
    zone.addEventListener("drop", (e) => {
      const files = e.dataTransfer && e.dataTransfer.files;
      if (files && files.length > 0) {
        onFile(files[0]);
      }
    });
  }

  function init() {
    if (coverInput) {
      coverInput.addEventListener("change", (e) => {
        if (e.target.files && e.target.files[0]) {
          handleCoverFile(e.target.files[0]);
        }
      });
    }

    if (wmInput) {
      wmInput.addEventListener("change", (e) => {
        if (e.target.files && e.target.files[0]) {
          handleWatermarkFile(e.target.files[0]);
        }
      });
    }

    setupDragDrop(coverDropZone, handleCoverFile);
    setupDragDrop(wmDropZone, handleWatermarkFile);

    // Lightbox click-to-zoom on preview zones when image is loaded
    if (coverDropZone) {
      coverDropZone.addEventListener("click", () => {
        if (coverCanvas && coverCanvas.style.display !== "none") {
          const title = coverFile ? `Cover Image: ${coverFile.name}` : "Cover Image (Input)";
          if (window.Lightbox) Lightbox.open(coverCanvas.toDataURL(), title);
        }
      });
    }

    if (wmDropZone) {
      wmDropZone.addEventListener("click", () => {
        if (wmCanvas && wmCanvas.style.display !== "none") {
          const title = watermarkFile ? `Watermark Image: ${watermarkFile.name}` : "Watermark Image (Input)";
          if (window.Lightbox) Lightbox.open(wmCanvas.toDataURL(), title);
        }
      });
    }
  }

  function clearInputs() {
    coverFile = null;
    watermarkFile = null;
    coverImg = null;
    wmImg = null;
    carrierCapacityBytes = 0;
    estimatedPayloadBytes = 0;

    if (coverInput) coverInput.value = "";
    if (wmInput) wmInput.value = "";

    if (coverCanvas) coverCanvas.style.display = "none";
    if (wmCanvas) wmCanvas.style.display = "none";
    if (coverPlaceholder) coverPlaceholder.style.display = "flex";
    if (wmPlaceholder) wmPlaceholder.style.display = "flex";

    if (coverBadgeContainer) {
      coverBadgeContainer.classList.add("hidden");
      coverBadgeContainer.classList.remove("flex");
    }
    if (wmBadgeContainer) {
      wmBadgeContainer.classList.add("hidden");
      wmBadgeContainer.classList.remove("flex");
    }

    if (coverFileName) coverFileName.textContent = "Select cover image...";
    if (wmFileName) wmFileName.textContent = "Select watermark image (optional)...";
    if (coverFileSize) coverFileSize.textContent = "—";
    if (coverPartition) coverPartition.textContent = "—";
    if (coverDims) coverDims.textContent = "—";

    if (wmModeFormat) wmModeFormat.textContent = "—";
    if (wmDimensions) wmDimensions.textContent = "—";
    if (wmPayloadSize) wmPayloadSize.textContent = "—";
    if (carrierCapacity) carrierCapacity.textContent = "—";
    if (wmUtilization) wmUtilization.textContent = "—";
    if (wmStatusHint) wmStatusHint.textContent = "Lossless zlib payload • Multi-bit JND DCT embedding";

    updateRunButtonState();
  }

  return {
    init,
    clearInputs,
    getCoverFile: () => coverFile,
    getWatermarkFile: () => watermarkFile,
    hasValidInputs: () => !!coverFile,
    isExtractOnly: () => !watermarkFile,
  };
})();
