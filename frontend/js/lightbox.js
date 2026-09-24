/**
 * lightbox.js - Reusable Click-to-Zoom Image Viewer Modal.
 */

const Lightbox = (function () {
  const modal = document.getElementById("imageLightbox");
  const lightboxImg = document.getElementById("lightboxImg");
  const lightboxTitle = document.getElementById("lightboxTitle");
  const closeBtn = document.getElementById("lightboxCloseBtn");
  const backdrop = document.getElementById("lightboxBackdrop");

  function open(src, title = "Image Preview") {
    if (!modal || !lightboxImg) return;

    lightboxImg.src = src;
    if (lightboxTitle) lightboxTitle.textContent = title;

    modal.classList.remove("hidden");
    modal.classList.add("flex");
    document.body.classList.add("overflow-hidden");

    window.addEventListener("keydown", handleKeyDown);
  }

  function close() {
    if (!modal || !lightboxImg) return;

    modal.classList.add("hidden");
    modal.classList.remove("flex");
    lightboxImg.src = "";
    document.body.classList.remove("overflow-hidden");

    window.removeEventListener("keydown", handleKeyDown);
  }

  function handleKeyDown(e) {
    if (e.key === "Escape") {
      close();
    }
  }

  function init() {
    if (closeBtn) {
      closeBtn.addEventListener("click", close);
    }
    if (backdrop) {
      backdrop.addEventListener("click", close);
    }
    if (modal) {
      modal.addEventListener("click", (e) => {
        if (e.target === modal) {
          close();
        }
      });
    }
  }

  return {
    init,
    open,
    close,
  };
})();
