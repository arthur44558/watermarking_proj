# JND-Guided Frequency-Domain Image Watermarking
## Detailed Implementation Plan — Current Stage

## 1. Purpose and Scope

The current stage is intentionally limited to building and understanding the **smallest complete working unit of the watermarking system**.

The target is:

> Take an image, operate on its luminance component, divide it into 8×8 blocks, transform each block with the DCT, estimate a local perceptual threshold using an activity-based JND approximation, modify selected mid-frequency coefficients to encode watermark bits, reconstruct the image, and then extract the watermark from those coefficients.

We are **not** building the full robust video watermarking system yet.

### The current stage ends when we can reliably perform:

```text
Cover Image + Watermark Image
            │
            ▼
     JND-guided DCT
        embedding
            │
            ▼
     Watermarked Image
            │
            ▼
       DCT extraction
            │
            ▼
     Recovered Watermark
```

We should be able to demonstrate that:

1. The watermark is visually unobtrusive.
2. The watermark can be recovered.
3. The watermarked image remains sufficiently similar to the original.
4. Every major mathematical and implementation step can be explained clearly.

---

# 2. Final Project Architecture for the Image Stage

The project should eventually be organized approximately as follows:

```text
Macro_proj/
│
├── input/
│   ├── test_image.jpeg
│   └── watermark.png
│
├── output/
│   ├── watermarked.png
│   ├── extracted_watermark.png
│   ├── difference.png
│   └── comparison.png
│
├── src/
│   ├── config.py
│   ├── image_utils.py
│   ├── dct.py
│   ├── jnd.py
│   ├── watermark.py
│   ├── embedding.py
│   ├── extraction.py
│   ├── metrics.py
│   └── main.py
│
├── requirements.txt
└── README.md
```

The files should have **single, clear responsibilities**.

We do not need to create all of these files immediately. They will be introduced incrementally.

---

# 3. Complete Algorithm

The final image-level algorithm will be:

```text
Input Image
    │
    ▼
Load image
    │
    ▼
BGR → YCrCb
    │
    ▼
Extract Y (luminance)
    │
    ▼
Pad/crop dimensions to multiples of 8
    │
    ▼
Divide into 8×8 blocks
    │
    ▼
DCT for each block
    │
    ├───────────────┐
    │               │
    ▼               ▼
Local activity     Select mid-frequency
/ standard        DCT coefficient pair
deviation
    │
    ▼
JND approximation
    │
    ▼
Adaptive coefficient modification
    │
    ▼
Inverse DCT
    │
    ▼
Reconstruct modified Y
    │
    ▼
Combine modified Y with original Cr/Cb
    │
    ▼
YCrCb → BGR
    │
    ▼
Watermarked Image
```

Extraction reverses the relevant steps:

```text
Watermarked Image
    │
    ▼
BGR → YCrCb
    │
    ▼
Extract Y
    │
    ▼
8×8 blocks
    │
    ▼
DCT
    │
    ▼
Read selected coefficient relationship
    │
    ▼
Recover bits
    │
    ▼
Reshape bitstream
    │
    ▼
Recovered Watermark
```

---

# 4. Stage A — Load the Image

Use OpenCV:

```python
image = cv2.imread(...)
```

For the current test image:

```text
Resolution: 1080 × 1080
Channels:   3
Data type:  uint8
```

The three channels are B, G and R because OpenCV uses BGR ordering by default.

### Goal

Confirm that the input image can be loaded correctly before doing any processing.

---

# 5. Stage B — Convert BGR to YCrCb

Convert:

\[
BGR \rightarrow YCrCb
\]

and split the result into:

\[
(Y,Cr,Cb)
\]

The watermarking operation is initially performed only on **Y**, the luminance component.

Conceptually:

```text
                 Image
                   │
                   ▼
                 YCrCb
              ┌────┼────┐
              ▼    ▼    ▼
              Y    Cr   Cb
              │
              │
           watermark
```

### Why Y?

Y represents luminance/brightness information, while Cr and Cb represent chrominance.

Keeping Cr and Cb unchanged gives us a simple and controlled first implementation.

---

# 6. Stage C — Make Image Dimensions Compatible with 8×8 Blocks

The DCT processing unit will be:

\[
8\times8
\]

Therefore image dimensions need to be divisible by 8.

The current image happens to satisfy this:

\[
1080 \mod 8 = 0
\]

For a general image, dimensions may not be divisible by 8.

For example:

```text
1920 × 1080
```

is fine, while:

```text
1280 × 721
```

is not.

For the final implementation, use **padding** rather than discarding image content through cropping.

For example:

\[
721 \rightarrow 728
\]

because:

\[
728/8=91
\]

This functionality belongs in `image_utils.py`.

---

# 7. Stage D — Divide the Luminance Image into 8×8 Blocks

Given the luminance image:

\[
Y
\]

partition it into non-overlapping:

\[
8\times8
\]

blocks.

Conceptually:

```text
Y image

┌────┬────┬────┬────┬────┐
│8×8 │8×8 │8×8 │8×8 │ ...│
├────┼────┼────┼────┼────┤
│8×8 │8×8 │8×8 │8×8 │ ...│
├────┼────┼────┼────┼────┤
│... │... │... │... │ ...│
└────┴────┴────┴────┴────┘
```

Each block becomes one processing unit.

For the current 1080×1080 image:

\[
1080/8=135
\]

so there are:

\[
135\times135=18,225
\]

8×8 blocks.

---

# 8. Stage E — DCT Transform

For each 8×8 block:

\[
B
\]

calculate:

\[
C=DCT(B)
\]

This produces 64 frequency-domain coefficients:

\[
C(u,v)
\]

The 2-D DCT represents the block as a weighted combination of cosine basis functions at different spatial frequencies.

For an 8×8 block, the coefficient at:

\[
C(0,0)
\]

is the **DC coefficient**.

The remaining coefficients describe increasing spatial frequencies.

Conceptually:

```text
low frequency                    high frequency
      ↓                                ↓

┌──────────────────────────────────────────────┐
│ DC  low  low  low  medium  high  high  high│
│ low low  low  medium ...                   │
│ low low  medium ...                        │
│ medium ...                                 │
│ ...                                        │
└──────────────────────────────────────────────┘
```

We will not watermark the DC coefficient.

---

# 9. Current DCT Sanity Check

For our first 8×8 block, the spatial-domain mean was:

\[
\mu=170.5
\]

The DCT output gave:

\[
C(0,0)=1364
\]

For the orthonormal DCT used by OpenCV:

\[
C(0,0)=8\mu
\]

Therefore:

\[
8(170.5)=1364
\]

This confirms that the DCT is behaving as expected.

The block is also very smooth because its pixel values only vary roughly from 167 to 174.

That produces a dominant DC coefficient and relatively small AC coefficients.

---

# 10. Stage F — Measure Local Image Activity

The perceptual part begins by estimating how much local variation exists within a block.

For each 8×8 block:

\[
\mu=\frac{1}{64}\sum_{i=1}^{64}x_i
\]

and:

\[
\sigma=
\sqrt{
\frac{1}{64}
\sum_{i=1}^{64}(x_i-\mu)^2
}
\]

Here:

- Low \(\sigma\) → smooth block.
- High \(\sigma\) → highly textured/active block.

The current test block produced:

\[
\mu=170.5
\]

\[
\sigma=1.677051
\]

\[
\sigma^2=2.8125
\]

---

# 11. Stage G — Activity-Based JND Approximation

For the first demonstrator, use the simple model:

\[
\boxed{JND_B=\alpha+\beta\sigma_B}
\]

with initial parameters:

\[
\alpha=2.0
\]

\[
\beta=0.1
\]

Therefore, for our current test block:

\[
JND=2+0.1(1.677051)
\]

\[
\boxed{JND\approx2.167705}
\]

This means our current implementation is using a local activity value to create an adaptive distortion threshold.

### Important terminology

The model should be described honestly as:

> **Activity-based JND approximation**

It should **not** be described as a complete human-visual-system JND model.

This is intentionally a simple first model that is easy to inspect, explain, and experiment with.

Later, the JND module can be replaced or extended with a published, more sophisticated perceptual formulation without changing the rest of the architecture.

---

# 12. Stage H — Select Mid-Frequency Coefficients

For the first implementation, select two mid-frequency DCT coefficients:

\[
C_a=C(3,2)
\]

\[
C_b=C(2,3)
\]

In code:

```python
COEFF_A = (3, 2)
COEFF_B = (2, 3)
```

### Why two coefficients?

The watermark bit can be represented by their relative magnitude.

### Why mid-frequency coefficients?

Very low-frequency/DC modifications can have a strong visual effect.

Very high-frequency coefficients are more vulnerable to removal or alteration by operations such as filtering or compression.

Mid-frequency coefficients are therefore a sensible compromise for the initial demonstrator.

Robustness against attacks is **not** being claimed yet; this is simply the frequency region selected for the first experiment.

---

# 13. Stage I — Convert the Watermark Image into Bits

Use a small watermark image, for example:

```text
watermark.png
```

Resize it to a fixed size such as:

\[
32\times32
\]

Convert to grayscale, then threshold to produce:

\[
W(x,y)\in\{0,1\}
\]

The 32×32 watermark contains:

\[
32\times32=1024
\]

bits.

Thus:

```text
32 × 32 watermark
        ↓
1024 binary values
```

The bitstream is then embedded into image blocks.

---

# 14. Stage J — Map Watermark Bits to Image Blocks

For the first implementation, use simple sequential mapping:

```text
Block 0     → watermark bit 0
Block 1     → watermark bit 1
Block 2     → watermark bit 2
...
Block 1023  → watermark bit 1023
```

The 1080×1080 test image contains 18,225 blocks, so it has sufficient block capacity for a 1024-bit watermark.

### Why keep this simple?

Because the purpose of this stage is to understand the embedding mechanism, not yet to solve:

- synchronization,
- security,
- randomization,
- redundancy,
- or attack resistance.

Those are later stages.

---

# 15. Stage K — Embed One Watermark Bit

This is the central operation.

Define:

\[
A=C(3,2)
\]

\[
B=C(2,3)
\]

and the target separation:

\[
T=JND
\]

For bit `1`, enforce:

\[
A-B\geq T
\]

For bit `0`, enforce:

\[
B-A\geq T
\]

Conceptually:

```text
bit = 1

A ───────────────
        >
B ─────


bit = 0

B ───────────────
        >
A ─────
```

---

# 16. Stage L — Modify the Coefficients

Suppose we are embedding `1` and:

\[
A-B<T
\]

First calculate the required gap:

\[
d=T-(A-B)
\]

Then distribute the modification equally:

\[
A'=A+\frac d2
\]

\[
B'=B-\frac d2
\]

This produces:

\[
A'-B'=T
\]

For a bit `0`, do the opposite:

\[
B'=B+\frac d2
\]

\[
A'=A-\frac d2
\]

This creates a directional relationship between the selected frequency coefficients.

---

# 17. Example from the Current Experiment

For the actual first block, the measured coefficients were approximately:

\[
A=0.3256
\]

\[
B=-0.0602
\]

Therefore:

\[
A-B\approx0.3858
\]

The JND was:

\[
JND\approx2.1677
\]

For bit `1`, the required correction was:

\[
\frac{2.1677-0.3858}{2}\approx0.8909
\]

So:

\[
A'\approx1.2166
\]

\[
B'\approx-0.9512
\]

and therefore:

\[
A'-B'\approx2.1677
\]

The inverse DCT then produced spatial-domain changes of only about a few tenths of a luminance level.

This illustrates an important property of frequency-domain embedding:

> A deliberate modification in frequency space can appear as a small, distributed spatial-domain perturbation.

---

# 18. Embedding Strength / Safety Margin

The initial demonstrator can use:

\[
T=JND
\]

However, this places the coefficient relationship exactly at the threshold.

A later experimental control should therefore allow:

\[
\boxed{T=k\cdot JND}
\]

where \(k\) is a tunable factor.

For example:

```text
k = 1.0
k = 1.25
k = 1.5
k = 2.0
```

This parameter can be called:

```python
JND_SCALE
```

The important tradeoff is:

```text
Higher embedding strength
        ↓
Larger coefficient separation
        ↓
Potentially easier extraction
        ↓
Greater image distortion
```

This tradeoff will become one of the main experiments in the image stage.

---

# 19. Stage M — Inverse DCT

After modifying the selected coefficients:

\[
C\rightarrow C'
\]

perform:

\[
B'=IDCT(C')
\]

This converts the modified frequency representation back into the spatial domain.

Because the selected basis functions extend over the block, the resulting changes are distributed across multiple pixels.

---

# 20. Stage N — Reconstruct the Modified Luminance Image

After processing all required blocks, place every modified block back into its original position.

This reconstructs:

\[
Y'
\]

The structure is:

```text
Original Y

┌────┬────┬────┐
│ B1 │ B2 │ B3 │
├────┼────┼────┤
│ B4 │ B5 │ B6 │
├────┼────┼────┤
│... │... │... │
└────┴────┴────┘

        ↓

Modified Y'

┌────┬────┬────┐
│ B1'│ B2'│ B3'│
├────┼────┼────┤
│ B4'│ B5'│ B6'│
├────┼────┼────┤
│... │... │... │
└────┴────┴────┘
```

---

# 21. Stage O — Recombine Y, Cr and Cb

The modified luminance channel is combined with the original chroma channels:

\[
(Y',Cr,Cb)
\]

Then convert back:

\[
YCrCb\rightarrow BGR
\]

This produces:

```text
output/watermarked.png
```

The chroma channels have not been modified.

---

# 22. Stage P — Extract the Watermark

Extraction begins with:

```text
watermarked.png
```

Perform:

```text
BGR → YCrCb
       ↓
      Y
       ↓
    8×8 blocks
       ↓
      DCT
```

For each watermark-bearing block, read:

\[
A=C(3,2)
\]

\[
B=C(2,3)
\]

Then determine:

\[
A>B\Rightarrow1
\]

\[
B>A\Rightarrow0
\]

For the initial demonstration, this simple comparison is sufficient.

---

# 23. Stage Q — Reconstruct the Watermark

Collect all extracted bits:

```text
1 1 0 0 1 0 1 1 ...
```

For a 32×32 watermark:

\[
1024\text{ bits}\rightarrow32\times32
\]

Then save:

```text
output/extracted_watermark.png
```

The result can be compared directly with the original watermark.

---

# 24. Metrics

The project should evaluate more than visual appearance.

## 24.1 PSNR

Mean squared error:

\[
MSE=
\frac1N\sum(I-I')^2
\]

Then:

\[
PSNR=
10\log_{10}
\left(
\frac{MAX^2}{MSE}
\right)
\]

This provides a numerical measure of how much the image changed.

---

## 24.2 SSIM

Structural Similarity Index (SSIM) gives another measure of similarity between the original and watermarked images.

It should be used alongside PSNR rather than as a replacement.

---

## 24.3 Watermark Bit Accuracy

For extracted watermark \(W'\):

\[
Accuracy=
\frac{\text{correctly extracted bits}}
{\text{total bits}}
\]

This tells us how accurately the payload was recovered.

---

## 24.4 Normalized Correlation

Use:

\[
NC=
\frac{\sum W_iW'_i}
{\sqrt{\sum W_i^2\sum {W'_i}^2}}
\]

This measures similarity between the original and recovered watermark.

For the first implementation, **bit accuracy and NC are sufficient watermark-quality metrics**.

---

# 25. Difference Image

Create a difference image:

\[
D=|I'-I|
\]

Since these differences may be visually tiny, amplify them for display.

Save:

```text
output/difference.png
```

This allows direct visualization of:

> Where did the watermarking algorithm modify the image?

The difference image is especially useful at zoomed-in scale.

---

# 26. Final Visualization

Eventually the demonstration should show four outputs:

```text
┌────────────────────┬────────────────────┐
│ Original           │ Watermarked        │
│                    │                    │
├────────────────────┼────────────────────┤
│ Difference         │ Extracted          │
│                    │ Watermark          │
└────────────────────┴────────────────────┘
```

Alongside:

```text
PSNR          : xx.xx dB
SSIM          : 0.xxxx
Bit Accuracy  : xx.xx %
NC            : 0.xxxx
```

This makes the system easy to demonstrate and explain.

---

# 27. Required Experiments Before Completing the Image Stage

## Experiment 1 — Embedding Strength

Test:

\[
k=1.0,\ 1.25,\ 1.5,\ 2.0
\]

Record:

```text
JND scale
PSNR
SSIM
Watermark bit accuracy
NC
```

Study the tradeoff between imperceptibility and recoverability.

---

## Experiment 2 — Smooth vs Textured Blocks

Select:

```text
smooth block
```

and:

```text
high-texture block
```

Calculate:

\[
\sigma
\]

and:

\[
JND
\]

Compare them to show that the threshold adapts according to local activity.

---

## Experiment 3 — Visual Inspection

Compare:

```text
Original
Watermarked
Difference
```

at:

- full-image scale,
- zoomed-in scale,
- smooth areas,
- textured areas.

---

## Experiment 4 — Watermark Payload Size

Test several watermark sizes, for example:

\[
16\times16
\]

\[
32\times32
\]

\[
64\times64
\]

Observe how payload size affects capacity and image quality.

---

# 28. Features Deliberately Excluded at This Stage

Do **not** add the following yet:

```text
❌ AES/encryption
❌ Chaotic maps
❌ Error-correcting codes
❌ Pseudo-random block selection
❌ Synchronization methods
❌ Motion-vector methods
❌ Temporal watermarking
❌ Spread spectrum
❌ SVD
❌ Wavelets
❌ Neural/deep-learning watermarking
❌ Complex perceptual models
❌ Attack-resistance mechanisms
```

These are later stages.

The purpose now is to make the foundational method understandable and measurable.

---

# 29. Final Code Responsibilities

## `config.py`

Stores tunable parameters:

```python
BLOCK_SIZE = 8

COEFF_A = (3, 2)
COEFF_B = (2, 3)

JND_ALPHA = 2.0
JND_BETA = 0.1

JND_SCALE = 1.0

WATERMARK_SIZE = (32, 32)
```

Keeping these values centralized makes experiments easy.

---

## `image_utils.py`

Responsible for:

```text
Image loading
Image saving
BGR ↔ YCrCb conversion
Padding
Image/block reconstruction
```

---

## `dct.py`

Responsible only for:

```text
8×8 block → DCT
DCT coefficients → 8×8 block
```

---

## `jnd.py`

Responsible for:

```text
Block → local activity
Local activity → JND
```

Core function:

```python
calculate_jnd(block)
```

---

## `watermark.py`

Responsible for:

```text
Watermark image
        ↓
Grayscale/binarization
        ↓
Bitstream
```

and:

```text
Bitstream
        ↓
Binary image
```

---

## `embedding.py`

Contains the core embedding operation:

```text
block + bit + JND
        ↓
modified block
```

This is the main encoder logic.

---

## `extraction.py`

Contains:

```text
watermarked block
        ↓
DCT
        ↓
inspect Ca and Cb
        ↓
recover bit
```

---

## `metrics.py`

Contains:

```text
PSNR
SSIM
Bit accuracy
Normalized correlation
```

---

## `main.py`

Coordinates the complete experiment:

```text
Load image
    ↓
Preprocess
    ↓
Convert watermark → bits
    ↓
Embed watermark
    ↓
Reconstruct watermarked image
    ↓
Save output
    ↓
Extract watermark
    ↓
Reconstruct watermark image
    ↓
Calculate metrics
    ↓
Generate visualizations
```

---

# 30. Explanation We Should Ultimately Be Able to Give

Once the image stage is complete, the core explanation should be:

> “The watermark is converted into a binary sequence. The host image is converted to YCrCb, and watermarking is performed on the luminance component. The luminance image is divided into 8×8 blocks, and each block is transformed into the frequency domain using the DCT. For each block, local spatial activity is measured using standard deviation and converted into an activity-based JND threshold. Two mid-frequency DCT coefficients are selected. A watermark bit is encoded by forcing a controlled difference between those coefficients, with the required modification determined by the local JND. The modified coefficients are transformed back using the inverse DCT and the image is reconstructed. During extraction, the same blocks and coefficients are analyzed, and the direction of the coefficient relationship is used to recover the embedded bitstream. The bitstream is reshaped into the watermark image, and PSNR, SSIM, bit accuracy, and normalized correlation are used to evaluate the result.”

This is the central narrative of the first milestone.

---

# 31. Implementation Order

Follow this order:

```text
CURRENT PROGRESS
       │
       ▼
✓ Load image
       │
       ▼
✓ Extract luminance
       │
       ▼
✓ Inspect 8×8 block
       │
       ▼
✓ DCT
       │
       ▼
✓ Activity/JND calculation
       │
       ▼
✓ Embed one bit
       │
       ▼
→ Extract one bit
       │
       ▼
→ Implement full-image block processing
       │
       ▼
→ Create binary watermark
       │
       ▼
→ Embed complete watermark
       │
       ▼
→ Extract complete watermark
       │
       ▼
→ Reconstruct watermark image
       │
       ▼
→ PSNR / SSIM / accuracy / NC
       │
       ▼
→ Difference visualization
       │
       ▼
→ Parameter experiments
       │
       ▼
→ Clean up codebase
       │
       ▼
IMAGE WATERMARKING MILESTONE
```

---

# 32. Relationship to the Later Video Stage

The image-level algorithm should be kept independent of video handling.

Later, the same image algorithm can be applied frame-by-frame:

```text
                  IMAGE ALGORITHM

          embed_watermark(frame)
                     │
                     ▼
              watermarked frame


                   VIDEO

frame 1 ──────→ image algorithm
frame 2 ──────→ image algorithm
frame 3 ──────→ image algorithm
   ⋮
frame N ──────→ image algorithm
```

This means the mathematics and embedding logic learned during the image stage remain directly useful when the project progresses to video.

The video stage will then introduce temporal considerations rather than requiring us to redesign the fundamental DCT/JND embedding mechanism.

---

# 33. Core Philosophy of the Current Stage

The guiding rule for this milestone is:

> **Understand the mechanism first, then scale it.**

We are deliberately moving through:

```text
one block
   ↓
one bit
   ↓
many blocks
   ↓
complete watermark
   ↓
complete image
   ↓
video frames
```

This keeps the implementation easy to debug, easy to visualize, and easy to explain academically.
