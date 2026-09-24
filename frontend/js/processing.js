/**
 * processing.js - Orchestrates backend API call, loading states, and timing for images and videos.
 */

const Processing = (function () {
  const runBtn = document.getElementById("runWatermarkBtn");
  const runSpinner = document.getElementById("runSpinner");
  const runBtnText = document.getElementById("runBtnText");

  const statusBadge = document.getElementById("statusBadge");
  const statusIndicator = document.getElementById("statusIndicator");
  const statusLabel = document.getElementById("statusLabel");

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

      const response = await fetch("/api/watermark", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();
      const elapsedMs = Math.round(performance.now() - startTime);

      if (!response.ok || !data.success) {
        throw new Error(data.error || "Watermarking operation failed.");
      }

      // Render successful results
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
    setSystemStatus("ready");
  }

  return {
    init,
    setSystemStatus,
    execute,
  };
})();
