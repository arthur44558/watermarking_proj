# JND-Guided Frequency-Domain Image & Video Watermarking Studio

> [!CAUTION]
> ### DIRECTIVE FOR ALL AI AGENTS & DEVELOPERS
> **ANY AI AGENT OR DEVELOPER WORKING ON THIS REPOSITORY MUST UPDATE [`ARCHITECTURE.md`](ARCHITECTURE.md) AND [`README.md`](README.md) IMMEDIATELY AFTER MAKING ANY CHANGES TO THE PROJECT.**
> 
> Detailed architecture, mathematical formulations, data flows, and component specs are documented in [**`ARCHITECTURE.md`**](ARCHITECTURE.md).

An imperceptible, robust, and blind media watermarking system based on 2D Discrete Cosine Transform (DCT) and activity-based Just Noticeable Difference (JND) perceptual masking. Supports:
- **Arbitrary Image Watermarking**: Arbitrary cover dimensions and watermark images (PNG, JPG, WebP; Grayscale or RGB; up to 1920×1200, 1 MiB envelope) with 100% blind reconstruction.
- **Fastest Memory-Safe Video Watermarking**: Frame-by-frame processing of MP4/AVI/MOV/WEBM video streams without uncontrolled memory usage, bounded multithreaded worker pools, and multi-frame sampling extraction with CRC32 verification.

---

## 1. Quick Start (1-Click Launcher)

To launch the full web application on Windows:
```cmd
start.bat
```
This batch script automatically:
1. Verifies/initializes the virtual environment with **Python 3.14**.
2. Activates `.venv` and verifies required dependencies from `requirements.txt`.
3. Creates necessary `uploads/` and `output/` runtime directories.
4. Launches the Flask backend server on `http://localhost:5000`.
5. Automatically opens your default web browser to the application interface.

Alternatively, to run the server directly:
```powershell
.venv\Scripts\python.exe src\web\app.py
```

To run the automated test suite:
```powershell
.venv\Scripts\pytest -v
```

---

## 2. System Architecture

```text
Macro_proj/
├── .venv/                      # Python 3.14 virtual environment
├── input/                      # Standard sample inputs
│   ├── test_image.jpeg         # Sample cover image (1080x1080)
│   └── watermark.png           # Sample watermark image (32x32)
├── uploads/                    # Temporary staging for user uploads
├── output/                     # Saved watermarked & extracted images
├── src/
│   ├── watermarking/           # Core algorithmic modules
│   │   ├── __init__.py
│   │   ├── config.py           # Config: 16-pair DCT (16 bits/block), 32B header, JND alpha/beta/scale, video params
│   │   ├── image_utils.py      # BGR ↔ YCrCb, channel splitting, padding & unpadding
│   │   ├── dct.py              # 2D DCT / IDCT
│   │   ├── jnd.py              # Activity-based JND approximation (alpha + beta*sigma)
│   │   ├── payload.py          # Lossless serialization, zlib compression, 32B framing header, CRC32
│   │   ├── optimizer.py        # Watermark quality search, WebP compression, downscaling
│   │   ├── embedding.py        # Multi-bit JND DCT embedding with spatial quantization refinement
│   │   ├── extraction.py       # Blind header extraction, CRC32 verification & deserialization
│   │   ├── video.py            # Bounded frame-by-frame video processing, threaded worker pool, sampling extraction
│   │   ├── metrics.py          # Cover PSNR/SSIM, Watermark RMSE/MAE/PSNR, Bit Accuracy, NC
│   │   └── pipeline.py         # High-level pipeline: capacity check, embed_and_verify & extract_only
│   ├── web/                    # Local HTTP service
│   │   ├── __init__.py
│   │   ├── app.py              # Server entry point & static file routing
│   │   └── routes.py           # POST /api/watermark, POST /api/capacity, GET /api/config handlers
│   └── experiments/            # Educational step-by-step verification scripts
├── frontend/                   # Modern Bento grid web interface
│   ├── index.html              # Bento UI layout with live metadata cards and responsive canvas/video players
│   ├── css/
│   │   └── styles.css          # Responsive container rules & preview containment
│   └── js/
│       ├── app.js              # Application lifecycle, config pills & event coordination
│       ├── upload.js           # Media handling (Image & Video), client preview, capacity calculation
│       ├── processing.js       # Real multipart/form-data fetch to /api/watermark
│       ├── results.js          # Renders arbitrary canvases, video player, honest metrics & diff views
│       └── lightbox.js         # Click-to-zoom modal for high-res images and video playback
├── tests/
│   ├── test_arbitrary_image_watermarking.py  # 10 comprehensive algorithmic roundtrip tests
│   ├── test_embedding_robustness.py           # Randomized multi-trial bit recovery and CRC32 tests
│   ├── test_watermark_optimizer.py            # Watermark optimization & downscaling tests
│   ├── test_web_api.py                        # Integration tests for Flask API routes
│   └── test_video_watermarking.py             # Video processing, bounded queues, multi-frame extraction tests
├── JND_video_stage1_fastest_implementation.md # Technical specification for Stage 1 video baseline
├── requirements.txt            # Python dependencies (numpy, opencv, scikit-image, scipy, flask)
├── start.bat                   # 1-click batch launcher
├── ARCHITECTURE.md             # Master technical architecture & component specification
└── README.md
```

---

## 3. Mathematical & Algorithmic Formulations

### 3.1 2D Discrete Cosine Transform (DCT)
For an $8 \times 8$ spatial block $B(x, y)$:
$$C(u, v) = \alpha(u) \alpha(v) \sum_{x=0}^{7} \sum_{y=0}^{7} B(x, y) \cos\left[\frac{(2x+1)u\pi}{16}\right] \cos\left[\frac{(2y+1)v\pi}{16}\right]$$

### 3.2 Activity-Based Perceptual JND Modulation
For block standard deviation $\sigma_B = \sqrt{\frac{1}{64} \sum_{i=1}^{64} (x_i - \mu)^2}$:
$$T_B = (\alpha + \beta \sigma_B) \times k$$
- Default parameters: $\alpha = 2.0$, $\beta = 0.1$, $k = 1.5$ (`JND_SCALE`).

### 3.3 Multi-Bit Differential Coefficient Embedding
Each $8 \times 8$ block embeds **16 bits** across 16 symmetric mid-to-high frequency coefficient pairs $(C_{a,i}, C_{b,i})$:
- For bit 1: Enforce $C_a - C_b \ge T_B$. If $C_a - C_b < T_B$, let $d = T_B - (C_a - C_b)$, then:
  $$C_a' = C_a + \frac{d}{2}, \quad C_b' = C_b - \frac{d}{2}$$
- For bit 0: Enforce $C_b - C_a \ge T_B$. If $C_b - C_a < T_B$, let $d = T_B - (C_b - C_a)$, then:
  $$C_b' = C_b + \frac{d}{2}, \quad C_a' = C_a - \frac{d}{2}$$

### 3.4 Spatial Quantization Refinement Loop
After inverse DCT, pixel values are rounded to integers and clipped to $[0, 255]$. To prevent edge-pixel rounding errors across 16 simultaneous coefficient modifications, a local refinement loop tests forward DCT on the quantized uint8 block; if any bit would flip due to clipping, the margin is adaptively boosted (up to 4 passes), guaranteeing **100.0% error-free bit recovery**.

### 3.5 Framing Protocol & Blind Extraction
The payload begins with a 24-byte header packed into the first 12 blocks of the Y channel:
- `MAGIC`: 4 bytes (`b"JNDW"`)
- `VERSION`: 1 byte (`0x01`)
- `CHANNELS_USED`: 1 byte (`0x01` for Y only, `0x03` for YCrCb)
- `COLOR_MODE`: 1 byte (`0x01` for Grayscale, `0x03` for RGB)
- `BIT_DEPTH`: 1 byte (`8`)
- `WIDTH`: 2 bytes uint16
- `HEIGHT`: 2 bytes uint16
- `ORIGINAL_BYTES`: 4 bytes uint32
- `COMPRESSED_BYTES`: 4 bytes uint32
- `CRC32`: 4 bytes uint32

The decoder blindly reads the 24-byte header, determines total compressed bytes and channel distribution, extracts the remaining bitstream in raster order, verifies the CRC32 checksum, decompresses via zlib, and reconstructs the watermark at original resolution and color mode.

---

## 4. API Specification

### `POST /api/capacity`
* **Content-Type**: `multipart/form-data`
* **Body**: `cover_image` (file)
* **Response** (`200 OK`):
  ```json
  {
    "success": true,
    "capacity": {
      "cover_width": 1080,
      "cover_height": 1080,
      "is_color": true,
      "total_carrier_blocks": 18225,
      "usable_y_capacity_bytes": 36426,
      "usable_multichannel_capacity_bytes": 109326,
      "max_usable_capacity_bytes": 109326,
      "bits_per_block": 16,
      "bytes_per_block": 2
    }
  }
  ```

### `POST /api/watermark`
* **Content-Type**: `multipart/form-data`
* **Body**:
  * `cover_image`: Cover media file (Image `.png`/`.jpg`/`.webp`/`.bmp` OR Video `.mp4`/`.avi`/`.mov`/`.webm`)
  * `watermark_image`: Watermark image file (Optional; omit for Extract-Only mode)
  * `mode`: Optional processing mode for videos: `"sequential"` or `"threaded"` (default: `"threaded"`)
* **Response** (`200 OK` - Mode A: Embed & Verify - Image):
  ```json
  {
    "success": true,
    "mode": "embed_and_verify",
    "media_type": "image",
    "watermarked_image": "/output/watermarked_3109ed23.png",
    "extracted_watermark": "/output/extracted_3109ed23.png",
    "difference_image": "/output/difference_3109ed23.png",
    "metrics": {
      "psnr": 54.12,
      "ssim": 0.9996,
      "bit_accuracy": 100.0,
      "normalized_correlation": 1.0,
      "watermark_rmse": 0.0,
      "watermark_mae": 0.0,
      "watermark_psnr": 99.99
    }
  }
  ```
* **Response** (`200 OK` - Mode A: Embed & Verify - Video):
  ```json
  {
    "success": true,
    "mode": "embed_and_verify",
    "media_type": "video",
    "watermarked_video": "/output/watermarked_video_3109ed23.mp4",
    "extracted_watermark": "/output/extracted_video_wm_3109ed23.png",
    "video_info": {
      "width": 1920,
      "height": 1080,
      "fps": 30.0,
      "frame_count": 300,
      "duration_sec": 10.0,
      "processed_frames": 300,
      "codec": "H.264 Lossless (CRF 0 MP4)",
      "container": "mp4"
    },
    "performance": {
      "processing_time_sec": 4.82,
      "average_fps": 62.24,
      "peak_ram_mb": 118.5,
      "processing_mode": "threaded (4 workers)"
    },
    "extraction": {
      "status": "Success",
      "crc_status": "Passed (CRC32 Verified)",
      "valid_sampled_frames": 10,
      "total_sampled_frames": 10,
      "payload_consistent": true
    },
    "metrics": {
      "psnr": 48.72,
      "ssim": 0.9984,
      "bit_accuracy": 100.0,
      "normalized_correlation": 1.0
    }
  }
  ```
* **Response** (`200 OK` - Mode B: Extract-Only):
  Returns extracted watermark with metrics set to `null` (displayed as `—` on UI, no fabricated metrics).
* **Response** (`400 Bad Request` - Capacity Deficit):
  Returns detailed error with payload size, carrier capacity, and exact deficit bytes before any cover modification occurs.

### `GET /api/config`
* Returns current algorithm hyperparameters, capacity limits, and video streaming configurations.

---

## 5. Automated Test Suite (32/32 Passing)

```powershell
.venv\Scripts\python.exe -m pytest -v
```

1. **`tests/test_arbitrary_image_watermarking.py`** (10 tests): Full roundtrip grayscale/RGB embedding, odd carrier resolutions, capacity limits, extract-only.
2. **`tests/test_embedding_robustness.py`** (5 tests): Multi-trial randomized color covers, guaranteeing 100% bit accuracy and 0 CRC32 errors.
3. **`tests/test_watermark_optimizer.py`** (5 tests): Dynamic downscaling, WebP/raw compression, quality search.
4. **`tests/test_web_api.py`** (4 tests): Flask HTTP routes (`/api/capacity`, `/api/watermark`, `/api/config`).
5. **`tests/test_video_watermarking.py`** (8 tests): Sequential/threaded frame streaming, memory stability (RSS bounded), multi-frame CRC32 verification, benchmark utilities, and web video API endpoints.

