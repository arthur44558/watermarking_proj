# JND-Guided Frequency-Domain Image Watermarking Studio

An imperceptible, robust, and blind image-in-image watermarking system based on 2D Discrete Cosine Transform (DCT) and activity-based Just Noticeable Difference (JND) perceptual masking. Supports arbitrary cover images and arbitrary watermark images (PNG, JPG, WebP; Grayscale or RGB; up to 1920×1200, 1 MiB envelope) with an interactive Bento-grid web interface.

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

Alternatively, to run the server directly from PowerShell:
```powershell
.venv\Scripts\python.exe src\web\app.py
```

To run the automated test suite:
```powershell
.venv\Scripts\python.exe tests\test_arbitrary_image_watermarking.py
.venv\Scripts\python.exe tests\test_web_api.py
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
│   │   ├── config.py           # Config: 16-pair DCT (16 bits/block), 24B header, JND alpha/beta/scale
│   │   ├── image_utils.py      # BGR ↔ YCrCb, channel splitting, padding & unpadding
│   │   ├── dct.py              # 2D DCT / IDCT
│   │   ├── jnd.py              # Activity-based JND approximation (alpha + beta*sigma)
│   │   ├── payload.py          # Lossless serialization, zlib compression, 24B framing header, CRC32
│   │   ├── watermark.py        # Watermark preprocessing & legacy wrappers
│   │   ├── embedding.py        # Multi-bit JND DCT embedding with spatial quantization refinement
│   │   ├── extraction.py       # Blind header extraction, CRC32 verification & deserialization
│   │   ├── metrics.py          # Cover PSNR/SSIM, Watermark RMSE/MAE/PSNR, Bit Accuracy, NC
│   │   └── pipeline.py         # High-level pipeline: capacity check, embed_and_verify & extract_only
│   ├── web/                    # Local HTTP service
│   │   ├── __init__.py
│   │   ├── app.py              # Server entry point & static file routing
│   │   └── routes.py           # POST /api/watermark, POST /api/capacity, GET /api/config handlers
│   └── experiments/            # Educational step-by-step verification scripts
├── frontend/                   # Modern Bento grid web interface
│   ├── index.html              # Bento UI layout with live metadata cards and responsive canvas
│   ├── css/
│   │   └── styles.css          # Responsive container rules & preview containment
│   └── js/
│       ├── app.js              # Application lifecycle, config pills & event coordination
│       ├── upload.js           # Live capacity checks, client-side metadata & drag/drop
│       ├── processing.js       # Real multipart/form-data fetch to /api/watermark
│       └── results.js          # Renders arbitrary canvases, honest metrics & diff views
├── tests/
│   ├── test_arbitrary_image_watermarking.py  # 10 comprehensive algorithmic roundtrip tests
│   └── test_web_api.py                       # Integration tests for Flask API routes
├── requirements.txt            # Python dependencies (numpy, opencv, scikit-image, scipy, flask)
├── start.bat                   # 1-click batch launcher
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
  * `cover_image`: Cover image file (Required)
  * `watermark_image`: Watermark image file (Optional; omit for Extract-Only mode)
* **Response** (`200 OK` - Mode A: Embed & Verify):
  ```json
  {
    "success": true,
    "mode": "embed_and_verify",
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
    },
    "metadata": {
      "cover_width": 1080,
      "cover_height": 1080,
      "watermark_width": 32,
      "watermark_height": 32,
      "watermark_format": "PNG",
      "watermark_color_mode": "RGB",
      "raw_payload_bytes": 3072,
      "compressed_payload_bytes": 184,
      "total_payload_bytes": 208,
      "carrier_capacity_bytes": 109326,
      "channels_used": 1,
      "channels_used_label": "Y (Luminance)",
      "utilization_percent": 0.19,
      "compression_ratio": "16.70x",
      "processed_blocks": 104,
      "total_carrier_blocks": 18225
    }
  }
  ```
* **Response** (`200 OK` - Mode B: Extract-Only):
  Returns extracted watermark with metrics set to `null` (displayed as `—` on UI, no fabricated metrics).
* **Response** (`400 Bad Request` - Capacity Deficit):
  Returns detailed error with payload size, carrier capacity, and exact deficit bytes before any cover modification occurs.

### `GET /api/config`
* Returns current algorithm hyperparameters and capacity limits.
