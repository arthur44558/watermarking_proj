/**
 * results.js - Handles rendering of real watermarking results, metrics, metadata,
 * downloads, and lightbox zoom for both Image and Video outputs.
 */

const Results = (function () {
  const outOriginalCanvas = document.getElementById("outOriginalCanvas");
  const outOriginalVideo = document.getElementById("outOriginalVideo");
  const outWatermarkedCanvas = document.getElementById("outWatermarkedCanvas");
  const outWatermarkedVideo = document.getElementById("outWatermarkedVideo");
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

  const originalCardTitle = document.getElementById("originalCardTitle");
  const watermarkedCardTitle = document.getElementById("watermarkedCardTitle");
  const downloadWatermarkedBtn = document.getElementById("downloadWatermarkedBtn");
  const downloadWatermarkedBtnText = document.getElementById("downloadWatermarkedBtnText");
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

  // Video performance card elements
  const videoPerformanceCard = document.getElementById("videoPerformanceCard");
  const videoModeBadge = document.getElementById("videoModeBadge");
  const videoStreamInfo = document.getElementById("videoStreamInfo");
  const videoFpsMetric = document.getElementById("videoFpsMetric");
  const videoPeakRam = document.getElementById("videoPeakRam");
  const videoCrcStatus = document.getElementById("videoCrcStatus");

  let currentMode = "embed_and_verify";
  let isVideoResult = false;
  let watermarkedVideoUrl = null;
  let originalVideoUrl = null;

  function init() {
    // Click-to-zoom lightbox handlers
    if (outOriginalContainer) {
      outOriginalContainer.addEventListener("click", (e) => {
        if (e.target && e.target.tagName === "VIDEO") return;
        if (originalResultOverlay && !originalResultOverlay.classList.contains("hidden")) return;
        if (originalVideoUrl && outOriginalVideo && !outOriginalVideo.classList.contains("hidden")) {
          if (window.Lightbox) Lightbox.open(originalVideoUrl, "Original Video (Reference Baseline)", true);
        } else if (outOriginalCanvas && outOriginalCanvas.style.display !== "none") {
          if (window.Lightbox) Lightbox.open(outOriginalCanvas.toDataURL(), "Original Image (Reference Baseline)", false);
        }
      });
    }

    if (outWatermarkedContainer) {
      outWatermarkedContainer.addEventListener("click", (e) => {
        if (e.target && e.target.tagName === "VIDEO") return;
        if (watermarkResultOverlay && !watermarkResultOverlay.classList.contains("hidden")) return;
        if (watermarkedVideoUrl && outWatermarkedVideo && !outWatermarkedVideo.classList.contains("hidden")) {
          const title = currentMode === "extract_only" ? "Carrier Video (Input)" : "Watermarked Video (JND DCT)";
          if (window.Lightbox) Lightbox.open(watermarkedVideoUrl, title, true);
        } else if (outWatermarkedCanvas && outWatermarkedCanvas.style.display !== "none") {
          const title = currentMode === "extract_only" ? "Extraction Input Image" : "Watermarked Image (DCT + JND)";
          if (window.Lightbox) Lightbox.open(outWatermarkedCanvas.toDataURL(), title, false);
        }
      });
    }

    if (outExtractedContainer) {
      outExtractedContainer.addEventListener("click", () => {
        if (extractedResultOverlay && extractedResultOverlay.classList.contains("hidden")) {
          if (window.Lightbox) Lightbox.open(outExtractedCanvas.toDataURL(), "Extracted Watermark Image (Lossless)", false);
        }
      });
    }
  }

  function setOriginalPreview(source, w, h, isVideo = false) {
    if (isVideo && outOriginalVideo) {
      originalVideoUrl = typeof source === "string" ? source : "";
      if (outOriginalCanvas) outOriginalCanvas.style.display = "none";
      outOriginalVideo.classList.remove("hidden");
      outOriginalVideo.style.display = "block";
      outOriginalVideo.src = originalVideoUrl;
      if (originalCardTitle) originalCardTitle.textContent = "Original Video";
      if (originalResultOverlay) originalResultOverlay.classList.add("hidden");
    } else if (outOriginalCanvas) {
      originalVideoUrl = null;
      if (outOriginalVideo) {
        outOriginalVideo.pause();
        outOriginalVideo.src = "";
        outOriginalVideo.classList.add("hidden");
        outOriginalVideo.style.display = "none";
      }
      outOriginalCanvas.style.display = "block";
      outOriginalCanvas.width = w;
      outOriginalCanvas.height = h;
      const ctx = outOriginalCanvas.getContext("2d");
      ctx.clearRect(0, 0, w, h);
      ctx.drawImage(source, 0, 0);
      if (originalCardTitle) originalCardTitle.textContent = "Original Image";
      if (originalResultOverlay) originalResultOverlay.classList.add("hidden");
    }
  }

  function setProcessingState(isExtractOnly = false, isVideo = false) {
    currentMode = isExtractOnly ? "extract_only" : "embed_and_verify";

    if (watermarkResultOverlay) {
      watermarkResultOverlay.classList.remove("hidden");
      if (wmOverlayIcon) {
        wmOverlayIcon.textContent = "progress_activity";
        wmOverlayIcon.classList.add("animate-spin");
      }
      if (wmOverlayText) {
        if (isVideo) {
          wmOverlayText.textContent = isExtractOnly
            ? "Sampling & decoding video frames..."
            : "Processing video frame-by-frame (DCT+JND)...";
        } else {
          wmOverlayText.textContent = isExtractOnly
            ? "Analyzing host image..."
            : "Embedding payload in DCT domain...";
        }
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
      if (isVideo) {
        pipelineStatusBanner.textContent = isExtractOnly
          ? "Pipeline: Extracting Video Watermark..."
          : "Pipeline: Processing Video Stream...";
      } else {
        pipelineStatusBanner.textContent = isExtractOnly
          ? "Pipeline: Extracting..."
          : "Pipeline: Embedding & Verifying...";
      }
    }
  }

  function displayResults(data, elapsedMs) {
    currentMode = data.mode || "embed_and_verify";
    const isExtractOnly = currentMode === "extract_only";
    const isVideo = data.media_type === "video";
    isVideoResult = isVideo;
    const meta = data.metadata || {};

    // 1. Render Watermarked / Input Media
    if (isVideo && data.watermarked_video && outWatermarkedVideo) {
      // VIDEO DISPLAY
      watermarkedVideoUrl = data.watermarked_video;
      if (outWatermarkedCanvas) outWatermarkedCanvas.style.display = "none";
      outWatermarkedVideo.classList.remove("hidden");
      outWatermarkedVideo.style.display = "block";
      outWatermarkedVideo.src = `${data.watermarked_video}?t=${Date.now()}`;
      outWatermarkedVideo.load();

      if (watermarkResultOverlay) {
        watermarkResultOverlay.classList.add("hidden");
      }
    } else if (data.watermarked_image && outWatermarkedCanvas) {
      // IMAGE DISPLAY
      watermarkedVideoUrl = null;
      if (outWatermarkedVideo) {
        outWatermarkedVideo.pause();
        outWatermarkedVideo.src = "";
        outWatermarkedVideo.classList.add("hidden");
        outWatermarkedVideo.style.display = "none";
      }
      outWatermarkedCanvas.style.display = "block";

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

    // 2. Render Extracted Watermark Image
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
    if (downloadWatermarkedBtn) {
      if (isVideo && data.watermarked_video) {
        const vidExt = (data.video_info && data.video_info.container) ? data.video_info.container : (data.watermarked_video.split('.').pop() || "mp4");
        downloadWatermarkedBtn.href = data.watermarked_video;
        downloadWatermarkedBtn.download = isExtractOnly ? `input_carrier_video.${vidExt}` : `watermarked_video.${vidExt}`;
        if (downloadWatermarkedBtnText) downloadWatermarkedBtnText.textContent = "Download Video";
        downloadWatermarkedBtn.classList.remove("hidden");
        downloadWatermarkedBtn.classList.add("inline-flex");
      } else if (data.watermarked_image) {
        downloadWatermarkedBtn.href = data.watermarked_image;
        downloadWatermarkedBtn.download = isExtractOnly ? "input_carrier.png" : "watermarked_image.png";
        if (downloadWatermarkedBtnText) downloadWatermarkedBtnText.textContent = "Download";
        downloadWatermarkedBtn.classList.remove("hidden");
        downloadWatermarkedBtn.classList.add("inline-flex");
      }
    }

    if (downloadExtractedBtn && data.extracted_watermark) {
      downloadExtractedBtn.href = data.extracted_watermark;
      downloadExtractedBtn.download = "extracted_watermark.png";
      downloadExtractedBtn.classList.remove("hidden");
      downloadExtractedBtn.classList.add("inline-flex");
    }

    // CRC verification state check
    const ext = data.extraction || {};
    const crcMatch = data.crc_match !== undefined ? data.crc_match : (ext.crc_match !== undefined ? ext.crc_match : true);
    const crcStatus = data.crc_status || ext.crc_status || "";
    const enforceCrc = data.enforce_crc !== undefined ? data.enforce_crc : (ext.enforce_crc !== undefined ? ext.enforce_crc : true);
    const hasCrcMismatch = (crcMatch === false) || crcStatus.toLowerCase().includes("mismatch");

    // 4. Update UI Card Titles, Badges, and Metrics
    if (isExtractOnly) {
      if (watermarkedCardTitle) {
        watermarkedCardTitle.textContent = isVideo ? "Extraction Input Video" : "Extraction Input Image";
      }
      if (badgePsnrMini) {
        badgePsnrMini.textContent = isVideo ? "Video Carrier" : "Carrier Input";
        badgePsnrMini.className =
          "font-mono text-[9px] px-1.5 py-0.5 bg-secondary-container text-on-secondary-fixed font-semibold rounded";
      }
      if (badgeBerMini) {
        if (hasCrcMismatch) {
          badgeBerMini.textContent = "CRC Mismatch";
          badgeBerMini.className = "font-mono text-[9px] px-1.5 py-0.5 bg-amber-100 text-amber-800 border border-amber-300 font-semibold rounded";
        } else if (!enforceCrc) {
          badgeBerMini.textContent = "CRC Disabled";
          badgeBerMini.className = "font-mono text-[9px] px-1.5 py-0.5 bg-amber-100 text-amber-800 border border-amber-300 font-semibold rounded";
        } else {
          badgeBerMini.textContent = isVideo ? "Video Frame Extracted" : "Blind Extracted";
          badgeBerMini.className = "font-mono text-[9px] px-1.5 py-0.5 bg-secondary-container text-on-secondary-fixed font-semibold rounded";
        }
      }
      if (watermarkFidelityMetric) watermarkFidelityMetric.textContent = "PSNR: —";
      if (watermarkFidelityText) watermarkFidelityText.textContent = "No Reference Comparison";
      if (extractCorrMetric) extractCorrMetric.textContent = "NC: —";

      if (extractFidelityText) {
        const bytes = meta.compressed_payload_bytes || 0;
        extractFidelityText.textContent = `${meta.watermark_width || "—"}×${meta.watermark_height || "—"} ${meta.watermark_color_mode || ""} (${bytes.toLocaleString()} B)`;
      }

      if (metricPsnr) metricPsnr.textContent = "—";
      if (metricSsim) metricSsim.textContent = "—";
      if (metricAcc) metricAcc.textContent = "—";
      if (metricNc) metricNc.textContent = "—";
      if (metricAccSub) {
        if (hasCrcMismatch) {
          metricAccSub.textContent = isVideo ? "Sampled frames (CRC Mismatch)" : "Extracted payload (CRC Mismatch)";
        } else if (!enforceCrc) {
          metricAccSub.textContent = isVideo ? "Sampled frames (CRC Disabled)" : "Extracted payload (CRC Disabled)";
        } else {
          metricAccSub.textContent = "Blind extraction (no ground truth)";
        }
      }
    } else {
      if (watermarkedCardTitle) {
        watermarkedCardTitle.textContent = isVideo ? "Watermarked Video" : "Watermarked Image";
      }
      if (badgePsnrMini) {
        badgePsnrMini.textContent = isVideo ? "Video Embedded" : "Embedded";
        badgePsnrMini.className =
          "font-mono text-[9px] px-1.5 py-0.5 bg-primary-fixed text-primary font-semibold rounded";
      }
      if (badgeBerMini) {
        if (hasCrcMismatch) {
          badgeBerMini.textContent = "CRC Mismatch";
          badgeBerMini.className = "font-mono text-[9px] px-1.5 py-0.5 bg-amber-100 text-amber-800 border border-amber-300 font-semibold rounded";
        } else if (!enforceCrc) {
          badgeBerMini.textContent = "CRC Disabled";
          badgeBerMini.className = "font-mono text-[9px] px-1.5 py-0.5 bg-amber-100 text-amber-800 border border-amber-300 font-semibold rounded";
        } else {
          badgeBerMini.textContent = isVideo ? "Multi-Frame Verified" : "Blind Extraction";
          badgeBerMini.className = "font-mono text-[9px] px-1.5 py-0.5 bg-surface-container border border-slate-200 text-secondary font-semibold rounded";
        }
      }

      const metrics = data.metrics || {};
      const psnr = metrics.psnr !== undefined ? `${metrics.psnr}` : "—";
      const ssim = metrics.ssim !== undefined ? `${metrics.ssim}` : "—";
      const acc = metrics.bit_accuracy !== undefined ? `${metrics.bit_accuracy}%` : "—";
      const nc = metrics.normalized_correlation !== undefined ? `${metrics.normalized_correlation}` : "—";

      if (metricPsnr) metricPsnr.textContent = psnr;
      if (metricSsim) metricSsim.textContent = ssim;
      if (metricAcc) metricAcc.textContent = acc;
      if (metricNc) metricNc.textContent = nc;

      if (watermarkFidelityMetric) {
        watermarkFidelityMetric.textContent = isVideo ? `PSNR: ${psnr} dB (Sampled)` : `PSNR: ${psnr} dB`;
      }
      if (watermarkFidelityText) {
        if (isVideo && data.performance) {
          watermarkFidelityText.textContent = `${data.performance.average_fps} FPS • Peak RAM: ${data.performance.peak_ram_mb} MB`;
        } else {
          watermarkFidelityText.textContent = "Perceptual Invisibility";
        }
      }
      if (extractCorrMetric) extractCorrMetric.textContent = `NC: ${nc}`;
      if (extractFidelityText) {
        extractFidelityText.textContent = `${meta.watermark_width}×${meta.watermark_height} ${meta.watermark_color_mode} (${meta.total_payload_bytes ? meta.total_payload_bytes.toLocaleString() : 0} bytes)`;
      }

      if (metricAccSub) {
        if (hasCrcMismatch) {
          if (isVideo && data.extraction) {
            metricAccSub.textContent = `${data.extraction.valid_sampled_frames}/${data.extraction.total_sampled_frames} Frames (CRC Mismatch)`;
          } else {
            metricAccSub.textContent = `${meta.total_payload_bytes ? meta.total_payload_bytes.toLocaleString() : 0} bytes (CRC Mismatch)`;
          }
        } else if (!enforceCrc) {
          if (isVideo && data.extraction) {
            metricAccSub.textContent = `${data.extraction.valid_sampled_frames}/${data.extraction.total_sampled_frames} Frames (CRC Disabled)`;
          } else {
            metricAccSub.textContent = `${meta.total_payload_bytes ? meta.total_payload_bytes.toLocaleString() : 0} bytes (CRC Disabled)`;
          }
        } else {
          if (isVideo && data.extraction) {
            metricAccSub.textContent = `${data.extraction.valid_sampled_frames}/${data.extraction.total_sampled_frames} Sampled Frames Verified (CRC32)`;
          } else if (meta.total_payload_bytes) {
            metricAccSub.textContent = `${meta.total_payload_bytes.toLocaleString()} / ${meta.total_payload_bytes.toLocaleString()} bytes (CRC32 Verified)`;
          }
        }
      }
    }

    // Update Payload Match Pill with CRC resilience
    if (payloadMatchPill) {
      if (hasCrcMismatch) {
        payloadMatchPill.className = "px-2 py-0.5 rounded font-semibold bg-amber-100 text-amber-800 border border-amber-300 text-[11px]";
        payloadMatchPill.textContent = "CRC Mismatch";
      } else if (!enforceCrc) {
        payloadMatchPill.className = "px-2 py-0.5 rounded font-semibold bg-amber-100 text-amber-800 border border-amber-300 text-[11px]";
        payloadMatchPill.textContent = "CRC Disabled";
      } else {
        payloadMatchPill.className = "px-2 py-0.5 rounded font-semibold bg-primary-fixed/60 text-primary border border-primary/20 text-[11px]";
        payloadMatchPill.textContent = isExtractOnly
          ? `${meta.watermark_width || "—"}×${meta.watermark_height || "—"} ${meta.watermark_color_mode || ""}`
          : `${meta.watermark_width}×${meta.watermark_height} (${(data.metrics && data.metrics.bit_accuracy !== undefined) ? `${data.metrics.bit_accuracy}%` : "—"})`;
      }
    }

    // 5. Update Status & Timer
    if (executionTimer) {
      executionTimer.innerHTML = `<span class="material-symbols-outlined text-[13px] text-primary">schedule</span> Execution: ${elapsedMs}ms`;
    }
    if (pipelineStatusBanner) {
      pipelineStatusBanner.textContent = isVideo ? "Pipeline: Video Stream Completed" : "Pipeline: Completed";
    }

    // 6. Update Configuration Chips
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
        ${isVideo ? `<span class="text-slate-300">•</span><span><strong class="text-primary font-medium">Mode:</strong> Bounded Video Pipeline</span>` : ""}
      `;
    }

    // 7. Video Performance Card
    if (isVideo && videoPerformanceCard) {
      videoPerformanceCard.classList.remove("hidden");
      videoPerformanceCard.classList.add("flex");

      const v = data.video_info || {};
      const perf = data.performance || {};
      const ext = data.extraction || {};

      if (videoModeBadge) {
        videoModeBadge.textContent = perf.processing_mode || "Threaded Video Pipeline";
      }
      if (videoStreamInfo) {
        videoStreamInfo.textContent = `${v.width || "—"}×${v.height || "—"} • ${v.duration_sec || 0}s (${v.frame_count || 0} frames)`;
      }
      if (videoFpsMetric) {
        videoFpsMetric.textContent = `${perf.average_fps || "—"} FPS (${perf.processing_time_sec || "—"}s total)`;
      }
      if (videoPeakRam) {
        videoPeakRam.textContent = `${perf.peak_ram_mb || "—"} MB (Δ +${perf.ram_increase_mb || 0} MB)`;
      }
      if (videoCrcStatus) {
        const consistent = ext.payload_consistent ? "Consistent" : "Discrepancy";
        const cStatus = ext.crc_status || (ext.crc_match === false ? "CRC Mismatch" : "Verified");
        videoCrcStatus.textContent = `${cStatus} • ${consistent} (${ext.valid_sampled_frames || 0}/${ext.total_sampled_frames || 0} f)`;
        if (ext.crc_match === false || (ext.crc_status && ext.crc_status.toLowerCase().includes("mismatch")) || ext.enforce_crc === false) {
          videoCrcStatus.className = "font-semibold text-amber-700 text-[11px]";
        } else {
          videoCrcStatus.className = "font-semibold text-emerald-700 text-[11px]";
        }
      }
    } else if (videoPerformanceCard) {
      videoPerformanceCard.classList.add("hidden");
      videoPerformanceCard.classList.remove("flex");
    }

    // 8. Watermark Optimization Card
    if (data.optimization && optimizationCard) {
      optimizationCard.classList.remove("hidden");
      optimizationCard.classList.add("flex");

      const opt = data.optimization;
      if (opt.applied) {
        optStatusBadge.textContent = "Automatically optimized to fit";
        optStatusBadge.className =
          "font-mono text-[10px] px-2 py-0.5 rounded font-medium bg-amber-100 text-amber-800 border border-amber-200";
      } else {
        optStatusBadge.textContent = "No compression needed";
        optStatusBadge.className =
          "font-mono text-[10px] px-2 py-0.5 rounded font-medium bg-emerald-100 text-emerald-800 border border-emerald-200";
      }

      optOrigSize.textContent = (opt.original_size_bytes / 1024).toFixed(1) + " KB";
      optOptSize.textContent = (opt.optimized_size_bytes / 1024).toFixed(1) + " KB";
      const reduction = ((1 - opt.optimized_size_bytes / opt.original_size_bytes) * 100).toFixed(1);
      optReduction.textContent = reduction + "%";

      optOrigDims.textContent = `${opt.original_width}×${opt.original_height}`;
      optOptDims.textContent = `${opt.optimized_width}×${opt.optimized_height}`;
      optFormatQual.textContent = `${opt.codec} Q${opt.quality}`;
    } else if (optimizationCard) {
      optimizationCard.classList.add("hidden");
      optimizationCard.classList.remove("flex");
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
      if (errorMessage && (errorMessage.toLowerCase().includes("crc32 mismatch") || errorMessage.toLowerCase().includes("crc mismatch"))) {
        pipelineStatusBanner.innerHTML = `<span class="text-error font-semibold">Error: CRC32 mismatch. Uncheck "Enforce CRC" to inspect candidate watermark.</span>`;
      } else {
        pipelineStatusBanner.innerHTML = `<span class="text-error font-semibold">Error: ${errorMessage}</span>`;
      }
    }
  }

  function resetResults() {
    currentMode = "embed_and_verify";
    isVideoResult = false;
    watermarkedVideoUrl = null;
    originalVideoUrl = null;

    if (outOriginalCanvas) {
      const ctx = outOriginalCanvas.getContext("2d");
      ctx.clearRect(0, 0, outOriginalCanvas.width, outOriginalCanvas.height);
      outOriginalCanvas.style.display = "block";
    }
    if (outOriginalVideo) {
      outOriginalVideo.pause();
      outOriginalVideo.src = "";
      outOriginalVideo.classList.add("hidden");
      outOriginalVideo.style.display = "none";
    }

    if (outWatermarkedCanvas) {
      const ctx = outWatermarkedCanvas.getContext("2d");
      ctx.clearRect(0, 0, outWatermarkedCanvas.width, outWatermarkedCanvas.height);
      outWatermarkedCanvas.style.display = "block";
    }
    if (outWatermarkedVideo) {
      outWatermarkedVideo.pause();
      outWatermarkedVideo.src = "";
      outWatermarkedVideo.classList.add("hidden");
      outWatermarkedVideo.style.display = "none";
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

    if (originalCardTitle) originalCardTitle.textContent = "Original Reference";
    if (watermarkedCardTitle) watermarkedCardTitle.textContent = "Watermarked / Extracted Media";
    if (badgePsnrMini) {
      badgePsnrMini.textContent = "Embedded";
      badgePsnrMini.className =
        "font-mono text-[9px] px-1.5 py-0.5 bg-primary-fixed text-primary font-semibold rounded";
    }
    if (badgeBerMini) badgeBerMini.textContent = "Blind Extraction";

    if (downloadWatermarkedBtn) {
      downloadWatermarkedBtn.classList.add("hidden");
      downloadWatermarkedBtn.classList.remove("inline-flex");
      downloadWatermarkedBtn.removeAttribute("href");
      if (downloadWatermarkedBtnText) downloadWatermarkedBtnText.textContent = "Download";
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
    if (payloadMatchPill) {
      payloadMatchPill.className = "px-2 py-0.5 rounded font-semibold bg-primary-fixed/60 text-primary border border-primary/20 text-[11px]";
      payloadMatchPill.textContent = "Standby";
    }
    if (videoCrcStatus) {
      videoCrcStatus.className = "font-semibold text-emerald-700 text-[11px]";
      videoCrcStatus.textContent = "—";
    }

    if (pipelineStatusBanner) pipelineStatusBanner.textContent = "Pipeline: Standby";
    if (executionTimer) {
      executionTimer.innerHTML = `<span class="material-symbols-outlined text-[13px] text-primary">schedule</span> Standby`;
    }

    if (optimizationCard) {
      optimizationCard.classList.add("hidden");
      optimizationCard.classList.remove("flex");
    }

    if (videoPerformanceCard) {
      videoPerformanceCard.classList.add("hidden");
      videoPerformanceCard.classList.remove("flex");
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
