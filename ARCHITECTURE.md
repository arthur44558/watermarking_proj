# Master Architecture & Technical Specification

> [!CAUTION]
> ### DIRECTIVE FOR ALL AI AGENTS & DEVELOPERS
> **ANY AI AGENT OR DEVELOPER WORKING ON THIS REPOSITORY MUST UPDATE THIS DOCUMENT (`ARCHITECTURE.md`) AND `README.md` IMMEDIATELY AFTER MAKING ANY CHANGES TO THE PROJECT.**
> 
> Keep this document accurate, comprehensive, and up-to-date so that future contributors and autonomous agents do not have to read the entire codebase to understand the system.

---

## 1. Executive Summary

This repository implements a **Perceptual Frequency-Domain Watermarking System** powered by 2D Discrete Cosine Transform (DCT) modulation and activity-based Just Noticeable Difference (JND) visual masking.

The system supports **dual media carriers**:
1. **Arbitrary Image Watermarking**: Full image-in-image watermarking supporting arbitrary cover dimensions and watermark images (PNG, JPG, WebP, BMP, Grayscale or RGB) up to 1920×1200 with 100% blind reconstruction and 0 bit errors.
2. **Fastest Memory-Safe Video Watermarking (Stage 1 Baseline)**: High-performance frame-by-frame video watermarking that embeds an optimized watermark into every video frame with guaranteed bounded memory usage (never accumulating frames in RAM), multi-frame sampling extraction, and CRC32 verification.

The application includes a local **Flask Web API backend** and an interactive **Tailwind CSS Bento-Grid frontend** launched with a 1-click `start.bat` script.

---

## 2. Directory Structure & File Map

```text
Macro_proj/
├── .venv/                              # Python 3.14 virtual environment
├── input/                              # Standard reference inputs (test images, sample watermarks)
├── uploads/                            # Staging directory for uploaded media
├── output/                             # Served output files (watermarked images, videos, extracted marks)
├── src/
│   ├── watermarking/                   # Algorithmic core engine
│   │   ├── __init__.py                 # Public package exports
│   │   ├── config.py                   # Global constants: 16-pair DCT, JND parameters, codecs, queue limits
│   │   ├── dct.py                      # 2D DCT-II and IDCT block transformations
│   │   ├── jnd.py                      # Activity-based JND approximation: JND = (alpha + beta * sigma) * scale
│   │   ├── payload.py                  # Framing header (32B), CRC32, serialization, zlib/WebP/JPEG codecs
│   │   ├── optimizer.py                # Watermark quality search, auto-compression, and downscaling
│   │   ├── embedding.py                # 16-pair DCT differential embedding with spatial rounding compensation
│   │   ├── extraction.py               # Blind extraction from Y/Cr/Cb channels & watermark reconstruction
│   │   ├── video.py                    # Video pipeline: inspection, bounded queues, sequential/threaded workers, sampling extraction
│   │   ├── image_utils.py              # Color space conversions (BGR <-> YCrCb), padding, block slicing
│   │   ├── metrics.py                  # PSNR, SSIM, Normalized Correlation (NC), Bit Accuracy, RMSE, MAE
│   │   └── pipeline.py                 # High-level pipeline wrappers: watermark_image, extract_only, capacity
│   └── web/                            # Flask web server
│       ├── __init__.py
│       ├── app.py                      # App factory, static file serving, output serving, 404 handler
│       └── routes.py                   # API endpoints: POST /api/watermark, POST /api/capacity, GET /api/config
├── frontend/                           # Bento-grid web application
│   ├── index.html                      # Bento workspace with dual media previews, controls, metrics
│   ├── css/
│   │   └── styles.css                  # Container styling, preview containment, animations
│   └── js/
│       ├── app.js                      # Application lifecycle coordinator & server configuration chips
│       ├── upload.js                   # Media handling (Image & Video), client preview, capacity calculation
│       ├── processing.js               # API execution handler, spinner states, timing
│       ├── results.js                  # Results rendering: video player / image canvas, metrics, downloads
│       └── lightbox.js                 # Click-to-zoom modal supporting both high-res images and playable video
├── tests/                              # Automated test suite
│   ├── test_arbitrary_image_watermarking.py  # Algorithmic image roundtrip tests
│   ├── test_embedding_robustness.py           # Randomized multi-trial bit recovery and CRC32 tests
│   ├── test_watermark_optimizer.py            # Watermark optimization & downscaling tests
│   ├── test_web_api.py                        # Web API route integration tests
│   └── test_video_watermarking.py             # Video processing, bounded queues, multi-frame extraction tests
├── JND_video_stage1_fastest_implementation.md # Technical specification for Stage 1 video baseline
├── requirements.txt                    # Python package dependencies
├── start.bat                           # 1-Click Windows launcher script
├── ARCHITECTURE.md                     # Master architectural specification (THIS FILE)
└── README.md                           # Public repository overview
```

---

## 3. Mathematical & Algorithmic Foundations

### 3.1 2D Discrete Cosine Transform (DCT)
Spatial luminance blocks of size $8 \times 8$, $B(x, y)$, are transformed into frequency coefficients $C(u, v)$ using 2D-DCT-II:
$$C(u, v) = \alpha(u) \alpha(v) \sum_{x=0}^{7} \sum_{y=0}^{7} B(x, y) \cos\left[\frac{(2x+1)u\pi}{16}\right] \cos\left[\frac{(2y+1)v\pi}{16}\right]$$
where $\alpha(0) = \frac{1}{\sqrt{8}}$ and $\alpha(u) = \sqrt{\frac{2}{8}}$ for $u > 0$.

### 3.2 Activity-Based Perceptual JND Masking
Visual masking exploits the Human Visual System (HVS) property that high spatial texture and variance mask luminance distortions. The local JND threshold $T_B$ for block $B$ is computed from its standard deviation $\sigma_B$:
$$\sigma_B = \sqrt{\frac{1}{64}\sum_{i=1}^{64} (x_i - \mu_B)^2}$$
$$T_B = \max\left((\alpha + \beta \sigma_B) \times k, \; 3.5\right)$$
- **Default Parameters**: $\alpha = 2.0$, $\beta = 0.1$, $k = 1.5$ (`JND_SCALE`).

### 3.3 16-Pair Differential Frequency Modulation
Each $8 \times 8$ block embeds **16 bits (2 bytes)** using 16 symmetric mid-to-high frequency coefficient pairs $(C_a, C_b)$:
- **Pair coordinates**: strictly off-diagonal, non-DC symmetric pairs: $((3,2), (2,3))$, $((1,4), (4,1))$, etc.
- **Modulation Rule**:
  - If bit = 1: enforce $C_a - C_b \ge T_B$. If $C_a - C_b < T_B$, adjust by $d = T_B - (C_a - C_b)$:
    $$C_a' = C_a + \frac{d}{2}, \quad C_b' = C_b - \frac{d}{2}$$
  - If bit = 0: enforce $C_b - C_a \ge T_B$. If $C_b - C_a < T_B$, adjust by $d = T_B - (C_b - C_a)$:
    $$C_b' = C_b + \frac{d}{2}, \quad C_a' = C_a - \frac{d}{2}$$

### 3.4 Spatial Quantization & Color Roundtrip Compensation
After IDCT, pixel values are rounded to integers and clipped to $[0, 255]$. To prevent rounding errors from flipping bits, a refinement loop tests forward DCT on the quantized uint8 block (including BGR-YCrCb roundtrip checks); if any bit flip occurs, $T_B$ is increased by $2.0$ and re-embedded, guaranteeing **100.0% zero-error extraction**.

---

## 4. Payload Framing & Optimization

### 4.1 32-Byte Framing Header
Every payload is prefixed with a 32-byte binary header (`struct` format `>4s B B B B B B H H H H I I I H`):
```text
[0:4]   Magic: 'JNDW' (4 bytes)
[4:5]   Version: 2 (1 byte)
[5:6]   Channels Used: 1 (Y) or 3 (Y, Cr, Cb) (1 byte)
[6:7]   Color Mode: 0 (Grayscale), 1 (RGB/BGR) (1 byte)
[7:8]   Codec: 0 (RAW_ZLIB), 1 (WebP), 2 (JPEG) (1 byte)
[8:9]   Quality: 0-100 (1 byte)
[9:10]  Reserved: 0x00 (1 byte)
[10:12] Original Width: uint16
[12:14] Original Height: uint16
[14:16] Optimized Width: uint16
[16:18] Optimized Height: uint16
[18:22] Uncompressed Raw Bytes: uint32
[22:26] Compressed Payload Bytes: uint32
[26:30] CRC32 Checksum over Compressed Data: uint32
[30:32] Reserved: 0x0000 (2 bytes)
```

### 4.2 Watermark Optimizer (`optimizer.py`)
Automatically adapts any watermark to fit carrier capacity:
1. **Stage 0**: Lossless test with `RAW_ZLIB` at level 9.
2. **Stage 1**: Near-monochrome detection (converts RGB to 1-channel Grayscale if $|R-G| \le 5$ and $|G-B| \le 5$).
3. **Stage 2**: Binary search over lossy WebP quality $Q \in [25, 95]$ at original dimensions.
4. **Stage 3**: Progressive aspect-ratio-preserving downscaling (scales 0.9, 0.8... down to min dimension 32px) + quality search.
5. **Stage 4**: Capacity deficit error with exact required/available byte counts if even minimum scale cannot fit.

---

## 5. Video Processing Architecture (`video.py`)

Stage 1 fastest video watermarking implementation adheres to strict memory safety and throughput requirements:

```text
                  Input Video (.mp4 / .avi / .mov)
                                ↓
                    OpenCV VideoCapture (cap)
                                ↓
                    [Frame 0: Capacity Check]
                                ↓
              Watermark Optimizer -> Serialized Payload
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│              Memory-Safe Processing Pipeline                    │
│                                                                 │
│  [Decoder Thread]  ──►  in_queue (maxsize=8)                    │
│                                ↓                                │
│                     [Worker Thread Pool (2-4)]                  │
│                     • 1 frame in -> JND DCT -> 1 frame out      │
│                     • Capacity verified per frame               │
│                                ↓                                │
│  [Writer Thread]   ◄──  out_queue (maxsize=8)                   │
│                     • Bounded reorder buffer                    │
│                     • Strictly preserves frame sequence         │
│                     • VideoWriter with supported codec fallback │
└─────────────────────────────────────────────────────────────────┘
                                ↓
               Multi-Frame Sampling Extraction & CRC32
               (Frame 0, 30, 60... verify header & CRC)
                                ↓
             Output Playable Watermarked Video & Metrics
```

### 5.1 Memory Safety Rules
- **No All-Frames Accumulation**: Never store frames in a Python list.
- **One Frame In $\to$ One Frame Out**: Immediate de-referencing (`del frame`, `del watermarked_frame`) enables instant garbage collection.
- **Bounded Queues**: `in_queue` and `out_queue` have `maxsize=8`. The decoder thread automatically pauses when workers are busy, preventing RAM inflation on long videos.
- **RSS Tracking**: Process RAM is monitored via `psutil` / Windows `GetProcessMemoryInfo` API / `tracemalloc`.

### 5.2 Multi-Frame Extraction & CRC32
- Samples frames across the video at intervals (e.g. every 30 frames up to 10 samples).
- Blindly reads the 32-byte header and verifies CRC32 checksum for each sampled frame.
- Verifies payload consistency across all valid frames and reconstructs the watermark from the first verified frame.

### 5.3 Codec Fallback Chain & Web Compatibility
Tests output codecs in order of pixel fidelity and browser compatibility:
1. `FFV1` (`.avi`) - FFmpeg intra-frame lossless video codec (built into OpenCV, guarantees 100% bit fidelity and 0 pixel difference)
2. `HFYU` (`.avi`) - Huffman YUV lossless codec
3. `RGBA` (`.avi`) - Raw lossless RGB codec
4. `mp4v` (`.mp4`) - Standard MPEG-4 Part 2
5. `avc1` / `H264` (`.mp4`) - H.264/AVC
6. `XVID` (`.avi`) - XviD MPEG-4
7. `MJPG` (`.avi`) - Motion JPEG

**Browser-Playable Transcoding**:
When an `.avi` container is generated by OpenCV, the video engine automatically checks for local `ffmpeg`. If available, it invokes `ffmpeg -y -i <avi> -c:v libx264 -crf 0 -preset ultrafast <mp4>` to produce a browser-playable lossless H.264 MP4 stream. This guarantees immediate playback in HTML5 `<video>` across Chromium, Safari, and Firefox while maintaining verified multi-frame CRC32 extraction.

---

## 6. Web API Specification (`web/routes.py`)

Base URL: `http://localhost:5000/api`

### 6.1 `POST /api/watermark`
Dual-mode endpoint for images and videos:
- **Form Data**:
  - `cover_image` (File, Required): Image (`.png`, `.jpg`, `.webp`) OR Video (`.mp4`, `.avi`, `.mov`, `.webm`, `.mkv`).
  - `watermark_image` (File, Optional): Watermark image file. If omitted, triggers **Extract-Only Mode**.
  - `mode` (Text, Optional): For video, `"threaded"` (default) or `"sequential"`.
- **Response (Video Embed Mode)**:
  ```json
  {
    "success": true,
    "mode": "embed_and_verify",
    "media_type": "video",
    "watermarked_video": "/output/watermarked_video_a1b2c3d4.mp4",
    "watermarked_video_path": "C:\\path\\to\\output\\watermarked_video_a1b2c3d4.mp4",
    "extracted_watermark": "/output/extracted_video_wm_e5f6g7h8.png",
    "extracted_watermark_path": "C:\\path\\to\\output\\extracted_video_wm_e5f6g7h8.png",
    "video_info": {
      "width": 1280,
      "height": 720,
      "fps": 30.0,
      "frame_count": 300,
      "duration_sec": 10.0,
      "processed_frames": 300,
      "codec": "avc1",
      "container": "mp4"
    },
    "performance": {
      "processing_time_sec": 8.52,
      "average_fps": 35.21,
      "start_ram_mb": 115.4,
      "peak_ram_mb": 142.0,
      "ram_increase_mb": 26.6,
      "processing_mode": "threaded (4 workers)"
    },
    "extraction": {
      "status": "Success",
      "crc_status": "Passed (CRC32 Verified)",
      "valid_sampled_frames": 10,
      "total_sampled_frames": 10,
      "payload_consistent": true,
      "first_valid_frame": 0
    },
    "metrics": {
      "psnr": 43.12,
      "ssim": 0.9854,
      "bit_accuracy": 100.0,
      "normalized_correlation": 1.0,
      "watermark_rmse": 0.0,
      "watermark_mae": 0.0,
      "watermark_psnr": 99.99
    }
  }
  ```

### 6.2 `POST /api/capacity`
- **Form Data**: `cover_image` (Image or Video file).
- **Response**: Exact capacity in bytes, total carrier blocks, and video stream properties if video.

### 6.3 `GET /api/config`
- **Response**: Algorithmic constants (`BLOCK_SIZE`, `JND_ALPHA`, `JND_BETA`, `BITS_PER_BLOCK`, supported formats, video settings).

---

## 7. Frontend Bento-Grid Interface

- **Cover Section**: Supports drag-and-drop or browsing for both images and videos. Renders image canvas or HTML5 video preview with live duration, resolution, block count, and capacity display.
- **Watermark Section**: Previews arbitrary watermark, calculates file size, samples grayscale/color mode, and displays real-time utilization against cover capacity.
- **Results Section**:
  - Image outputs render on `<canvas id="outWatermarkedCanvas">`.
  - Video outputs render in `<video id="outWatermarkedVideo">` with playback controls.
  - Video Performance card displays stream resolution, average FPS throughput, peak RAM, and multi-frame CRC32 status.
  - Extracted watermark renders in thumbnail with direct download button.
  - Lightbox modal enables full-resolution zoom for images and video player playback for videos.

---

## 8. Verification & Test Suite

The test suite covers algorithmic robustness, video memory safety, and web integration:

```bash
# Run full automated test suite
.venv\Scripts\python.exe -m pytest -v
```

1. `tests/test_arbitrary_image_watermarking.py`: 10 comprehensive tests for arbitrary dimensions, grayscale, RGB, capacity checks, and extract-only mode.
2. `tests/test_embedding_robustness.py`: Randomized trials verifying 100.0% bit accuracy and 0 CRC32 errors.
3. `tests/test_watermark_optimizer.py`: Tests quality search, WebP compression, downscaling, and capacity rejection.
4. `tests/test_web_api.py`: Tests `/api/config`, `/api/capacity`, and `/api/watermark`.
5. `tests/test_video_watermarking.py`: Tests synthetic video generation, sequential and threaded processing, frame preservation, multi-frame extraction, memory stability, and video API routes.
