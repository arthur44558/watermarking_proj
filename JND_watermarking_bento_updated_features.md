# JND-Guided Frequency-Domain Watermarking
## Local Web Application — Updated UI & Functional Specification

This specification updates the existing local Bento-style watermarking application.

The existing visual structure should be preserved. The additions below are functional extensions to the current image watermarking workflow only.

Do not add unrelated features, authentication, cloud storage, databases, video processing, encryption, attack simulation, or other future-stage functionality.

---

# 1. Core Workflow

The application must support two modes through the same interface.

## Mode A — Embed + Verify

When both a cover image and a watermark image are provided:

```text
Cover Image + Watermark
          ↓
      Watermarking
          ↓
Watermarked / Extracted Image
          +
Extracted Watermark
```

The application embeds the watermark into the cover image and then extracts the watermark from the generated result.

The purpose is to verify the complete pipeline:

```text
image + watermark
=
watermarked image + extracted watermark
```

---

## Mode B — Extract Existing Watermark

When only an image is provided and no watermark is supplied:

```text
Image
  ↓
Watermark Extraction
  ↓
Watermarked / Extracted Image
  +
Extracted Watermark
```

In this mode, the supplied image is treated as an already-watermarked image.

The application must attempt to extract the watermark using the existing extraction mechanism.

The supplied image itself should be shown in the `Watermarked / Extracted Image` result area as the raw input image.

The extracted watermark should appear in the `Extracted Watermark` area.

There must be no requirement to provide the original watermark for extraction.

---

# 2. Result Title Change

Rename the current result card:

```text
Watermarked Image
```

to:

```text
Watermarked / Extracted Image
```

This title applies because the same result area has two possible meanings.

### When a watermark is supplied

It displays:

```text
Generated Watermarked Image
```

### When no watermark is supplied

It displays:

```text
Input Image Used for Extraction
```

The card title remains:

```text
Watermarked / Extracted Image
```

A small contextual badge can indicate:

```text
Embedded
```

or:

```text
Extraction Input
```

Do not create a separate large result card for these two modes.

---

# 3. Input Logic

The application has two inputs:

```text
Cover Image
Watermark
```

The watermark input is optional.

## Both supplied

Run:

```text
Embedding → Reconstruction → Extraction
```

## Only cover image supplied

Run:

```text
Extraction
```

## Neither supplied

Do not run processing.

Show the normal empty state.

---

# 4. Run Button Behavior

The existing button:

```text
Run Watermarking
```

should remain the main action button.

Its label should change according to the available inputs.

### Cover + Watermark

```text
Run Watermarking
```

### Cover only

```text
Extract Watermark
```

This makes the current operation immediately understandable.

Do not create two separate large action buttons.

---

# 5. Input Cards

Keep the existing Bento layout.

## Cover Image

The current Cover Image card remains the primary image input.

The user should be able to:

- browse for an image;
- preview it;
- view its dimensions;
- click the preview to enlarge it.

---

## Watermark

The current Watermark card remains the watermark input.

The user should be able to:

- browse for an image;
- preview it;
- view its dimensions;
- click the preview to enlarge it.

The watermark is optional for extraction-only mode.

The card should visually indicate this:

```text
WATERMARK IMAGE
Optional for extraction
```

Do not make the optional state visually dominant.

---

# 6. Click-to-Zoom Image Viewer

Add a reusable image lightbox/modal.

This must work for:

1. uploaded cover image;
2. uploaded watermark image;
3. generated watermarked/extracted image;
4. extracted watermark.

The user should be able to click any displayed image to enlarge it.

---

# 7. Image Zoom Behavior

When the user clicks an image:

```text
Page
 ↓
Darkened / subdued overlay
 ↓
Large image viewer
```

The viewer should display the image at a larger size while preserving its original aspect ratio.

Use:

```css
object-fit: contain;
```

Do not crop the image.

---

# 8. Lightbox Controls

The zoom viewer should have:

- close button;
- image title;
- enlarged image.

The viewer should close when:

- the close button is clicked;
- the user clicks outside the image;
- the user presses `Escape`.

No advanced image editor is required.

Do not add:

- image filters;
- crop tools;
- drawing tools;
- annotation tools;
- rotation;
- color adjustment.

This is only a viewing/zoom feature.

---

# 9. Reusable Image Viewer Component

Create one reusable component rather than implementing four separate zoom systems.

Conceptually:

```text
ImageViewer
    ├── image
    ├── title
    └── close
```

Any image card can invoke it:

```javascript
openImageViewer(imageUrl, title)
```

Example:

```text
openImageViewer(
    coverImageUrl,
    "Cover Image"
)
```

and:

```text
openImageViewer(
    watermarkImageUrl,
    "Watermark"
)
```

and:

```text
openImageViewer(
    resultImageUrl,
    "Watermarked / Extracted Image"
)
```

and:

```text
openImageViewer(
    extractedWatermarkUrl,
    "Extracted Watermark"
)
```

---

# 10. Download Watermarked / Extracted Image

Add a download control to the:

```text
Watermarked / Extracted Image
```

result card.

The button should be compact and secondary to the image itself.

Example:

```text
[ Download Image ]
```

or an icon with an accessible label:

```text
Download
```

---

# 11. Download Extracted Watermark

Add a download control to the:

```text
Extracted Watermark
```

result card.

Example:

```text
[ Download Watermark ]
```

The downloaded file must contain the actual extracted watermark generated by the backend.

Do not reconstruct or approximate it in the browser.

---

# 12. Download Rules

Downloads should only appear when the corresponding result exists.

Before processing:

```text
No download button
```

After successful processing:

```text
Download Watermarked / Extracted Image
Download Extracted Watermark
```

The download buttons should use the actual generated output files.

---

# 13. Result Card — Watermarked / Extracted Image

The existing result card should be renamed and retain the current Bento styling.

Header:

```text
Watermarked / Extracted Image
```

Possible contextual badge:

```text
Embedded
```

or:

```text
Extraction Input
```

The image should be clickable for zooming.

Footer controls:

```text
[ Download ]
```

The card should remain aspect-ratio-aware.

Do not force landscape images into a tall fixed-height container.

---

# 14. Result Card — Extracted Watermark

Header:

```text
Extracted Watermark
```

The extracted watermark should:

- preserve its aspect ratio;
- be clickable to zoom;
- show its relevant metadata;
- provide a download button after extraction.

Possible footer:

```text
NC: 0.9998
1,024 bits reconstructed
[ Download ]
```

Only show metrics that the backend actually calculates.

---

# 15. Extraction-Only Result Behavior

Suppose the user selects:

```text
Cover Image:
watermarked_image.png

Watermark:
not selected
```

The application must not show:

```text
Awaiting Watermark
```

or block execution.

Instead:

```text
Input detected
Extraction mode
```

The button becomes:

```text
Extract Watermark
```

After execution:

```text
Watermarked / Extracted Image
    ↓
Original supplied image

Extracted Watermark
    ↓
Recovered watermark
```

This is the key new workflow.

---

# 16. Extraction-Only Metadata

In extraction-only mode, the result card can show:

```text
Mode: Extraction Only
```

and:

```text
Input: Supplied Image
```

The watermark result can show:

```text
Extraction completed
```

If the backend calculates extraction confidence, bit accuracy, NC, or another metric without requiring the original watermark, display only the metrics that are genuinely available.

Do not fabricate verification metrics when the original watermark is unknown.

---

# 17. Important Metric Rule for Extraction-Only Mode

When the original watermark is not provided, the application cannot calculate comparison metrics such as:

```text
Bit Accuracy
Normalized Correlation
```

against the original watermark.

Therefore, in extraction-only mode:

```text
Bit Accuracy
—
```

and:

```text
Normalized Correlation
—
```

unless an independent reference exists.

Do not display:

```text
100%
NC = 1
```

simply because extraction succeeded.

The system has extracted a watermark; it has not independently verified that watermark against a known reference.

---

# 18. Embed + Verify Metrics

When both inputs are provided, the application can calculate comparison-based metrics because it has both:

```text
Original Watermark
Extracted Watermark
```

The results area can show:

```text
PSNR
SSIM
Bit Accuracy
Normalized Correlation
```

provided the backend actually calculates them.

This mode is the full:

```text
Embedding + Extraction Verification
```

workflow.

---

# 19. Extraction-Only Metrics

When only the image is supplied, the results area should adapt.

For example:

```text
PSNR
—

SSIM
—

Bit Accuracy
—

Normalized Correlation
—

Extraction Status
Completed
```

Do not leave misleading values from a previous run.

Every new processing operation must clear or replace stale metrics.

---

# 20. State Reset Rules

When the user changes the cover image:

```text
Clear old results
Clear old metrics
Clear old extracted watermark
```

When the user changes the watermark:

```text
Clear old results
Clear old metrics
Clear old extracted watermark
```

When the user clicks:

```text
Clear Inputs
```

clear:

- cover input;
- watermark input;
- previews;
- generated outputs;
- extracted watermark;
- metrics;
- processing status.

This prevents results from one image/watermark pair from being incorrectly associated with another.

---

# 21. Backend API

The existing endpoint can support both modes.

Example:

```text
POST /api/watermark
```

### Embed + Verify

Request:

```text
cover_image
watermark_image
```

Backend performs:

```text
Embedding
→ Watermarked image
→ Extraction
→ Extracted watermark
→ Metrics
```

---

### Extraction Only

Request:

```text
cover_image
```

with no watermark field.

Backend performs:

```text
Input image
→ Extraction
→ Extracted watermark
```

The input image itself becomes the result displayed in:

```text
Watermarked / Extracted Image
```

---

# 22. Backend Mode Detection

The backend can determine the mode from whether the watermark file exists.

Conceptually:

```python
if watermark_image is not None:
    mode = "embed_and_verify"
else:
    mode = "extract_only"
```

Then:

```python
if mode == "embed_and_verify":
    result = embed_and_extract(cover, watermark)

elif mode == "extract_only":
    result = extract_only(cover)
```

Do not duplicate the extraction algorithm.

Both modes should use the same `extraction.py` implementation.

---

# 23. High-Level Pipeline

The pipeline should expose two clear services.

## Embed + Extract

```python
embed_and_extract(cover_image, watermark_image)
```

Conceptually:

```text
Cover
 ↓
YCrCb
 ↓
Y
 ↓
8×8 blocks
 ↓
DCT
 ↓
JND
 ↓
Embed bits
 ↓
IDCT
 ↓
Watermarked image
 ↓
Extract
 ↓
Extracted watermark
 ↓
Metrics
```

---

## Extract Only

```python
extract_only(watermarked_image)
```

Conceptually:

```text
Input image
 ↓
YCrCb
 ↓
Y
 ↓
8×8 blocks
 ↓
DCT
 ↓
Coefficient comparison
 ↓
Recovered bits
 ↓
Extracted watermark
```

The extraction implementation itself should be shared.

---

# 24. Critical Limitation of Blind Extraction

The extraction-only workflow must use whatever assumptions the current extraction implementation requires to determine:

- watermark dimensions;
- number of embedded bits;
- block mapping.

If these parameters are currently fixed or inferred from the implementation, keep those assumptions explicit in the backend.

Do not invent a new synchronization or metadata system.

For the current prototype, the extraction-only mode is a demonstration of the existing extraction mechanism, not a fully generalized blind watermarking protocol.

If the current extractor requires a fixed watermark size such as:

```text
32 × 32
```

that limitation should be represented honestly in the UI/configuration.

---

# 25. Frontend State

Extend the application state to include processing mode.

Conceptually:

```javascript
{
    coverImage: null,
    watermarkImage: null,

    coverPreview: null,
    watermarkPreview: null,

    mode: "idle",
    processing: false,

    result: null,
    error: null
}
```

Possible modes:

```text
idle
embed_and_verify
extract_only
processing
completed
error
```

The actual implementation may simplify this, but the UI must distinguish the two processing workflows.

---

# 26. Action Button State

### No cover

```text
Run button disabled
```

### Cover only

```text
Extract Watermark
```

enabled.

### Cover + watermark

```text
Run Watermarking
```

enabled.

### Processing

```text
Processing...
```

disabled.

### Completed with watermark

```text
Run Watermarking
```

available again.

### Completed without watermark

```text
Extract Watermark
```

available again.

---

# 27. Visual Mode Indicator

A small badge in the processing card can show:

```text
EMBED + VERIFY
```

when both inputs exist.

Or:

```text
EXTRACT ONLY
```

when only the cover image exists.

Keep this subtle.

Do not add another large panel.

---

# 28. Processing Card Copy

Current technical description can remain concise.

For embedding:

```text
Activity-based JND masking calculates block thresholds and
modifies selected mid-band luminance DCT coefficients.
```

For extraction:

```text
The supplied image is analyzed in the DCT domain to recover
the embedded watermark from the selected coefficient relationship.
```

Avoid claiming robustness or authentication beyond what the current implementation actually performs.

---

# 29. Image Card Layout

For all image cards, use an aspect-ratio-aware preview.

Conceptual CSS:

```css
.image-preview {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    border-radius: 12px;
}

.image-preview img {
    display: block;
    max-width: 100%;
    max-height: 360px;
    width: auto;
    height: auto;
    object-fit: contain;
}
```

Do not assign a large fixed portrait height to result cards.

A 1920×1200 image should remain visibly landscape.

A square watermark should remain square.

A portrait image should remain portrait.

---

# 30. Image Click Affordance

Make it visually apparent that images are clickable.

A subtle treatment is enough:

```text
cursor: zoom-in;
```

Optionally show a small zoom icon on hover.

Do not permanently overlay large controls over the image.

---

# 31. Download Button Placement

Keep downloads inside the relevant result cards.

Example:

```text
Watermarked / Extracted Image

[ IMAGE ]

PSNR: 52.41 dB

[ Download Image ]
```

and:

```text
Extracted Watermark

[ IMAGE ]

NC: 1
1024 bits reconstructed

[ Download Watermark ]
```

The download controls should not dominate the card.

---

# 32. Download File Names

Use descriptive generated filenames.

For embed + verify:

```text
watermarked_<original-name>.png
extracted_watermark_<watermark-name>.png
```

For extraction-only:

```text
extraction_input_<original-name>.png
extracted_watermark.png
```

Avoid overwriting previous results.

---

# 33. No New Image Editing Features

The image viewer is strictly for viewing.

Do not add:

- crop;
- rotate;
- brightness;
- contrast;
- filters;
- resize controls;
- drawing;
- annotations.

The application is a watermarking prototype, not an image editor.

---

# 34. Final User Experience

## Scenario A — Embedding

User does:

```text
1. Choose Cover Image
2. Choose Watermark
3. Click Run Watermarking
```

Application does:

```text
Cover + Watermark
        ↓
Embedding
        ↓
Watermarked / Extracted Image
        +
Extracted Watermark
        +
Verification Metrics
```

---

## Scenario B — Extraction

User does:

```text
1. Choose an already-watermarked image
2. Leave Watermark empty
3. Click Extract Watermark
```

Application does:

```text
Image
  ↓
Extraction
  ↓
Watermarked / Extracted Image
  +
Extracted Watermark
```

The first result is simply the supplied image.

The second result is the recovered watermark.

No comparison-based watermark accuracy should be shown because there is no reference watermark.

---

# 35. Final UI Structure

The existing Bento layout remains:

```text
┌───────────────────────────────────────────────────────────────┐
│ Header                                                        │
├───────────────────────────────┬───────────────────────────────┤
│ Cover Image                   │ Processing                    │
│                               │                               │
│ Upload + Preview              │ Run Watermarking /            │
│                               │ Extract Watermark             │
├───────────────────────────────┤                               │
│ Watermark                     ├───────────────────────────────┤
│                               │ Watermarked / Extracted Image │
│ Upload + Preview              │                               │
│                               ├───────────────────────────────┤
│                               │ Extracted Watermark           │
├───────────────────────────────┴───────────────────────────────┤
│ Metrics                                                       │
├───────────────────────────────────────────────────────────────┤
│ Method / Pipeline                                             │
└───────────────────────────────────────────────────────────────┘
```

The exact grid can retain the current implementation because the current screenshot already has a strong structure.

The important changes are:

- image previews are clickable;
- downloads are available for generated outputs;
- watermark input is optional;
- the action changes based on available inputs;
- the result title becomes `Watermarked / Extracted Image`;
- extraction-only mode is supported;
- metrics adapt to the selected mode.

---

# 36. Definition of Done

The update is complete when:

### Image interaction

- Cover image can be clicked and enlarged.
- Watermark image can be clicked and enlarged.
- Watermarked/extracted result can be clicked and enlarged.
- Extracted watermark can be clicked and enlarged.
- Viewer preserves image aspect ratio.
- Viewer closes through button, outside click, or Escape.

### Downloads

- Watermarked/extracted image can be downloaded.
- Extracted watermark can be downloaded.
- Buttons only appear when outputs exist.
- Downloads contain the actual generated files.

### Embedding mode

```text
Cover + Watermark
→ Watermarked / Extracted Image
→ Extracted Watermark
→ Metrics
```

works.

### Extraction mode

```text
Cover only
→ Watermarked / Extracted Image = supplied image
→ Extracted Watermark
```

works.

### Correct metrics

- Embed + verify can show comparison metrics.
- Extraction-only does not falsely show Bit Accuracy or NC against an unknown reference.
- Old metrics are cleared when inputs change.
- No stale results survive a new processing operation.

### UI

- Result title is `Watermarked / Extracted Image`.
- Layout remains Bento.
- Landscape images are not forced into tall portrait containers.
- All image previews preserve aspect ratio.
- No unrelated features have been introduced.

---

# 37. Final Interaction Model

The central concept of the application should now be visually and functionally obvious:

```text
                    ┌───────────────┐
                    │  Cover Image  │
                    └───────┬───────┘
                            │
                 ┌──────────┴──────────┐
                 │                     │
          Watermark provided      No watermark
                 │                     │
                 ↓                     ↓
          EMBED + EXTRACT          EXTRACT ONLY
                 │                     │
                 ↓                     ↓
     Watermarked / Extracted   Watermarked / Extracted
            Image                     Image
                 │                     │
                 └──────────┬──────────┘
                            ↓
                 Extracted Watermark
```

This keeps the application simple while making the two capabilities immediately understandable.
