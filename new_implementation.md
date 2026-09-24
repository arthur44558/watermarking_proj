# JND-Guided Frequency-Domain Watermarking
## Full Local Application Integration Specification
### Frontend + Python Backend + Modular Image Watermarking Pipeline

---

## 1. Objective

Connect the existing Bento-style frontend to a real local Python watermarking backend.

The current frontend is already visually structured as a local image-watermarking application, with:

- Cover Image upload
- Watermark Image upload
- Run Watermarking action
- Original Image result
- Watermarked Image result
- Extracted Watermark result
- PSNR / SSIM / Bit Accuracy / NC result cards
- Method configuration
- Processing pipeline

The frontend must now become a real client of the image-watermarking implementation rather than simulating watermarking in browser JavaScript.

The existing frontend currently creates a synthetic carrier and watermark, performs a client-side pixel-level approximation, and inserts hard-coded evaluation values. Those behaviors must be removed from the production workflow and replaced by the actual Python DCT/JND watermarking pipeline.

The design and layout should be preserved unless a change is explicitly required for correctness or responsive image handling.

The backend is the source of truth for all mathematical processing and evaluation results.

---

# 2. Current Algorithm That Must Be Connected

The image-stage algorithm defined in the existing project specification is:

```text
Cover Image
    ↓
BGR → YCrCb
    ↓
Extract Y / Luminance
    ↓
Pad to 8×8-compatible dimensions
    ↓
Divide into 8×8 blocks
    ↓
DCT
    ↓
Local standard deviation σ
    ↓
JND = α + βσ
    ↓
Select C(3,2) and C(2,3)
    ↓
Embed watermark bit
    ↓
Inverse DCT
    ↓
Reconstruct Y
    ↓
Combine original Cr/Cb
    ↓
YCrCb → BGR
    ↓
Watermarked Image
    ↓
DCT extraction
    ↓
Recovered Watermark
```

The current project specification explicitly defines this as the smallest complete image-level unit before moving to robust video watermarking. fileciteturn0file1L4-L14

The current target is a complete path from cover image + watermark image to watermarked image + recovered watermark. fileciteturn0file1L14-L38

---

# 3. Integration Rule

The architecture must become:

```text
                         LOCAL APPLICATION

┌──────────────────────────────────────────────────────────┐
│                       FRONTEND                           │
│                                                          │
│  Cover Upload   Watermark Upload   Run Watermarking      │
│         │               │                 │              │
│         └───────────────┴─────────────────┘              │
│                          │                               │
│                       HTTP Request                       │
└──────────────────────────┼───────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│                     LOCAL WEB SERVER                     │
│                                                          │
│                     POST /api/watermark                 │
│                          │                               │
│                          ▼                               │
│                   Watermarking Pipeline                  │
└──────────────────────────┼───────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│                  IMAGE WATERMARKING CORE                  │
│                                                          │
│ image_utils → watermark → DCT → JND → embedding         │
│                                      ↓                   │
│ extraction ← metrics ← reconstruction                   │
└──────────────────────────────────────────────────────────┘
```

The browser should handle interaction and presentation.

Python should handle image processing.

Do not implement DCT, JND, embedding, extraction, or evaluation in frontend JavaScript.

---

# 4. Important Current-Frontend Problems to Remove

The attached frontend currently contains several behaviors that were suitable for visual prototyping but must not remain once the real backend is connected.

## 4.1 Remove the synthetic default carrier as the application input

The current frontend generates a diagnostic 512×512 test pattern in JavaScript.

That generated image is not the user's image.

The production UI must instead start in an empty-input state and allow the user to select the cover image.

The existing development test image may still be used from Python/CLI experiments, but it must not be silently inserted into the web UI.

---

## 4.2 Remove the synthetic default watermark

The current frontend draws its own watermark graphic and converts it to a 32×32 binary grid.

This must be replaced by:

```text
User-selected watermark image
        ↓
Frontend preview only
        ↓
Upload to Python backend
        ↓
Backend converts watermark image into bits
```

The user should never have to upload `.bin` data.

The watermark input is an image.

---

## 4.3 Remove client-side watermark simulation

The current frontend approximates the process by:

- computing luminance values directly in canvas;
- calculating block standard deviation in JavaScript;
- applying pixel modifications to small spatial regions;
- repeating 1024 watermark bits;
- calling the result a DCT/JND embedding simulation.

That is not the actual DCT embedding algorithm.

Delete this production execution path.

The frontend should send files to the backend instead.

---

## 4.4 Remove hard-coded metrics

Do not hard-code values such as:

```text
43.82 dB
0.9941
100.0%
0.9998
BER: 0.00%
```

The current frontend inserts such values after a timer-based simulation.

Those values must be replaced with numbers returned by the real backend.

Before execution, display:

```text
—
```

After execution, display actual calculated values.

---

## 4.5 Remove fake execution timing

The current frontend uses a timeout to simulate processing time.

Remove the artificial delay.

The status should represent actual API state:

```text
Ready
Processing
Completed
Error
```

The execution duration can be measured by the frontend around the real request, or returned by the backend if desired.

Do not display an estimated fixed time such as `~110ms`.

---

# 5. Frontend Design to Preserve

The visual system is already established.

Keep:

- Bento card layout;
- muted blue/indigo palette;
- softly rounded rectangular cards;
- compact spacing;
- Inter + JetBrains Mono visual hierarchy;
- technical metadata;
- compact action bar;
- result comparison section;
- method/configuration card;
- pipeline visualization.

The frontend already uses a 12-column Bento grid and a two-column primary result layout. The existing result area should retain that general structure. fileciteturn0file0L123-L126

The current result redesign already places Original Image and Watermarked Image side by side, with Extracted Watermark in a dedicated compact card below them. fileciteturn0file0L245-L321

Do not revert that layout into three tall equal-width vertical result cards.

---

# 6. Final User Flow

The complete user journey must be:

```text
Open local application
        ↓
Select Cover Image
        ↓
Select Watermark Image
        ↓
Preview both
        ↓
Click "Run Watermarking"
        ↓
Frontend sends both files
        ↓
Python backend performs real algorithm
        ↓
Backend returns generated outputs + metrics
        ↓
Frontend displays:
    Original
    Watermarked
    Extracted Watermark
    Metrics
        ↓
User can select different images
        ↓
Run again
```

No code changes should be required between runs.

---

# 7. Recommended Project Structure

Refactor the existing project into:

```text
Macro_proj/
│
├── .venv/
│
├── input/
│   └── test_image.jpeg
│
├── uploads/
│
├── output/
│
├── src/
│   │
│   ├── watermarking/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── image_utils.py
│   │   ├── dct.py
│   │   ├── jnd.py
│   │   ├── watermark.py
│   │   ├── embedding.py
│   │   ├── extraction.py
│   │   ├── metrics.py
│   │   └── pipeline.py
│   │
│   ├── web/
│   │   ├── __init__.py
│   │   ├── app.py
│   │   └── routes.py
│   │
│   └── experiments/
│       ├── 01_load_image.py
│       ├── 02_luminance.py
│       ├── 03_blocks.py
│       ├── 04_dct.py
│       ├── 05_jnd_test.py
│       ├── 06_embed_bit.py
│       └── 07_extract_bit.py
│
├── frontend/
│   ├── index.html
│   ├── css/
│   │   ├── variables.css
│   │   ├── base.css
│   │   ├── layout.css
│   │   ├── components.css
│   │   └── responsive.css
│   ├── js/
│   │   ├── app.js
│   │   ├── upload.js
│   │   ├── processing.js
│   │   └── results.js
│   └── assets/
│
├── requirements.txt
└── README.md
```

The existing project plan already defines the image-stage modules as single-responsibility components. fileciteturn0file1L42-L76

---

# 8. `config.py`

Centralize fixed algorithm parameters.

Use:

```python
BLOCK_SIZE = 8

COEFF_A = (3, 2)
COEFF_B = (2, 3)

JND_ALPHA = 2.0
JND_BETA = 0.1

JND_SCALE = 1.0

WATERMARK_SIZE = (32, 32)
```

The current project specification uses an activity-based JND approximation:

```text
JND = α + βσ
```

with:

```text
α = 2.0
β = 0.1
```

and uses the selected coefficient pair:

```text
C(3,2)
C(2,3)
```

The existing implementation plan identifies these parameters explicitly. fileciteturn0file1L453-L491 fileciteturn0file1L497-L528

Do not make them editable from the UI yet.

The frontend can display them as read-only configuration.

---

# 9. `image_utils.py`

Responsibilities:

```text
Load image
Validate image
BGR ↔ YCrCb conversion
Separate channels
Pad image to multiple of 8
Crop padding
Reconstruct image
Save image
```

Conceptual functions:

```python
load_image(path)
to_ycrcb(image)
split_channels(ycrcb)
pad_to_block_size(y, block_size=8)
crop_to_original_size(y, original_shape)
merge_channels(y, cr, cb)
to_bgr(ycrcb)
```

For arbitrary cover images, use padding rather than discarding content.

The project specification explicitly calls for padding when image dimensions are not multiples of 8. fileciteturn0file1L229-L275

---

# 10. `dct.py`

Only DCT functionality.

```python
def dct_block(block):
    ...

def idct_block(coefficients):
    ...
```

Use OpenCV's DCT implementation, matching the already-tested project code.

No web or file-upload logic belongs here.

---

# 11. `jnd.py`

Current model:

```python
def calculate_jnd(block, alpha=2.0, beta=0.1):
    std = np.std(block)
    return alpha + beta * std
```

The project describes this as an:

```text
Activity-based JND approximation
```

not a full human visual system model. fileciteturn0file1L453-L493

Keep this module replaceable so a later JND model can be introduced without changing the web layer.

---

# 12. `watermark.py`

Responsibilities:

```text
Watermark image
    ↓
Grayscale
    ↓
Resize/preprocess to configured watermark size
    ↓
Threshold
    ↓
Binary bitstream
```

For the current baseline:

```text
32 × 32
      ↓
1024 bits
```

The existing implementation plan explicitly defines a 32×32 binary watermark as the example first payload. fileciteturn0file1L532-L570

The interface should accept arbitrary watermark image files.

The backend owns the conversion into bits.

---

# 13. `embedding.py`

Implement the actual DCT-domain embedding.

Use:

```python
COEFF_A = (3, 2)
COEFF_B = (2, 3)
```

For bit `1`:

```text
A - B >= T
```

For bit `0`:

```text
B - A >= T
```

with:

```text
T = JND
```

or:

```text
T = JND_SCALE × JND
```

The baseline is:

```text
JND_SCALE = 1.0
```

The project plan defines the coefficient adjustment as equal redistribution between the two selected coefficients. fileciteturn0file1L600-L691

Conceptual interface:

```python
def embed_bit(block, bit):
    ...
```

Then:

```python
def embed_watermark(y_channel, bits):
    ...
```

---

# 14. Critical Correction During Refactoring

The backend must perform actual DCT-domain embedding.

Do not replace it with spatial pixel modification.

The current frontend code directly modifies pixels inside each 8×8 region. That code must not be treated as the real watermark algorithm.

The real pipeline must be:

```text
spatial block
    ↓
DCT
    ↓
modify C(3,2), C(2,3)
    ↓
IDCT
    ↓
spatial block
```

This is the algorithm specified by the current project plan. fileciteturn0file1L327-L359

---

# 15. `extraction.py`

For every watermark-bearing block:

```text
block
 ↓
DCT
 ↓
A = C(3,2)
B = C(2,3)
 ↓
A > B → 1
A <= B → 0
```

Collect the bits and reconstruct the watermark image.

Conceptual interfaces:

```python
def extract_bit(block):
    ...

def extract_watermark(y_channel, watermark_shape):
    ...
```

The current extraction logic is intentionally simple and is defined by the existing project stage. fileciteturn0file1L880-L944

---

# 16. `metrics.py`

Calculate only metrics that are genuinely implemented.

Required target metrics:

```text
PSNR
SSIM
Bit Accuracy
Normalized Correlation (NC)
```

The project specification identifies these as the relevant image-stage evaluation metrics. fileciteturn0file1L948-L1009

Conceptual functions:

```python
calculate_psnr(original, watermarked)
calculate_ssim(original, watermarked)
calculate_bit_accuracy(original_bits, extracted_bits)
calculate_normalized_correlation(original_watermark, extracted_watermark)
```

Do not hard-code any metric.

---

# 17. `pipeline.py`

This is the only high-level watermarking entry point used by the web server.

Conceptual API:

```python
result = watermark_image(
    cover_image,
    watermark_image
)
```

The pipeline should internally perform:

```text
validate cover
validate watermark
        ↓
cover → YCrCb
        ↓
extract Y
        ↓
pad Y
        ↓
watermark → bits
        ↓
divide Y into 8×8 blocks
        ↓
DCT
        ↓
JND
        ↓
embed bit
        ↓
IDCT
        ↓
reconstruct Y
        ↓
crop padding
        ↓
combine Y + Cr + Cb
        ↓
watermarked image
        ↓
extract watermark
        ↓
metrics
        ↓
result
```

The complete image-level pipeline in the project plan follows this ordering. fileciteturn0file1L80-L164

---

# 18. Result Object

Return a structured result from the pipeline.

Recommended conceptual shape:

```python
{
    "watermarked_image": watermarked_image,
    "extracted_watermark": extracted_watermark,
    "metrics": {
        "psnr": ...,
        "ssim": ...,
        "bit_accuracy": ...,
        "normalized_correlation": ...
    },
    "metadata": {
        "cover_width": ...,
        "cover_height": ...,
        "watermark_width": ...,
        "watermark_height": ...,
        "processed_blocks": ...,
        "embedded_bits": ...
    },
    "configuration": {
        "color_space": "YCrCb",
        "embedding_channel": "Y",
        "block_size": 8,
        "transform": "2D-DCT-II",
        "jnd_alpha": 2.0,
        "jnd_beta": 0.1,
        "coefficient_a": [3, 2],
        "coefficient_b": [2, 3]
    }
}
```

The web layer can serialize the numerical metadata while generated images are represented by local URLs/paths.

---

# 19. Web Backend

Use a small local Python web server.

A Flask/FastAPI-style implementation is appropriate.

The web layer needs only the functionality required by this application.

Minimum routes:

```text
GET  /
POST /api/watermark
GET  /output/<filename>
```

The exact framework may be chosen according to the existing application environment.

Do not introduce a database.

Do not introduce authentication.

Do not introduce cloud storage.

---

# 20. `app.py`

Responsibilities:

- initialize the local web application;
- configure frontend/static serving;
- configure output-file serving;
- register routes.

Keep algorithm code out of `app.py`.

---

# 21. `routes.py`

Responsibilities:

```text
receive uploaded files
validate required inputs
store temporary input files
call watermarking pipeline
save generated output files
return JSON result
```

Conceptual route:

```text
POST /api/watermark
```

Request:

```text
multipart/form-data

cover_image=<image file>
watermark_image=<image file>
```

---

# 22. API Success Response

Example:

```json
{
  "success": true,
  "watermarked_image": "/output/watermarked_<id>.png",
  "extracted_watermark": "/output/extracted_<id>.png",
  "metrics": {
    "psnr": 42.17,
    "ssim": 0.9912,
    "bit_accuracy": 100.0,
    "normalized_correlation": 0.9984
  },
  "metadata": {
    "cover_width": 1920,
    "cover_height": 1080,
    "watermark_width": 32,
    "watermark_height": 32,
    "processed_blocks": 32400,
    "embedded_bits": 1024
  },
  "configuration": {
    "color_space": "YCrCb",
    "embedding_channel": "Y",
    "block_size": 8,
    "transform": "2D-DCT-II",
    "jnd_alpha": 2.0,
    "jnd_beta": 0.1,
    "coefficient_a": [3, 2],
    "coefficient_b": [2, 3]
  }
}
```

The values above are only response-shape examples.

Do not use them as hard-coded results.

---

# 23. API Error Response

Use a consistent structure:

```json
{
  "success": false,
  "error": "Readable error message"
}
```

Examples:

```text
Cover image is required.
Watermark image is required.
Invalid cover image.
Invalid watermark image.
Image dimensions could not be processed.
Watermark payload exceeds available blocks.
Watermarking failed.
```

Do not expose Python tracebacks to the browser.

The terminal/log can retain the actual exception for debugging.

---

# 24. Frontend Input Components

The existing HTML already has:

```text
#coverFileInput
#wmFileInput
```

with image file selection behavior. The cover input accepts `image/*`, and the watermark input accepts image formats including PNG, JPEG, BMP, and WEBP. fileciteturn0file0L144-L190

Keep that behavior.

When the user selects an image:

```text
selected file
    ↓
local browser preview
    ↓
filename
    ↓
dimensions
    ↓
ready for API submission
```

No watermark algorithm runs at this point.

---

# 25. Cover Image Preview

The selected cover image should:

- appear immediately in the input card;
- preserve aspect ratio;
- show actual dimensions;
- show actual file size;
- not be resized destructively.

The current frontend uses a canvas preview. That can remain if desired, but an `<img>` preview is simpler.

The preview is display-only.

The original uploaded bytes must be sent to the backend.

Do not send a screenshot of the preview canvas if the original file can be sent directly.

---

# 26. Watermark Preview

Same rule:

```text
selected watermark file
        ↓
browser preview
```

The preview must not become the watermark data source.

The original file should be transmitted to the backend.

---

# 27. Arbitrary Image Dimensions

The frontend must never assume:

```text
512 × 512
```

or:

```text
1080 × 1080
```

The existing project is intended to accept arbitrary images at this stage.

The backend handles block compatibility by padding.

The user only needs to select an image.

---

# 28. Watermark Size Handling

The current algorithm can use the configured watermark size:

```text
32 × 32
```

The user can supply a watermark of any normal image dimensions.

The backend performs the required conversion to the configured binary representation.

The UI should display:

```text
Original watermark: 800 × 400
Processing representation: 32 × 32 binary
```

only if this metadata is actually returned by the backend.

Do not force the user to resize their image manually.

---

# 29. Capacity Handling

The number of available 8×8 blocks determines whether the configured watermark can be embedded.

The current project plan uses one watermark bit per block in the baseline mapping. fileciteturn0file1L572-L596

For a cover image:

```text
padded_width / 8 × padded_height / 8
```

calculate the available number of blocks.

For the baseline 32×32 watermark:

```text
32 × 32 = 1024 bits
```

If insufficient blocks exist:

```text
Do not process.
Return a clear capacity error.
```

Example:

```text
Cover image does not contain enough 8×8 blocks
for the current 32×32 watermark payload.
```

Do not silently repeat watermark bits.

The current frontend uses modulo repetition of the first 1024 bits. That behavior must be removed because the project plan's baseline maps watermark bits sequentially to required blocks rather than cyclically repeating them. fileciteturn0file0L768-L771

---

# 30. Processing Button

Existing button:

```text
Run Watermarking
```

Keep this label.

It should be disabled until:

```text
cover image selected
AND
watermark selected
AND
not currently processing
```

When active:

```text
Embedding...
```

or:

```text
Processing...
```

The status indicator changes to:

```text
Processing
```

After success:

```text
Completed
```

After failure:

```text
Error
```

---

# 31. Frontend Request Code

`processing.js` should perform something conceptually equivalent to:

```javascript
async function runWatermarking(coverFile, watermarkFile) {
    const formData = new FormData();

    formData.append("cover_image", coverFile);
    formData.append("watermark_image", watermarkFile);

    const response = await fetch("/api/watermark", {
        method: "POST",
        body: formData
    });

    const data = await response.json();

    if (!response.ok || !data.success) {
        throw new Error(data.error || "Watermarking failed.");
    }

    return data;
}
```

Do not manually set the `Content-Type` header when using `FormData`.

The browser supplies the multipart boundary.

---

# 32. Frontend Result Update

After a successful response:

```text
result.watermarked_image
      ↓
Watermarked Image card

result.extracted_watermark
      ↓
Extracted Watermark card

result.metrics
      ↓
Metric cards

result.metadata
      ↓
Input/result metadata

result.configuration
      ↓
Method Configuration card
```

The Original Image card continues to show the selected cover image.

---

# 33. Result State Before Processing

Before execution:

```text
Original Image
    → selected cover preview

Watermarked Image
    → Awaiting Processing

Extracted Watermark
    → Awaiting Extraction

PSNR
    → —

SSIM
    → —

Bit Accuracy
    → —

NC
    → —
```

Do not show fake values.

The existing reset function already resets these metric fields to `—`, which should remain the initial state. fileciteturn0file0L636-L655

---

# 34. Result State During Processing

During API execution:

```text
Watermarked Image
    → Processing

Extracted Watermark
    → Processing

Metrics
    → —
```

The frontend may show a compact loading indicator.

Do not block the whole page.

The upload cards can remain visible.

---

# 35. Result State After Processing

After success:

```text
Original Image
    → actual selected image

Watermarked Image
    → actual backend output

Extracted Watermark
    → actual backend output

PSNR
    → backend value

SSIM
    → backend value

Bit Accuracy
    → backend value

NC
    → backend value
```

The overlays should disappear only when the associated output really exists.

---

# 36. Result State on Error

On error:

```text
status = Error
```

Keep the original input previews.

Do not clear the selected files.

Show a compact error message near the processing card.

Keep result metrics at:

```text
—
```

until a successful processing run occurs.

---

# 37. Responsive Result Layout

The current result structure is correct and should remain conceptually:

```text
┌─────────────────────────────┬─────────────────────────────┐
│ Original Image              │ Watermarked Image            │
│                             │                             │
│       aspect-ratio          │       aspect-ratio          │
│       preserving image      │       preserving image      │
│                             │                             │
└─────────────────────────────┴─────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Extracted Watermark                                          │
│ [compact aspect-ratio-preserving preview]                    │
└─────────────────────────────────────────────────────────────┘

┌──────────┬──────────┬──────────────┬────────────────────────┐
│ PSNR     │ SSIM     │ Bit Accuracy │ NC                     │
└──────────┴──────────┴──────────────┴────────────────────────┘
```

Do not force all three result images into identical dimensions.

Landscape, portrait, and square images must retain their aspect ratios.

---

# 38. Aspect-Ratio-Aware Result Preview

Use:

```css
.result-preview {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 160px;
    max-height: 420px;
}

.result-preview img,
.result-preview canvas {
    max-width: 100%;
    max-height: 100%;
    width: auto;
    height: auto;
    object-fit: contain;
}
```

The card should not be given an enormous fixed height.

The preview region should adapt to the available card dimensions.

This is particularly important for arbitrary user photos.

---

# 39. Metrics UI

Current metric cards:

```text
PSNR
SSIM INDEX
BIT ACCURACY
NORM. CORRELATION (NC)
```

may remain.

However, the descriptive lines must not claim thresholds unless such thresholds are explicitly defined as project acceptance criteria.

Avoid implying:

```text
Threshold > 38 dB
Target > 0.98
```

unless those values have actually been established experimentally.

Prefer:

```text
Image distortion metric
Structural similarity
Recovered bit correctness
Watermark similarity
```

or simply omit the secondary line.

The project specification defines the metrics, but does not establish universal pass/fail thresholds. fileciteturn0file1L948-L1009

---

# 40. Method Configuration UI

The current frontend already presents:

```text
Space: YCrCb
Channel: Y
Partition: 8×8 Blocks
Transform: 2D-DCT-II
JND: α=2.0, β=0.1
Coeffs: C(3,2) ↔ C(2,3)
```

This should remain.

These values should preferably be populated from the backend configuration response rather than duplicated manually in HTML.

This prevents the UI and algorithm from drifting apart.

---

# 41. Pipeline Visualization

Keep:

```text
BGR
 ↓
YCrCb
 ↓
Y
 ↓
8×8 Blocks
 ↓
DCT
 ↓
JND
 ↓
Embed
 ↓
IDCT
 ↓
Watermarked Image
 ↓
Extract
```

This directly represents the current image-stage pipeline.

The project plan defines the same image-to-watermarked-image path and the reverse extraction path. fileciteturn0file1L80-L164

Do not add:

```text
Encrypt
Compress
Synchronize
Motion
Video
Attack Testing
```

because those are outside the current stage.

---

# 42. Metadata

Display only actual backend metadata.

Good fields:

```text
Dimensions
File Size
Processed Blocks
Embedded Bits
Color Space
Embedding Channel
```

Do not display:

```text
Entropy
Security Level
Encryption
Authentication
Compression Resistance
Attack Score
```

unless those are actually implemented.

---

# 43. Difference Image

A difference image may be displayed only if the backend actually generates it.

The current project plan defines:

\[
D=|I'-I|
\]

and proposes a visual difference output. fileciteturn0file1L1013-L1033

If implemented, add:

```text
Difference
```

as another result card.

If not implemented, do not create a fake difference image in the frontend.

---

# 44. File Storage

Use:

```text
uploads/
```

for temporary uploaded input files.

Use:

```text
output/
```

for generated results.

Example:

```text
uploads/
    <unique_cover_name>
    <unique_watermark_name>

output/
    watermarked_<id>.png
    extracted_<id>.png
```

Generated output filenames must be unique enough to prevent collisions between runs.

---

# 45. Temporary File Cleanup

After processing, temporary input files may be deleted when they are no longer needed.

Generated result files should remain available long enough for the frontend to load them.

A simple local prototype does not require sophisticated storage management.

---

# 46. CORS

Prefer serving frontend and backend from the same local origin:

```text
http://localhost:<port>
```

Then frontend requests can use:

```text
/api/watermark
```

without cross-origin configuration.

Do not add CORS middleware unless frontend and backend genuinely run on different origins.

A single local server is simpler for this project.

---

# 47. Static Frontend Serving

The local server should serve:

```text
frontend/index.html
frontend/css/*
frontend/js/*
frontend/assets/*
```

and the generated output resources.

Preferred architecture:

```text
http://localhost:8000/
    → frontend

http://localhost:8000/api/watermark
    → backend

http://localhost:8000/output/...
    → generated result
```

---

# 48. Frontend JavaScript Responsibilities After Integration

## `app.js`

Only application initialization and state coordination.

```text
initialize
bind events
reset state
```

---

## `upload.js`

Only:

```text
file selection
preview generation
filename
dimensions
file size
input state
```

---

## `processing.js`

Only:

```text
FormData
POST request
loading state
API error handling
timing
```

---

## `results.js`

Only:

```text
render result images
render metrics
render metadata
render configuration
result-state transitions
```

The separation prevents the frontend from becoming one large script.

---

# 49. Remove These Functions from the Existing Frontend Workflow

The following current behaviors should be deleted or replaced:

```text
createDefaultCarrier()
createDefaultWatermark()
populateBitGridFromCanvas()

client-side wmBits state
client-side JND loop
client-side block pixel modification
client-side simulated extraction
hard-coded SSIM
hard-coded Bit Accuracy
hard-coded NC
simulated setTimeout processing
fixed estimated processing time
```

The current frontend contains these behaviors explicitly in the page script, including default-image generation, binary-grid generation, and client-side pixel-level simulation. fileciteturn0file0L475-L612 fileciteturn0file0L738-L852

---

# 50. Do Not Preserve the Current Modulo Watermark Repetition

The frontend currently uses:

```javascript
const bitIndex =
    (by * numBlocksX + bx) % 1024;
```

That causes the watermark payload to repeat across blocks.

This is not the baseline sequential mapping described in the current project plan.

Instead:

```text
first watermark bit
    → first selected block

second watermark bit
    → second selected block

...

1024th watermark bit
    → 1024th selected block
```

After all watermark bits are embedded, remaining blocks remain unchanged.

The project plan explicitly defines sequential mapping and deliberately excludes redundancy/randomization at this stage. fileciteturn0file1L572-L596

---

# 51. Block Selection

The baseline mapping should process blocks in raster order:

```text
row 0:
    block 0, block 1, block 2, ...

row 1:
    next block, next block, ...

...
```

Only the number of blocks required by the watermark payload should be modified.

This makes the implementation simple and explainable.

---

# 52. Watermark Payload Metadata

For the default configuration:

```text
Watermark representation: 32 × 32 binary
Payload: 1,024 bits
```

Display:

```text
Payload
1,024 bits
```

Do not describe this as cryptographic payload capacity.

The project is not implementing encryption or secure payload management at this stage.

---

# 53. Watermark Output

The extracted watermark must be created from the bits recovered by the backend.

The backend should not simply return the original watermark file.

The extracted result must genuinely pass through:

```text
watermarked image
    ↓
Y
    ↓
8×8 blocks
    ↓
DCT
    ↓
C(3,2), C(2,3)
    ↓
bit decisions
    ↓
bitstream
    ↓
watermark image
```

This is essential because extraction is one of the milestones of the current project. fileciteturn0file1L24-L38

---

# 54. Original Result

The Original Image card should display exactly the uploaded cover image.

Do not show the synthetic benchmark carrier.

Do not manipulate it for comparison.

It is the reference image used for PSNR/SSIM calculations.

---

# 55. Watermarked Result

The Watermarked Image card must display the exact output generated by:

```text
Python DCT/JND pipeline
```

not a JavaScript simulation.

---

# 56. Extracted Result

The Extracted Watermark card must display the actual reconstructed watermark.

Its metrics should correspond to the actual extracted bits.

---

# 57. Reset / Clear Inputs

The existing button:

```text
Clear Inputs
```

should reset:

```text
cover file
watermark file
cover preview
watermark preview
results
metrics
status
```

It should **not recreate a fake default benchmark image**.

After reset, the application should return to:

```text
Ready
No cover selected
No watermark selected
Awaiting Processing
```

This is a key change from the current frontend's reset behavior, which recreates generated defaults. fileciteturn0file0L728-L735

---

# 58. Initial Application State

On first load:

```text
Status:
Ready

Cover:
Select a cover image

Watermark:
Select a watermark image

Watermarked:
Awaiting Processing

Extracted:
Awaiting Extraction

PSNR:
—

SSIM:
—

Bit Accuracy:
—

NC:
—
```

No output should imply that processing has already happened.

---

# 59. Backend Validation

Before processing:

```text
cover image exists
watermark image exists
files are valid images
watermark payload fits available blocks
```

If any condition fails:

```text
return error
```

Do not silently substitute defaults.

---

# 60. Image Data Precision

The image-processing code should use floating-point arrays during DCT/IDCT calculations.

The existing experiment converts an 8×8 luminance block to `float32` before DCT.

Preserve that behavior.

After reconstruction, clip values appropriately before converting/saving the final image.

Do not do the entire frequency-domain calculation in `uint8`.

---

# 61. Color Handling

OpenCV reads images in:

```text
BGR
```

Use:

```text
BGR → YCrCb
```

Perform embedding only in:

```text
Y
```

Keep:

```text
Cr
Cb
```

unchanged for the baseline.

Then:

```text
Y' + Cr + Cb
    ↓
YCrCb → BGR
```

The project plan explicitly defines this luminance-only arrangement. fileciteturn0file1L190-L225

---

# 62. Padding and Reconstruction

Store the original dimensions:

```python
original_height
original_width
```

Pad Y to:

```text
ceil(width / 8) × 8
ceil(height / 8) × 8
```

Perform block processing.

After reconstruction:

```text
crop padded Y
```

back to:

```text
original_height × original_width
```

Then reconstruct the final image.

This ensures arbitrary source images can be handled while preserving output dimensions.

---

# 63. Output Format

Save generated images as PNG for the local prototype unless the implementation already requires another format.

This avoids introducing an additional lossy compression step into the baseline evaluation.

The original uploaded image format does not need to match the output format.

---

# 64. Metrics and Color Space

PSNR and SSIM should compare:

```text
original cover image
vs
watermarked image
```

using a consistent representation.

For the simplest baseline, use the full reconstructed image in a clearly defined representation.

Do not calculate PSNR on one channel and label it as full-image PSNR unless the UI makes that explicit.

Bit accuracy and NC compare:

```text
original watermark representation
vs
extracted watermark representation
```

---

# 65. Backend/Frontend Contract

The frontend should not need to know internal algorithm details.

Its contract is:

### Input

```text
cover_image
watermark_image
```

### Output

```text
watermarked image URL
extracted watermark URL
metrics
metadata
configuration
```

The mathematical implementation behind that contract can evolve later.

---

# 66. Future-Proofing Without Adding Features

The code should be modular enough that later research additions can be introduced independently.

Possible future replacements include:

```text
jnd.py
embedding.py
extraction.py
metrics.py
```

But do not implement those future features now.

The current image-stage specification intentionally excludes encryption, error correction, pseudo-random embedding, synchronization, temporal watermarking, neural watermarking, and attack-resistance mechanisms. fileciteturn0file1L1157-L1177

---

# 67. Testing Strategy

Before testing through the browser, test the backend directly.

## Test 1 — Existing known image

```text
cover = existing development image
watermark = known test watermark
```

Verify:

```text
watermarked image generated
extracted watermark generated
metrics calculated
```

---

## Test 2 — Landscape photograph

Use a normal landscape image.

Verify:

```text
output retains original dimensions
result preview remains landscape
watermark extraction works
```

---

## Test 3 — Portrait photograph

Verify:

```text
output retains portrait orientation
frontend does not stretch result
```

---

## Test 4 — Non-multiple-of-8 dimensions

Example:

```text
1280 × 721
```

Verify:

```text
internal padding occurs
output returns to 1280 × 721
```

---

## Test 5 — Different watermark aspect ratio

Use:

```text
wide watermark
tall watermark
square watermark
```

Verify that preprocessing converts each to the configured binary representation.

---

# 68. API Integration Test

Use a simple request outside the browser:

```text
POST /api/watermark
cover_image = test.jpg
watermark_image = watermark.png
```

Confirm that:

```text
HTTP response = success
watermarked image exists
extracted watermark exists
metrics are numeric
```

Only after this works should browser integration be considered complete.

---

# 69. Frontend Integration Test

Test this sequence:

```text
1. Load page
2. No default fake images
3. Select cover
4. Cover preview appears
5. Select watermark
6. Watermark preview appears
7. Run button enables
8. Click Run
9. Status becomes Processing
10. Backend processes
11. Status becomes Completed
12. Watermarked output appears
13. Extracted watermark appears
14. Metrics populate
```

Then:

```text
15. Select another cover
16. Previous result clears
17. Select another watermark
18. Run again
19. New results replace previous results
```

---

# 70. Error Test

Test:

```text
cover missing
watermark missing
invalid file
too-small cover for configured payload
backend failure
```

The UI must remain usable after each error.

---

# 71. Performance

Do not optimize prematurely.

The priority order is:

```text
correctness
→ modularity
→ stable API
→ correct results
→ UI integration
→ performance tuning
```

The current project is a local academic prototype, not a production service.

Do not introduce multiprocessing, GPU processing, queues, workers, or caching unless later measurements demonstrate that they are needed.

---

# 72. Security for This Local Prototype

Basic local validation is sufficient.

Do not build:

```text
authentication
authorization
encryption
user accounts
database
```

The application is intended for local development and demonstration.

---

# 73. Remove Misleading Labels

Use terminology consistent with the actual project.

Preferred:

```text
Cover Image
Watermark
Embedding & Extraction Results
Watermarked Image
Extracted Watermark
Luminance Channel
Activity-Based JND
DCT
PSNR
SSIM
Bit Accuracy
Normalized Correlation
```

Avoid terminology that suggests functionality not implemented, such as:

```text
Authentication Signature
Encrypted Payload
Secure Signature
Attack Resistance
Client-Side DCT Engine
```

The frontend currently contains several dashboard-style labels; simplify them where they overstate the underlying functionality. The method configuration itself is accurate and should be retained. fileciteturn0file0L357-L405

---

# 74. Header

Keep the existing project title:

```text
JND-Guided Frequency-Domain Watermarking
```

Keep the concise description:

```text
Perceptual Discrete Cosine Transform (DCT) watermarking
using activity-based JND masking.
```

Keep simple technical badges such as:

```text
YCrCb • Y Channel
8×8 DCT
Ready
```

Do not add standards/compliance claims that are not part of the project.

---

# 75. Processing Card

The existing processing card already communicates:

```text
Perceptual DCT Engine
JND α=2.0, β=0.1
Activity-based JND masking...
Run Watermarking
```

Keep this structure, but make the text describe the actual backend operation.

Do not show:

```text
Estimated ~110ms
```

unless it represents a real measured time.

---

# 76. Local Development Command

The README should document a simple startup flow.

Conceptually:

```bash
# activate virtual environment
# install requirements
# start local web server
```

Then:

```text
Open the local application in the browser.
```

Use the actual command chosen during implementation.

Do not hard-code a framework-specific command in this design document if the final backend framework has not yet been selected.

---

# 77. Dependency Management

The existing project already uses:

```text
numpy
opencv-python
matplotlib
```

The backend will additionally need:

- the selected web framework;
- a suitable SSIM implementation if SSIM is not already implemented.

Update:

```text
requirements.txt
```

after the backend is connected.

Do not add libraries that are not required.

---

# 78. End-to-End Architecture

The final application should look like:

```text
                        ┌─────────────────────┐
                        │    Browser / UI     │
                        │                     │
Cover Image ───────────→│ Upload              │
Watermark ─────────────→│ Preview             │
                        │ Run                 │
                        │ Results             │
                        └─────────┬───────────┘
                                  │
                                  │ POST /api/watermark
                                  ▼
                        ┌─────────────────────┐
                        │    Local Server     │
                        └─────────┬───────────┘
                                  │
                                  ▼
                        ┌─────────────────────┐
                        │ Watermark Pipeline  │
                        │                     │
                        │ image_utils         │
                        │ watermark           │
                        │ DCT                 │
                        │ JND                 │
                        │ embedding           │
                        │ extraction          │
                        │ metrics             │
                        └─────────┬───────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
              Watermarked    Extracted      Metrics
                Image        Watermark
                    │             │             │
                    └─────────────┼─────────────┘
                                  ▼
                        ┌─────────────────────┐
                        │       Browser       │
                        │   Render Results    │
                        └─────────────────────┘
```

---

# 79. Definition of Done

The integration is complete when:

## Frontend

- cover image can be selected;
- watermark image can be selected;
- previews preserve aspect ratios;
- arbitrary supported images can be selected;
- Run Watermarking sends actual files to the backend;
- result layout works for landscape, portrait, and square images;
- no fake default data is required;
- no fake metrics are displayed.

## Backend

- actual YCrCb conversion runs;
- only Y is modified;
- image dimensions are padded when necessary;
- 8×8 blocks are processed;
- DCT is actually applied;
- JND is calculated from block standard deviation;
- C(3,2) and C(2,3) are used;
- watermark bits are embedded according to the defined coefficient relationship;
- IDCT reconstructs blocks;
- output image is rebuilt;
- watermark is genuinely extracted;
- metrics are genuinely calculated.

## Integration

- frontend receives generated output URLs;
- watermarked image renders;
- extracted watermark renders;
- metrics render;
- configuration reflects backend values;
- errors are handled;
- Clear Inputs resets to an empty ready state.

---

# 80. Final Implementation Principle

The frontend is the **visual laboratory**.

The Python modules are the **actual experiment**.

The local API is the **bridge between them**.

The correct final relationship is:

```text
USER
 │
 │ selects images
 ▼
FRONTEND
 │
 │ multipart/form-data
 ▼
LOCAL API
 │
 ▼
WATERMARKING PIPELINE
 │
 ├── YCrCb
 ├── Y channel
 ├── 8×8 blocks
 ├── DCT
 ├── standard deviation
 ├── JND
 ├── C(3,2) / C(2,3)
 ├── embedding
 ├── IDCT
 ├── reconstruction
 ├── extraction
 └── metrics
 │
 ▼
API RESPONSE
 │
 ▼
FRONTEND
 │
 ├── Watermarked Image
 ├── Extracted Watermark
 └── Metrics
```

Do not hide the real algorithm behind a visual simulation.

Do not add new watermarking features.

Do not make the frontend responsible for mathematical processing.

Keep the current Bento interface, replace the simulated processing with the real local backend, and make every displayed image, number, status, and configuration value correspond to the actual implementation.
