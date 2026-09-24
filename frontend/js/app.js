/**
 * app.js - Main application coordinator.
 */

document.addEventListener("DOMContentLoaded", () => {
  // Initialize modules
  if (window.Lightbox) Lightbox.init();
  Upload.init();
  Processing.init();
  Results.init();

  // Clear inputs handler
  const resetBtn = document.getElementById("resetInputsBtn");
  if (resetBtn) {
    resetBtn.addEventListener("click", () => {
      Upload.clearInputs();
      Results.resetResults();
      Processing.setSystemStatus("ready");
    });
  }

  // Fetch server configuration to populate method chips dynamically
  fetch("/api/config")
    .then((res) => res.json())
    .then((data) => {
      if (data.success && data.configuration) {
        const cfg = data.configuration;
        const configChips = document.getElementById("configChips");
        if (configChips) {
          configChips.innerHTML = `
            <span><strong class="text-secondary font-medium">Space:</strong> ${cfg.color_space}</span>
            <span class="text-slate-300">•</span>
            <span><strong class="text-secondary font-medium">Modulation:</strong> 16-Pair Multi-Bit DCT (${cfg.bits_per_block} bits/blk)</span>
            <span class="text-slate-300">•</span>
            <span><strong class="text-secondary font-medium">Partition:</strong> ${cfg.block_size}×${cfg.block_size} Blocks</span>
            <span class="text-slate-300">•</span>
            <span><strong class="text-secondary font-medium">Transform:</strong> ${cfg.transform}</span>
            <span class="text-slate-300">•</span>
            <span><strong class="text-secondary font-medium">JND:</strong> α=${cfg.jnd_alpha}, β=${cfg.jnd_beta}</span>
            <span class="text-slate-300">•</span>
            <span><strong class="text-secondary font-medium">Optimization:</strong> Auto-Compress / Scale</span>
          `;
        }
      }
    })
    .catch((err) => {
      console.warn("Could not fetch server config, using defaults:", err);
    });
});
