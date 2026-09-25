/**
 * processing.js - Orchestrates backend API call, loading states, and responsive
 * progressive estimation progress bars for both images and videos.
 */

const Processing = (function () {
  const runBtn = document.getElementById("runWatermarkBtn");
  const runSpinner = document.getElementById("runSpinner");
  const runBtnText = document.getElementById("runBtnText");

  const statusBadge = document.getElementById("statusBadge");
  const statusIndicator = document.getElementById("statusIndicator");
  const statusLabel = document.getElementById("statusLabel");

  // Progress Card Elements
  const progressCard = document.getElementById("processingProgressCard");
  const progressIcon = document.getElementById("progressIcon");
  const progressTitle = document.getElementById("progressTitle");
  const progressStageBadge = document.getElementById("progressStageBadge");
  const progressTimer = document.getElementById("progressTimer");
  const progressPercentBadge = document.getElementById("progressPercentBadge");
  const progressBarFill = document.getElementById("progressBarFill");
  const progressStepText = document.getElementById("progressStepText");
  const progressSubDetail = document.getElementById("progressSubDetail");

  // In-Overlay Mini Progress Elements
  const overlayProgressContainer = document.getElementById("overlayProgressContainer");
  const overlayProgressBarFill = document.getElementById("overlayProgressBarFill");
  const overlayProgressPercent = document.getElementById("overlayProgressPercent");

  let progressInterval = null;
  let currentStartTime = 0;

  function setSystemStatus(state) {
    if (!statusBadge || !statusIndicator || !statusLabel) return;

    if (state === "ready") {
      statusBadge.className =
        "flex items-center gap-1.5 px-2.5 py-0.5 rounded-full font-mono text-[11px] font-semibold bg-secondary-container text-on-secondary-fixed border border-primary/20";
      statusIndicator.className = "w-2 h-2 rounded-full bg-primary animate-pulse";
      statusLabel.textContent = "Ready";
    } else if (state === "processing") {
      statusBadge.className =
        "flex items-center gap-1.5 px-2.5 py-0.5 rounded-full font-mono text-[11px] font-semibold bg-primary text-on-primary border border-primary-container shadow-xs";
      statusIndicator.className = "w-2 h-2 rounded-full bg-white animate-ping";
      statusLabel.textContent = "Processing";
    } else if (state === "complete") {
      statusBadge.className =
        "flex items-center gap-1.5 px-2.5 py-0.5 rounded-full font-mono text-[11px] font-semibold bg-primary-fixed text-on-primary-fixed-variant border border-primary/30";
      statusIndicator.className = "w-2 h-2 rounded-full bg-primary";
      statusLabel.textContent = "Completed";
    } else if (state === "error") {
      statusBadge.className =
        "flex items-center gap-1.5 px-2.5 py-0.5 rounded-full font-mono text-[11px] font-semibold bg-error-container text-on-error-container border border-error/30";
      statusIndicator.className = "w-2 h-2 rounded-full bg-error";
      statusLabel.textContent = "Error";
    }
  }

  // Multi-stage profiles for realistic progressive estimation
  const STAGES = {
    image_embed: [
      { min: 0, max: 25, badge: "Stage 1/4", title: "Watermarking Image (DCT + JND)...", step: "Color-Space Conversion & 8×8 Grid Partitioning", sub: "BGR → YCrCb (Y channel)" },
      { min: 25, max: 55, badge: "Stage 2/4", title: "Watermarking Image (DCT + JND)...", step: "2D-DCT Transformation & Perceptual JND Masking", sub: "Variance σ, α=2.0, β=0.1" },
      { min: 55, max: 82, badge: "Stage 3/4", title: "Watermarking Image (DCT + JND)...", step: "16-Pair Differential DCT Modulation", sub: "C(3,2) ↔ C(2,3) embedding" },
      { min: 82, max: 100, badge: "Stage 4/4", title: "Watermarking Image (DCT + JND)...", step: "IDCT Reconstruction & Blind CRC32 Verification", sub: "Integrity check" },
    ],
    image_extract: [
      { min: 0, max: 30, badge: "Stage 1/3", title: "Extracting Watermark...", step: "Luminance Extraction & 8×8 Block Partitioning", sub: "Y channel analysis" },
      { min: 30, max: 70, badge: "Stage 2/3", title: "Extracting Watermark...", step: "Differential DCT Coefficient Sign Demodulation", sub: "16 bits/block extraction" },
      { min: 70, max: 100, badge: "Stage 3/3", title: "Extracting Watermark...", step: "Decompressing Payload & Blind CRC32 Verification", sub: "CRC32 checksum test" },
    ],
    video_embed: [
      { min: 0, max: 18, badge: "Stage 1/4", title: "Processing Video Stream (DCT + JND)...", step: "Stream Probing & Worker Queue Allocation", sub: "Bounded queue setup" },
      { min: 18, max: 65, badge: "Stage 2/4", title: "Processing Video Stream (DCT + JND)...", step: "Multi-Threaded Frame Watermarking", sub: "Parallel DCT + JND pipeline" },
      { min: 65, max: 85, badge: "Stage 3/4", title: "Processing Video Stream (DCT + JND)...", step: "Lossless Frame Assembly & Video Container Muxing", sub: "Video encoding" },
      { min: 85, max: 100, badge: "Stage 4/4", title: "Processing Video Stream (DCT + JND)...", step: "Multi-Frame Sampling & CRC32 Verification", sub: "Temporal consistency" },
    ],
    video_extract: [
      { min: 0, max: 20, badge: "Stage 1/3", title: "Extracting from Video...", step: "Video Stream Probing & Sampling Grid Setup", sub: "Frame selection" },
      { min: 20, max: 72, badge: "Stage 2/3", title: "Extracting from Video...", step: "Parallel Frame DCT Extraction", sub: "Differential sign detection" },
      { min: 72, max: 100, badge: "Stage 3/3", title: "Extracting from Video...", step: "Multi-Frame Voting & CRC32 Validation", sub: "Majority rule decoding" },
    ],
  };

  function getProfileKey(isVideo, isExtractOnly) {
    if (isVideo) {
      return isExtractOnly ? "video_extract" : "video_embed";
    }
    return isExtractOnly ? "image_extract" : "image_embed";
  }

  function startProgress(isVideo, isExtractOnly) {
    if (progressInterval) clearInterval(progressInterval);
    currentStartTime = performance.now();

    const profileKey = getProfileKey(isVideo, isExtractOnly);
    const stageList = STAGES[profileKey];
    const targetDuration = isVideo ? (isExtractOnly ? 2800 : 4800) : (isExtractOnly ? 900 : 1400);

    // Show Progress Card
    if (progressCard) {
      progressCard.classList.remove("hidden");
      progressCard.classList.add("flex");
    }

    // Reset Progress Card UI elements
    if (progressIcon) {
      progressIcon.textContent = "progress_activity";
      progressIcon.className = "material-symbols-outlined text-[18px] text-primary animate-spin shrink-0";
    }
    if (progressBarFill) {
      progressBarFill.style.width = "4%";
      progressBarFill.className = "h-full bg-primary rounded-full transition-all duration-150 ease-out relative overflow-hidden progress-bar-shimmer";
    }
    if (progressPercentBadge) {
      progressPercentBadge.textContent = "4%";
      progressPercentBadge.className = "px-2 py-0.5 rounded font-bold bg-primary-fixed text-primary text-[10px] font-mono";
    }
    if (progressStageBadge) {
      progressStageBadge.textContent = stageList[0].badge;
      progressStageBadge.className = "font-mono text-[9px] px-1.5 py-0.5 rounded bg-surface-container text-on-surface-variant border border-slate-200";
    }
    if (progressTitle) {
      progressTitle.textContent = stageList[0].title;
    }
    if (progressStepText) {
      progressStepText.textContent = stageList[0].step;
    }
    if (progressSubDetail) {
      progressSubDetail.textContent = stageList[0].sub;
    }
    if (progressTimer) {
      progressTimer.textContent = "0.0s elapsed";
    }

    // Overlay mini progress
    if (overlayProgressContainer) {
      overlayProgressContainer.classList.remove("hidden");
    }
    if (overlayProgressBarFill) {
      overlayProgressBarFill.style.width = "4%";
    }
    if (overlayProgressPercent) {
      overlayProgressPercent.classList.remove("hidden");
      overlayProgressPercent.textContent = "4%";
    }

    progressInterval = setInterval(() => {
      const elapsed = performance.now() - currentStartTime;
      const elapsedSec = (elapsed / 1000).toFixed(1);

      // Decelerating asymptotic curve approaching 95%
      const factor = 1 - Math.exp(-elapsed / (targetDuration * 0.45));
      const percent = Math.min(95, Math.max(5, Math.round(factor * 95)));

      // Find current stage
      let currentStage = stageList[0];
      for (const st of stageList) {
        if (percent >= st.min) {
          currentStage = st;
        }
      }

      if (progressBarFill) progressBarFill.style.width = `${percent}%`;
      if (progressPercentBadge) progressPercentBadge.textContent = `${percent}%`;
      if (progressTimer) progressTimer.textContent = `${elapsedSec}s elapsed`;
      if (progressStageBadge) progressStageBadge.textContent = currentStage.badge;
      if (progressStepText) progressStepText.textContent = currentStage.step;
      if (progressSubDetail) progressSubDetail.textContent = currentStage.sub;

      if (overlayProgressBarFill) overlayProgressBarFill.style.width = `${percent}%`;
      if (overlayProgressPercent) overlayProgressPercent.textContent = `${percent}%`;
    }, 80);
  }

  function completeProgress(isVideo, isExtractOnly, elapsedMs) {
    if (progressInterval) clearInterval(progressInterval);
    progressInterval = null;

    const elapsedSec = (elapsedMs / 1000).toFixed(2);

    if (progressBarFill) {
      progressBarFill.style.width = "100%";
      progressBarFill.className = "h-full rounded-full transition-all duration-200 ease-out relative overflow-hidden progress-bar-success";
    }
    if (progressPercentBadge) {
      progressPercentBadge.textContent = "100%";
      progressPercentBadge.className = "px-2 py-0.5 rounded font-bold bg-emerald-100 text-emerald-800 text-[10px] font-mono border border-emerald-300/50";
    }
    if (progressIcon) {
      progressIcon.textContent = "check_circle";
      progressIcon.className = "material-symbols-outlined text-[18px] text-emerald-600 shrink-0";
    }
    if (progressTitle) {
      if (isVideo) {
        progressTitle.textContent = isExtractOnly ? "Video Watermark Extracted" : "Video Watermarked & Verified";
      } else {
        progressTitle.textContent = isExtractOnly ? "Watermark Extracted" : "Watermarked & Verified";
      }
    }
    if (progressStageBadge) {
      progressStageBadge.textContent = "Completed";
      progressStageBadge.className = "font-mono text-[9px] px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 font-semibold";
    }
    if (progressStepText) {
      progressStepText.textContent = "Lossless blind extraction & CRC32 verification validated";
    }
    if (progressSubDetail) {
      progressSubDetail.textContent = `${elapsedSec}s elapsed`;
    }
    if (progressTimer) {
      progressTimer.textContent = `${elapsedSec}s total`;
    }

    if (overlayProgressBarFill) overlayProgressBarFill.style.width = "100%";
    if (overlayProgressPercent) overlayProgressPercent.textContent = "100%";

    // Fade out progress card after 3 seconds, or let it remain cleanly visible
    setTimeout(() => {
      if (overlayProgressContainer) overlayProgressContainer.classList.add("hidden");
      if (overlayProgressPercent) overlayProgressPercent.classList.add("hidden");
    }, 1500);
  }

  function errorProgress(errorMessage) {
    if (progressInterval) clearInterval(progressInterval);
    progressInterval = null;

    if (progressBarFill) {
      progressBarFill.className = "h-full rounded-full transition-all duration-200 relative overflow-hidden progress-bar-error";
    }
    if (progressPercentBadge) {
      progressPercentBadge.textContent = "Failed";
      progressPercentBadge.className = "px-2 py-0.5 rounded font-bold bg-error-container text-on-error-container text-[10px] font-mono border border-error/30";
    }
    if (progressIcon) {
      progressIcon.textContent = "error";
      progressIcon.className = "material-symbols-outlined text-[18px] text-error shrink-0";
    }
    if (progressTitle) {
      progressTitle.textContent = "Processing Failed";
    }
    if (progressStageBadge) {
      progressStageBadge.textContent = "Aborted";
      progressStageBadge.className = "font-mono text-[9px] px-1.5 py-0.5 rounded bg-error-container text-on-error-container border border-error/30 font-semibold";
    }
    if (progressStepText) {
      progressStepText.textContent = errorMessage || "Operation failed.";
    }
    if (progressSubDetail) {
      progressSubDetail.textContent = "Error";
    }

    if (overlayProgressContainer) overlayProgressContainer.classList.add("hidden");
    if (overlayProgressPercent) overlayProgressPercent.classList.add("hidden");
  }

  function resetProgress() {
    if (progressInterval) clearInterval(progressInterval);
    progressInterval = null;

    if (progressCard) {
      progressCard.classList.add("hidden");
      progressCard.classList.remove("flex");
    }
    if (progressBarFill) {
      progressBarFill.style.width = "0%";
      progressBarFill.className = "h-full bg-primary rounded-full transition-all duration-150 ease-out relative overflow-hidden progress-bar-shimmer";
    }
    if (progressPercentBadge) {
      progressPercentBadge.textContent = "0%";
      progressPercentBadge.className = "px-2 py-0.5 rounded font-bold bg-primary-fixed text-primary text-[10px] font-mono";
    }
    if (progressIcon) {
      progressIcon.textContent = "progress_activity";
      progressIcon.className = "material-symbols-outlined text-[18px] text-primary animate-spin shrink-0";
    }
    if (progressTimer) progressTimer.textContent = "0.0s elapsed";
    if (overlayProgressContainer) overlayProgressContainer.classList.add("hidden");
    if (overlayProgressPercent) overlayProgressPercent.classList.add("hidden");
    if (overlayProgressBarFill) overlayProgressBarFill.style.width = "0%";
  }

  async function execute() {
    const coverFile = Upload.getCoverFile();
    const wmFile = Upload.getWatermarkFile();
    const isExtractOnly = !wmFile;
    const isVideo = Upload.isCoverVideo && Upload.isCoverVideo();

    if (!coverFile) {
      alert("Please select a cover image or video.");
      return;
    }

    // Set UI to processing
    setSystemStatus("processing");
    runBtn.disabled = true;

    if (isVideo) {
      runBtnText.textContent = isExtractOnly ? "Extracting from Video..." : "Processing Video (DCT + JND)...";
    } else {
      runBtnText.textContent = isExtractOnly ? "Extracting Watermark..." : "Embedding (DCT + JND)...";
    }

    runSpinner.textContent = "progress_activity";
    runSpinner.classList.add("animate-spin");

    Results.setProcessingState(isExtractOnly, isVideo);
    startProgress(isVideo, isExtractOnly);

    const startTime = performance.now();

    try {
      const formData = new FormData();
      formData.append("cover_image", coverFile);
      if (wmFile) {
        formData.append("watermark_image", wmFile);
      }
      if (isVideo) {
        formData.append("mode", "threaded");
      }
      const crcToggle = document.getElementById("enforceCrcToggle");
      const enforceCrc = crcToggle ? crcToggle.checked : true;
      formData.append("enforce_crc", enforceCrc ? "true" : "false");

      const response = await fetch("/api/watermark", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();
      const elapsedMs = Math.round(performance.now() - startTime);

      if (!response.ok || !data.success) {
        throw new Error(data.error || "Watermarking operation failed.");
      }

      // Complete progress and render successful results
      completeProgress(isVideo, isExtractOnly, elapsedMs);
      Results.displayResults(data, elapsedMs);
      setSystemStatus("complete");

      // Success animation on button
      runSpinner.classList.remove("animate-spin");
      runSpinner.textContent = "check";
      if (isVideo) {
        runBtnText.textContent = isExtractOnly ? "Watermark Extracted" : "Video Watermarked";
      } else {
        runBtnText.textContent = isExtractOnly ? "Watermark Extracted" : "Watermark Embedded";
      }

      setTimeout(() => {
        runSpinner.textContent = "play_arrow";
        if (isVideo) {
          runBtnText.textContent = isExtractOnly ? "Extract from Video" : "Watermark Video";
        } else {
          runBtnText.textContent = isExtractOnly ? "Extract Watermark" : "Run Watermarking";
        }
        runBtn.disabled = false;
      }, 2000);
    } catch (err) {
      console.error("Watermarking error:", err);
      setSystemStatus("error");
      errorProgress(err.message);
      Results.setErrorState(err.message);

      runSpinner.classList.remove("animate-spin");
      runSpinner.textContent = "play_arrow";
      if (isVideo) {
        runBtnText.textContent = isExtractOnly ? "Extract from Video" : "Watermark Video";
      } else {
        runBtnText.textContent = isExtractOnly ? "Extract Watermark" : "Run Watermarking";
      }
      runBtn.disabled = false;
    }
  }

  function init() {
    if (runBtn) {
      runBtn.addEventListener("click", execute);
    }
    const crcToggle = document.getElementById("enforceCrcToggle");
    const crcLabel = document.getElementById("crcToggleLabel");
    if (crcToggle && crcLabel) {
      crcToggle.addEventListener("change", () => {
        if (crcToggle.checked) {
          crcLabel.textContent = "Enforce CRC";
          crcLabel.className = "text-[11px] font-mono font-medium text-on-surface";
          if (crcToggle.parentElement) {
            crcToggle.parentElement.classList.remove("bg-amber-50", "border-amber-300");
            crcToggle.parentElement.classList.add("bg-surface-container-low", "border-slate-200");
          }
        } else {
          crcLabel.textContent = "CRC Check: Off";
          crcLabel.className = "text-[11px] font-mono font-semibold text-amber-800";
          if (crcToggle.parentElement) {
            crcToggle.parentElement.classList.remove("bg-surface-container-low", "border-slate-200");
            crcToggle.parentElement.classList.add("bg-amber-50", "border-amber-300");
          }
        }
      });
    }
    setSystemStatus("ready");
  }

  return {
    init,
    setSystemStatus,
    execute,
    resetProgress,
  };
})();

