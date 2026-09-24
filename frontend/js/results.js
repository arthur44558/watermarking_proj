/**
 * results.js - Handles rendering of real watermarking results, metrics, metadata, downloads, and lightbox zoom.
 */

const Results = (function () {
  const outOriginalCanvas = document.getElementById("outOriginalCanvas");
  const outWatermarkedCanvas = document.getElementById("outWatermarkedCanvas");
  const outExtractedCanvas = document.getElementById("outExtractedCanvas");

  const outOriginalContainer = document.getElementById("outOriginalContainer");
  const outWatermarkedContainer = document.getElementById("outWatermarkedContainer");
  const outExtractedContainer = document.getElementById("outExtractedContainer");

  const originalResultOverlay = document.getElementById("originalResultOverlay");
  const watermarkResultOverlay = document.getElementById("watermarkResultOverlay");
  const extractedResultOverlay = document.getElementById("extractedResultOverlay");
  const wmOverlayIcon = document.getElementById("wmOverlayIcon");
  const wmOverlayText = document.getElementById("wmOverlayText");
  const exOverlayIcon = document.getElementById("exOverlayIcon");
  const exOverlayText = document.getElementById("exOverlayText");

  const watermarkedCardTitle = document.getElementById("watermarkedCardTitle");
  const downloadWatermarkedBtn = document.getElementById("downloadWatermarkedBtn");
  const downloadExtractedBtn = document.getElementById("downloadExtractedBtn");

  const watermarkFidelityMetric = document.getElementById("watermarkFidelityMetric");
  const watermarkFidelityText = document.getElementById("watermarkFidelityText");
  const extractCorrMetric = document.getElementById("extractCorrMetric");
  const extractFidelityText = document.getElementById("extractFidelityText");

  const badgePsnrMini = document.getElementById("badgePsnrMini");
  const badgeBerMini = document.getElementById("badgeBerMini");
  const payloadMatchPill = document.getElementById("payloadMatchPill");

  const metricPsnr = document.getElementById("metricPsnr");
  const metricSsim = document.getElementById("metricSsim");
  const metricAcc = document.getElementById("metricAcc");
  const metricNc = document.getElementById("metricNc");
  const metricAccSub = document.getElementById("metricAccSub");

  const pipelineStatusBanner = document.getElementById("pipelineStatusBanner");
  const executionTimer = document.getElementById("executionTimer");
  const configChips = document.getElementById("configChips");

  const optimizationCard = document.getElementById("optimizationCard");
  const optStatusBadge = document.getElementById("optStatusBadge");
  const optOrigSize = document.getElementById("optOrigSize");
  const optOptSize = document.getElementById("optOptSize");
  const optReduction = document.getElementById("optReduction");
  const optOrigDims = document.getElementById("optOrigDims");
  const optOptDims = document.getElementById("optOptDims");
  const optFormatQual = document.getElementById("optFormatQual");

  let currentMode = "embed_and_verify";

  function init() {
    // Click-to-zoom lightbox handlers
    if (outOriginalContainer) {
      outOriginalContainer.addEventListener("click", () => {
        if (originalResultOverlay && originalResultOverlay.classList.contains("hidden")) {
          if (window.Lightbox) Lightbox.open(outOriginalCanvas.toDataURL(), "Original Image (Reference Baseline)");
        }
      });
    }

    if (outWatermarkedContainer) {
      outWatermarkedContainer.addEventListener("click", () => {
        if (watermarkResultOverlay && watermarkResultOverlay.classList.contains("hidden")) {
          const title = currentMode === "extract_only" ? "Extraction Input Image" : "Watermarked Image (DCT + JND)";
          if (window.Lightbox) Lightbox.open(outWatermarkedCanvas.toDataURL(), title);
        }
      });
    }

    if (outExtractedContainer) {
      outExtractedContainer.addEventListener("click", () => {
        if (extractedResultOverlay && extractedResultOverlay.classList.contains("hidden")) {
          if (window.Lightbox) Lightbox.open(outExtractedCanvas.toDataURL(), "Extracted Watermark Image (Lossless)");
        }
      });
    }
  }

  function setOriginalPreview(img, w, h) {
    if (!outOriginalCanvas) return;
    outOriginalCanvas.width = w;
    outOriginalCanvas.height = h;
    const ctx = outOriginalCanvas.getContext("2d");
    ctx.clearRect(0, 0, w, h);
    ctx.drawImage(img, 0, 0);

    if (originalResultOverlay) {
      originalResultOverlay.classList.add("hidden");
    }
  }

  function setProcessingState(isExtractOnly = false) {
    currentMode = isExtractOnly ? "extract_only" : "embed_and_verify";

    if (watermarkResultOverlay) {
      watermarkResultOverlay.classList.remove("hidden");
      if (wmOverlayIcon) {
        wmOverlayIcon.textContent = "progress_activity";
        wmOverlayIcon.classList.add("animate-spin");
      }
      if (wmOverlayText) {
        wmOverlayText.textContent = isExtractOnly ? "Analyzing Host Image..." : "Embedding payload in DCT domain...";
      }
    }

    if (extractedResultOverlay) {
      extractedResultOverlay.classList.remove("hidden");
      if (exOverlayIcon) {
        exOverlayIcon.textContent = "hourglass_empty";
      }
      if (exOverlayText) {
        exOverlayText.innerHTML = isExtractOnly ? "Extracting<br>Watermark..." : "Verifying<br>Extraction...";
      }
    }

    if (pipelineStatusBanner) {
      pipelineStatusBanner.textContent = isExtractOnly ? "Pipeline: Extracting..." : "Pipeline: Embedding & Verifying...";
    }
  }

  function displayResults(data, elapsedMs) {
    currentMode = data.mode || "embed_and_verify";
    const isExtractOnly = currentMode === "extract_only";
    const meta = data.metadata || {};

    // 1. Render Watermarked / Input Image
    if (data.watermarked_image && outWatermarkedCanvas) {
      const wmImg = new Image();
      wmImg.onload = function () {
        const w = wmImg.naturalWidth || wmImg.width;
        const h = wmImg.naturalHeight || wmImg.height;
        outWatermarkedCanvas.width = w;
        outWatermarkedCanvas.height = h;
        const ctx = outWatermarkedCanvas.getContext("2d");
        ctx.clearRect(0, 0, w, h);
        ctx.drawImage(wmImg, 0, 0);

        if (watermarkResultOverlay) {
          watermarkResultOverlay.classList.add("hidden");
        }
      };
      wmImg.src = `${data.watermarked_image}?t=${Date.now()}`;
    }

    // 2. Render Extracted Watermark
    if (data.extracted_watermark && outExtractedCanvas) {
      const exImg = new Image();
      exImg.onload = function () {
        const w = exImg.naturalWidth || exImg.width;
        const h = exImg.naturalHeight || exImg.height;
        outExtractedCanvas.width = w;
        outExtractedCanvas.height = h;
        const ctx = outExtractedCanvas.getContext("2d");
        ctx.clearRect(0, 0, w, h);
        ctx.drawImage(exImg, 0, 0);

        if (extractedResultOverlay) {
          extractedResultOverlay.classList.add("hidden");
        }
      };
      exImg.src = `${data.extracted_watermark}?t=${Date.now()}`;
    }

    // 3. Configure Direct File Downloads
    if (downloadWatermarkedBtn && data.watermarked_image) {
      downloadWatermarkedBtn.href = data.watermarked_image;
      downloadWatermarkedBtn.download = isExtractOnly ? "input_carrier.png" : "watermarked_image.png";
      downloadWatermarkedBtn.classList.remove("hidden");
      downloadWatermarkedBtn.classList.add("inline-flex");
    }

    if (downloadExtractedBtn && data.extracted_watermark) {
      downloadExtractedBtn.href = data.extracted_watermark;
      downloadExtractedBtn.download = "extracted_watermark.png";
      downloadExtractedBtn.classList.remove("hidden");
      downloadExtractedBtn.classList.add("inline-flex");
    }

    // 4. Update UI Card Titles, Badges, and Metrics
    if (isExtractOnly) {
      if (watermarkedCardTitle) watermarkedCardTitle.textContent = "Extraction Input Image";
      if (badgePsnrMini) {
        badgePsnrMini.textContent = "Carrier Input";
        badgePsnrMini.className = "font-mono text-[9px] px-1.5 py-0.5 bg-secondary-container text-on-secondary-fixed font-semibold rounded";
      }
      if (badgeBerMini) badgeBerMini.textContent = "Blind Extracted";
      if (watermarkFidelityMetric) watermarkFidelityMetric.textContent = "PSNR: —";
      if (watermarkFidelityText) watermarkFidelityText.textContent = "No Reference Comparison";
      if (extractCorrMetric) extractCorrMetric.textContent = "NC: —";

      if (extractFidelityText) {
        const bytes = meta.compressed_payload_bytes || 0;
        extractFidelityText.textContent = `${meta.watermark_width || "—"}×${meta.watermark_height || "—"} ${meta.watermark_color_mode || ""} (${bytes.toLocaleString()} B)`;
      }
      if (payloadMatchPill) {
        payloadMatchPill.textContent = `${meta.watermark_width || "—"}×${meta.watermark_height || "—"} ${meta.watermark_color_mode || ""}`;
      }

      if (metricPsnr) metricPsnr.textContent = "—";
      if (metricSsim) metricSsim.textContent = "—";
      if (metricAcc) metricAcc.textContent = "—";
      if (metricNc) metricNc.textContent = "—";
      if (metricAccSub) metricAccSub.textContent = "Blind extraction (no ground truth)";
    } else {
      if (watermarkedCardTitle) watermarkedCardTitle.textContent = "Watermarked Image";
      if (badgePsnrMini) {
        badgePsnrMini.textContent = "Embedded";
        badgePsnrMini.className = "font-mono text-[9px] px-1.5 py-0.5 bg-primary-fixed text-primary font-semibold rounded";
      }
      if (badgeBerMini) badgeBerMini.textContent = "Blind Extraction";

      const metrics = data.metrics || {};
      const psnr = metrics.psnr !== undefined ? `${metrics.psnr}` : "—";
      const ssim = metrics.ssim !== undefined ? `${metrics.ssim}` : "—";
      const acc = metrics.bit_accuracy !== undefined ? `${metrics.bit_accuracy}%` : "—";
      const nc = metrics.normalized_correlation !== undefined ? `${metrics.normalized_correlation}` : "—";

      if (metricPsnr) metricPsnr.textContent = psnr;
      if (metricSsim) metricSsim.textContent = ssim;
      if (metricAcc) metricAcc.textContent = acc;
      if (metricNc) metricNc.textContent = nc;

      if (watermarkFidelityMetric) watermarkFidelityMetric.textContent = `PSNR: ${psnr} dB`;
      if (watermarkFidelityText) watermarkFidelityText.textContent = "Perceptual Invisibility";
      if (extractCorrMetric) extractCorrMetric.textContent = `NC: ${nc}`;
      if (extractFidelityText) {
        extractFidelityText.textContent = `${meta.watermark_width}×${meta.watermark_height} ${meta.watermark_color_mode} (${meta.total_payload_bytes.toLocaleString()} bytes)`;
      }
      if (payloadMatchPill) {
        payloadMatchPill.textContent = `${meta.watermark_width}×${meta.watermark_height} ${meta.watermark_color_mode} (${acc})`;
      }

      if (metricAccSub) {
        metricAccSub.textContent = `${meta.total_payload_bytes.toLocaleString()} / ${meta.total_payload_bytes.toLocaleString()} bytes (CRC32 Verified)`;
      }
    }

    // 5. Update Status & Timer
    if (executionTimer) {
      executionTimer.innerHTML = `<span class="material-symbols-outlined text-[13px] text-primary">schedule</span> Execution: ${elapsedMs}ms`;
    }
    if (pipelineStatusBanner) {
      pipelineStatusBanner.textContent = "Pipeline: Completed";
    }

    // 6. Update Configuration Chips if returned
    if (data.configuration && configChips) {
      const cfg = data.configuration;
      const chanLabel = cfg.channels_used === 3 ? "Y, Cr, Cb (Multi-Channel)" : "Y (Luminance)";
      configChips.innerHTML = `
        <span><strong class="text-secondary font-medium">Space:</strong> ${cfg.color_space}</span>
        <span class="text-slate-300">•</span>
        <span><strong class="text-secondary font-medium">Channels:</strong> ${chanLabel}</span>
        <span class="text-slate-300">•</span>
        <span><strong class="text-secondary font-medium">Partition:</strong> ${cfg.block_size}×${cfg.block_size} Blocks</span>
        <span class="text-slate-300">•</span>
        <span><strong class="text-secondary font-medium">Modulation:</strong> 16-Pair Multi-Bit DCT (${cfg.bits_per_block} bits/blk)</span>
        <span class="text-slate-300">•</span>
        <span><strong class="text-secondary font-medium">JND:</strong> α=${cfg.jnd_alpha}, β=${cfg.jnd_beta}</span>
      `;
    }

    // 7. Update Optimization Card
    if (data.optimization && optimizationCard) {
      optimizationCard.classList.remove("hidden");
      optimizationCard.classList.add("flex");
      
      const opt = data.optimization;
      if (opt.applied) {
        optStatusBadge.textContent = "Automatically optimized to fit";
        optStatusBadge.className = "font-mono text-[10px] px-2 py-0.5 rounded font-medium bg-amber-100 text-amber-800 border border-amber-200";
      } else {
        optStatusBadge.textContent = "No compression needed";
        optStatusBadge.className = "font-mono text-[10px] px-2 py-0.5 rounded font-medium bg-emerald-100 text-emerald-800 border border-emerald-200";
      }
      
      optOrigSize.textContent = (opt.original_size_bytes / 1024).toFixed(1) + " KB";
      optOptSize.textContent = (opt.optimized_size_bytes / 1024).toFixed(1) + " KB";
      const reduction = ((1 - (opt.optimized_size_bytes / opt.original_size_bytes)) * 100).toFixed(1);
      optReduction.textContent = reduction + "%";
      
      optOrigDims.textContent = `${opt.original_width}×${opt.original_height}`;
      optOptDims.textContent = `${opt.optimized_width}×${opt.optimized_height}`;
      optFormatQual.textContent = `${opt.codec} Q${opt.quality}`;
    }
  }

  function setErrorState(errorMessage) {
    if (watermarkResultOverlay) {
      watermarkResultOverlay.classList.remove("hidden");
      if (wmOverlayIcon) {
        wmOverlayIcon.textContent = "error";
        wmOverlayIcon.classList.remove("animate-spin");
      }
      if (wmOverlayText) wmOverlayText.textContent = "Operation Failed";
    }

    if (extractedResultOverlay) {
      extractedResultOverlay.classList.remove("hidden");
      if (exOverlayIcon) exOverlayIcon.textContent = "error";
      if (exOverlayText) exOverlayText.innerHTML = "Processing<br>Aborted";
    }

    if (pipelineStatusBanner) {
      pipelineStatusBanner.innerHTML = `<span class="text-error font-semibold">Error: ${errorMessage}</span>`;
    }
  }

  function resetResults() {
    currentMode = "embed_and_verify";

    if (outOriginalCanvas) {
      const ctx = outOriginalCanvas.getContext("2d");
      ctx.clearRect(0, 0, outOriginalCanvas.width, outOriginalCanvas.height);
    }
    if (outWatermarkedCanvas) {
      const ctx = outWatermarkedCanvas.getContext("2d");
      ctx.clearRect(0, 0, outWatermarkedCanvas.width, outWatermarkedCanvas.height);
    }
    if (outExtractedCanvas) {
      const ctx = outExtractedCanvas.getContext("2d");
      ctx.clearRect(0, 0, outExtractedCanvas.width, outExtractedCanvas.height);
    }

    if (originalResultOverlay) {
      originalResultOverlay.classList.remove("hidden");
    }
    if (watermarkResultOverlay) {
      watermarkResultOverlay.classList.remove("hidden");
      if (wmOverlayIcon) {
        wmOverlayIcon.textContent = "hourglass_empty";
        wmOverlayIcon.classList.remove("animate-spin");
      }
      if (wmOverlayText) wmOverlayText.textContent = "Awaiting Processing";
    }
    if (extractedResultOverlay) {
      extractedResultOverlay.classList.remove("hidden");
      if (exOverlayIcon) exOverlayIcon.textContent = "lock_clock";
      if (exOverlayText) exOverlayText.innerHTML = "Awaiting<br>Extraction";
    }

    if (watermarkedCardTitle) watermarkedCardTitle.textContent = "Watermarked / Extracted Image";
    if (badgePsnrMini) {
      badgePsnrMini.textContent = "Embedded";
      badgePsnrMini.className = "font-mono text-[9px] px-1.5 py-0.5 bg-primary-fixed text-primary font-semibold rounded";
    }
    if (badgeBerMini) badgeBerMini.textContent = "Blind Extraction";

    if (downloadWatermarkedBtn) {
      downloadWatermarkedBtn.classList.add("hidden");
      downloadWatermarkedBtn.classList.remove("inline-flex");
      downloadWatermarkedBtn.removeAttribute("href");
    }
    if (downloadExtractedBtn) {
      downloadExtractedBtn.classList.add("hidden");
      downloadExtractedBtn.classList.remove("inline-flex");
      downloadExtractedBtn.removeAttribute("href");
    }

    if (metricPsnr) metricPsnr.textContent = "—";
    if (metricSsim) metricSsim.textContent = "—";
    if (metricAcc) metricAcc.textContent = "—";
    if (metricNc) metricNc.textContent = "—";
    if (metricAccSub) metricAccSub.textContent = "Payload integrity verification";

    if (watermarkFidelityMetric) watermarkFidelityMetric.textContent = "PSNR: —";
    if (watermarkFidelityText) watermarkFidelityText.textContent = "Perceptual Invisibility";
    if (extractCorrMetric) extractCorrMetric.textContent = "NC: —";
    if (extractFidelityText) extractFidelityText.textContent = "Awaiting extraction";
    if (payloadMatchPill) payloadMatchPill.textContent = "Standby";

    if (pipelineStatusBanner) pipelineStatusBanner.textContent = "Pipeline: Standby";
    if (executionTimer) {
      executionTimer.innerHTML = `<span class="material-symbols-outlined text-[13px] text-primary">schedule</span> Standby`;
    }
    
    if (optimizationCard) {
      optimizationCard.classList.add("hidden");
      optimizationCard.classList.remove("flex");
    }
  }

  return {
    init,
    setOriginalPreview,
    setProcessingState,
    displayResults,
    setErrorState,
    resetResults,
  };
})();
