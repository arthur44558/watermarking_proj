/**
 * lightbox.js - Reusable Click-to-Zoom Media (Image & Video) Viewer Modal.
 */

const Lightbox = (function () {
  const modal = document.getElementById("imageLightbox");
  const lightboxImg = document.getElementById("lightboxImg");
  const lightboxVideo = document.getElementById("lightboxVideo");
  const lightboxTitle = document.getElementById("lightboxTitle");
  const closeBtn = document.getElementById("lightboxCloseBtn");
  const backdrop = document.getElementById("lightboxBackdrop");

  function open(src, title = "Media Preview", isVideo = false) {
    if (!modal) return;

    if (lightboxTitle) lightboxTitle.textContent = title;

    if (isVideo && lightboxVideo) {
      if (lightboxImg) {
        lightboxImg.style.display = "none";
        lightboxImg.src = "";
      }
      lightboxVideo.classList.remove("hidden");
      lightboxVideo.style.display = "block";
      lightboxVideo.src = src;
      lightboxVideo.play().catch(() => {});
    } else if (lightboxImg) {
      if (lightboxVideo) {
        lightboxVideo.pause();
        lightboxVideo.src = "";
        lightboxVideo.classList.add("hidden");
        lightboxVideo.style.display = "none";
      }
      lightboxImg.style.display = "block";
      lightboxImg.src = src;
    }

    modal.classList.remove("hidden");
    modal.classList.add("flex");
    document.body.classList.add("overflow-hidden");

    window.addEventListener("keydown", handleKeyDown);
  }

  function close() {
    if (!modal) return;

    modal.classList.add("hidden");
    modal.classList.remove("flex");

    if (lightboxImg) {
      lightboxImg.src = "";
      lightboxImg.style.display = "block";
    }
    if (lightboxVideo) {
      lightboxVideo.pause();
      lightboxVideo.src = "";
      lightboxVideo.classList.add("hidden");
      lightboxVideo.style.display = "none";
    }

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
