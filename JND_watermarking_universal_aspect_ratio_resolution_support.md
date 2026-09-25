# Universal Aspect Ratio & Resolution Support

## Requirement

All image and video inputs throughout the watermarking system must support **arbitrary aspect ratios and resolutions**.

The system must never assume fixed dimensions such as:

- 1920×1080
- 1080×1080
- 16:9
- 9:16

Every stage must dynamically adapt to the actual dimensions of the supplied input.

---

## 1. Cover Images

Cover images must support:

- Any supported resolution
- Any aspect ratio
- Landscape images
- Portrait images
- Square images
- Ultrawide images
- Non-standard/custom dimensions

The watermarked output must preserve the **exact original width and height** unless the user explicitly requests otherwise.

There must be:

- No automatic stretching
- No forced aspect-ratio conversion
- No unnecessary cropping
- No letterboxing

---

## 2. Watermark Images

Watermark images must also support:

- Any supported resolution
- Any aspect ratio
- Portrait, landscape, square, and custom shapes
- Arbitrary dimensions within the project's overall payload constraints

There must be no fixed watermark size such as 32×32.

The watermark optimizer must preserve the watermark's aspect ratio.

If downscaling is required to fit the available payload capacity, dimensions must be reduced proportionally.

Example:

```text
Original:
1920 × 1200

Optimized:
1280 × 800
```

not:

```text
1280 × 720
```

unless the original aspect ratio happens to match.

---

## 3. Video Inputs

Videos must support arbitrary:

- Width
- Height
- Aspect ratio
- FPS
- Duration

Examples that must be supported:

```text
1920 × 1080    16:9
1080 × 1920    9:16
1080 × 1080    1:1
3840 × 1600    ultrawide
1280 × 960     4:3
```

The watermarked video must preserve:

- Original width
- Original height
- Original aspect ratio
- Original frame ordering
- Original FPS where the selected output codec permits it

There must be:

- No stretching
- No forced 16:9 conversion
- No automatic letterboxing
- No unnecessary cropping

---

# 4. 8×8 DCT Block Handling

The watermarking algorithm uses 8×8 DCT blocks, so input dimensions will not always be divisible by 8.

For example:

```text
1279 × 719
```

cannot be divided perfectly into 8×8 blocks.

The implementation must handle these edge cases without changing the final output dimensions.

## Recommended strategy: temporary padding

Pad internally to the next multiple of 8:

```text
Original:
1279 × 719

Temporary processing size:
1280 × 720
```

Perform:

```text
8×8 block processing
DCT
JND calculation
Embedding
IDCT
```

Then crop the processed result back to:

```text
1279 × 719
```

The padded pixels must never appear in the final output.

---

## 5. Padding Requirements

Padding must:

- be temporary
- preserve the original image content
- not alter the requested output dimensions
- use a deterministic padding strategy
- not unnecessarily reduce watermark capacity
- be excluded from final metric calculations

Suitable padding strategies can be evaluated, such as edge replication or reflection.

The chosen strategy should be consistent between embedding and any internal processing that depends on the padded boundary.

---

# 6. Dynamic Capacity Calculation

Capacity must be calculated from the **actual carrier dimensions and actual embedding configuration**.

Do not use a fixed capacity such as:

```text
28 KB
```

for every image or video.

Instead, calculate capacity from factors such as:

```text
number of usable 8×8 blocks
×
bits available per block
×
JND/perceptual constraints
×
embedding configuration
```

For video, capacity may additionally depend on:

```text
number of usable frames
×
usable capacity per frame
×
temporal payload strategy
```

The system must determine capacity dynamically for each input.

---

# 7. Watermark Optimization

Watermark optimization must use the **actual available capacity** of the supplied carrier.

Example:

```text
Carrier A
1920 × 1080
    ↓
Capacity = X

Carrier B
1080 × 1920
    ↓
Capacity = Y

Carrier C
640 × 480
    ↓
Capacity = Z
```

The watermark optimizer must adapt accordingly.

If the watermark is already small enough:

```text
No unnecessary compression
```

If it is too large:

```text
Lossless optimization
    ↓
Quality-based compression
    ↓
Dimension reduction if necessary
```

Aspect ratio must remain unchanged during dimension reduction.

---

# 8. Output Dimension Preservation

### Image

```text
Input:
1279 × 719

Output:
1279 × 719
```

### Video

```text
Input:
1080 × 1920

Output:
1080 × 1920
```

No internal padding may leak into the final output.

---

# 9. UI Preview Requirements

The web interface must also support arbitrary aspect ratios.

Images and video previews should:

- preserve intrinsic aspect ratio
- fit within the available card/container
- avoid distortion
- avoid unnecessary cropping
- use `object-fit: contain` or an equivalent aspect-ratio-preserving strategy where appropriate

For landscape images, the preview must not force a square crop simply to fit the Bento card.

For portrait images, the same applies.

The UI card may have a fixed size, but the media itself must preserve its original proportions.

---

# 10. Metrics

Quality metrics must be calculated using the correct original and processed dimensions.

If temporary padding is used internally, padded pixels must not distort the reported metrics.

Compare:

```text
Original image
vs
Final cropped watermarked image
```

using the exact original dimensions.

The same principle applies to sampled video-frame metrics.

---

# 11. Video Frame Consistency

Every frame of a video must maintain the same:

```text
width
height
```

as the original video.

Temporary padding may be applied internally per frame when required for 8×8 processing, but each processed frame must be cropped back before writing.

The video encoder must receive frames of the expected output dimensions consistently.

---

# 12. Unsupported or Invalid Inputs

The system should reject an input only when it genuinely violates a supported technical limitation, such as:

- unsupported file format
- corrupt file
- dimensions too large for available system resources
- payload cannot fit even after reaching the configured minimum watermark quality/resolution
- video codec cannot be decoded or encoded by the available backend

Do not reject a file merely because it has an unusual aspect ratio or non-standard dimensions.

---

# 13. Memory Considerations

Universal resolution support must not mean unlimited memory allocation.

For large images/videos:

- process images using bounded memory
- process video frame-by-frame
- use `float32` for DCT calculations where appropriate
- avoid loading complete videos into RAM
- use bounded queues in multithreaded processing
- keep GPU batches bounded if GPU acceleration is used

High-resolution inputs should increase processing time and/or dynamically constrain payload capacity rather than causing uncontrolled memory growth.

---

# 14. Validation Matrix

The implementation should be tested with combinations such as:

### Images

```text
1920 × 1080   16:9
1080 × 1920   9:16
1080 × 1080    1:1
1279 × 719    non-multiple-of-8
1000 × 1500   2:3
3840 × 1600   ultrawide
```

### Videos

```text
1920 × 1080
1080 × 1920
1080 × 1080
1280 × 960
3840 × 1600
non-multiple-of-8 dimensions
```

For each test verify:

- input loads successfully
- output dimensions are identical
- aspect ratio is preserved
- no stretching occurs
- no unwanted cropping occurs
- DCT processing works
- watermark embedding works
- extraction works
- metrics are valid
- memory remains bounded

---

# 15. Core Principle

The entire application should follow this rule:

> **Dimensions are properties of the input, not assumptions of the algorithm.**

Every part of the system — preprocessing, DCT blocking, JND calculation, capacity estimation, watermark optimization, embedding, extraction, metrics, previews, and video encoding — must dynamically adapt to the actual input dimensions while preserving the original aspect ratio and final resolution.

