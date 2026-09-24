/**
 * upload.js - Handles file selection, drag-and-drop, client-side preview, metadata,
 * and dynamic capacity calculation for both Cover Images and Cover Videos.
 */

const Upload = (function () {
  let coverFile = null;
  let watermarkFile = null;
  let coverImg = null;
  let wmImg = null;
  let isCoverVideo = false;
  let videoObjectUrl = null;
  let carrierCapacityBytes = 0;
  let estimatedPayloadBytes = 0;

  // DOM elements
  const coverInput = document.getElementById("coverFileInput");
  const wmInput = document.getElementById("wmFileInput");
  const coverCanvas = document.getElementById("coverCanvas");
  const coverVideoPreview = document.getElementById("coverVideoPreview");
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
  const coverCardTitle = document.getElementById("coverCardTitle");
  const coverBadgeType = document.getElementById("coverBadgeType");

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
      if (runBtnText) {
        runBtnText.textContent = isCoverVideo ? "Watermark Video" : "Run Watermarking";
      }
      if (activeModeBadge) {
        activeModeBadge.textContent = isCoverVideo ? "VIDEO EMBED" : "EMBED + VERIFY";
        activeModeBadge.className =
          "font-mono text-[9px] px-1.5 py-0.5 rounded font-semibold bg-primary-fixed text-primary border border-primary/20";
      }
    } else if (coverFile && !watermarkFile) {
      runBtn.disabled = false;
      if (runBtnText) {
        runBtnText.textContent = isCoverVideo ? "Extract from Video" : "Extract Watermark";
      }
      if (activeModeBadge) {
        activeModeBadge.textContent = isCoverVideo ? "VIDEO EXTRACT" : "EXTRACT ONLY";
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

    // 16 bits (2 bytes) per block in Y (Luminance) minus 32-byte header
    const yCapacityBytes = Math.max(0, totalBlocks * 2 - 32);
    carrierCapacityBytes = yCapacityBytes;

    if (carrierCapacity) {
      const suffix = isCoverVideo ? "(Luminance / frame)" : "(Luminance)";
      carrierCapacity.textContent = `${formatBytes(yCapacityBytes)} ${suffix}`;
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
          wmStatusHint.textContent = isCoverVideo
            ? `Payload fits into frame DCT capacity. Redundantly embedded across all video frames.`
            : `Payload fits cleanly into carrier DCT capacity.`;
        }
      }
    } else {
      if (wmUtilization) wmUtilization.textContent = "—";
    }
  }

  async function queryServerCapacity(file) {
    try {
      const formData = new FormData();
      formData.append("cover_image", file);
      const res = await fetch("/api/capacity", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (data.success && data.capacity) {
        carrierCapacityBytes = data.capacity.usable_y_capacity_bytes;
        updateCapacityDisplay();
      }
    } catch (err) {
      console.warn("Could not query server capacity for cover media:", err);
    }
  }

  function handleCoverFile(file) {
    if (!file) return;

    const isVideo = file.type.startsWith("video/") || /\.(mp4|avi|mov|webm|mkv)$/i.test(file.name);
    const isImage = file.type.startsWith("image/") || /\.(png|jpg|jpeg|webp|bmp)$/i.test(file.name);

    if (!isVideo && !isImage) {
      alert("Please select a valid image (PNG, JPG, WEBP) or video (MP4, AVI, MOV, WEBM) file for the cover.");
      return;
    }

    coverFile = file;
    isCoverVideo = isVideo;
    coverFileName.textContent = file.name;
    coverFileSize.textContent = formatBytes(file.size);

    if (coverCardTitle) coverCardTitle.textContent = isVideo ? "Cover Video" : "Cover Image";
    if (coverBadgeType) coverBadgeType.textContent = isVideo ? "COVER VIDEO" : "COVER IMAGE";

    // Clear stale results on input change
    if (window.Results && Results.resetResults) {
      Results.resetResults();
    }

    if (isVideo) {
      // === VIDEO HANDLING ===
      if (coverCanvas) coverCanvas.style.display = "none";
      if (coverPlaceholder) coverPlaceholder.style.display = "none";

      if (videoObjectUrl) {
        URL.revokeObjectURL(videoObjectUrl);
      }
      videoObjectUrl = URL.createObjectURL(file);

      if (coverVideoPreview) {
        coverVideoPreview.src = videoObjectUrl;
        coverVideoPreview.style.display = "block";
        coverVideoPreview.onloadedmetadata = function () {
          const w = coverVideoPreview.videoWidth || 1280;
          const h = coverVideoPreview.videoHeight || 720;
          const dur = coverVideoPreview.duration ? coverVideoPreview.duration.toFixed(1) : "—";
          coverImg = { naturalWidth: w, naturalHeight: h, width: w, height: h, isVideo: true };

          coverBadgeContainer.classList.remove("hidden");
          coverBadgeContainer.classList.add("flex");
          const ext = (file.name.split(".").pop() || "VID").toUpperCase();
          coverBadgeDims.textContent = `${ext} • ${w} × ${h} px • ${dur}s`;
          coverDims.textContent = `${w}×${h} (${dur}s)`;

          const blocksH = Math.floor(h / 8);
          const blocksW = Math.floor(w / 8);
          const totalBlocks = blocksH * blocksW;
          coverPartition.textContent = `8×8 (${totalBlocks.toLocaleString()} blks/frame)`;

          updateCapacityDisplay();
          if (!isCoverVideo || file.size < 25 * 1024 * 1024) {
            queryServerCapacity(file);
          }

          if (window.Results && Results.setOriginalPreview) {
            Results.setOriginalPreview(videoObjectUrl, w, h, true);
          }

          updateRunButtonState();
        };
      }
    } else {
      // === IMAGE HANDLING ===
      if (coverVideoPreview) {
        coverVideoPreview.style.display = "none";
        coverVideoPreview.pause();
        coverVideoPreview.src = "";
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

          if (window.Results && Results.setOriginalPreview) {
            Results.setOriginalPreview(img, w, h, false);
          }

          updateRunButtonState();
        };
        img.src = e.target.result;
      };
      reader.readAsDataURL(file);
    }
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

        // Sample pixels to determine color mode
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

    // Lightbox click-to-zoom on preview zones
    if (coverDropZone) {
      coverDropZone.addEventListener("click", (e) => {
        if (e.target && e.target.tagName === "VIDEO") return;
        if (isCoverVideo && videoObjectUrl) {
          const title = coverFile ? `Cover Video: ${coverFile.name}` : "Cover Video (Input)";
          if (window.Lightbox) Lightbox.open(videoObjectUrl, title, true);
        } else if (coverCanvas && coverCanvas.style.display !== "none") {
          const title = coverFile ? `Cover Image: ${coverFile.name}` : "Cover Image (Input)";
          if (window.Lightbox) Lightbox.open(coverCanvas.toDataURL(), title, false);
        }
      });
    }

    if (wmDropZone) {
      wmDropZone.addEventListener("click", () => {
        if (wmCanvas && wmCanvas.style.display !== "none") {
          const title = watermarkFile ? `Watermark Image: ${watermarkFile.name}` : "Watermark Image (Input)";
          if (window.Lightbox) Lightbox.open(wmCanvas.toDataURL(), title, false);
        }
      });
    }
  }

  function clearInputs() {
    coverFile = null;
    watermarkFile = null;
    coverImg = null;
    wmImg = null;
    isCoverVideo = false;
    carrierCapacityBytes = 0;
    estimatedPayloadBytes = 0;

    if (videoObjectUrl) {
      URL.revokeObjectURL(videoObjectUrl);
      videoObjectUrl = null;
    }

    if (coverInput) coverInput.value = "";
    if (wmInput) wmInput.value = "";

    if (coverCanvas) coverCanvas.style.display = "none";
    if (coverVideoPreview) {
      coverVideoPreview.style.display = "none";
      coverVideoPreview.pause();
      coverVideoPreview.src = "";
    }
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

    if (coverCardTitle) coverCardTitle.textContent = "Cover Media";
    if (coverBadgeType) coverBadgeType.textContent = "COVER IMAGE / VIDEO";
    if (coverFileName) coverFileName.textContent = "Select cover image or video...";
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
    isCoverVideo: () => isCoverVideo,
    hasValidInputs: () => !!coverFile,
    isExtractOnly: () => !watermarkFile,
  };
})();
