# JND-Guided Frequency-Domain Image Watermarking

An imperceptible and robust image watermarking system based on 2D Discrete Cosine Transform (DCT) and activity-based Just Noticeable Difference (JND) perceptual masking.

---

## 1. Overview & Architecture

This implementation realizes the foundational image-level milestone outlined in `JND_guided_frequency_domain_image_watermarking_implementation_plan.md`.

The system operates strictly on the luminance ($Y$) channel of the input image, leaving color channels ($Cr$, $Cb$) pristine:
1. **Luminance Extraction**: Converts BGR image to $YCrCb$ color space and isolates $Y$.
2. **Block Partitioning**: Divides $Y$ into non-overlapping $8 \times 8$ pixel blocks.
3. **2D DCT Transform**: Maps spatial blocks into 64 frequency coefficients.
4. **Activity-Based JND Estimation**: Calculates local standard deviation $\sigma_B$ for each block to compute an adaptive distortion threshold $JND_B = (\alpha + \beta \sigma_B) \times k$.
5. **Adaptive Embedding**: Selects mid-frequency DCT coefficients $C_a = C(3, 2)$ and $C_b = C(2, 3)$. Symmetrically adjusts $C_a$ and $C_b$ to enforce $C_a - C_b \ge T$ for bit `1` or $C_b - C_a \ge T$ for bit `0`.
6. **Reconstruction**: Computes 2D IDCT, reconstructs the $Y'$ channel, recombines with original $Cr, Cb$, and converts back to BGR.
7. **Blind Extraction**: Converts watermarked image to $Y$, calculates 2D DCT for each block, and evaluates the sign of $C(3, 2) - C(2, 3)$ to recover the watermark bitstream without needing the original cover image.

```text
Macro_proj/
├── input/
│   ├── test_image.jpeg
│   └── watermark.png
├── output/
│   ├── watermarked.png
│   ├── extracted_watermark.png
│   ├── difference.png
│   ├── comparison.png
│   └── zoom_inspection.png
├── src/
│   ├── config.py          # Centralized hyperparameter configuration
│   ├── image_utils.py     # Image I/O, color conversions, padding, block splitting
│   ├── dct.py             # 2D DCT and IDCT transformations
│   ├── jnd.py             # Activity-based JND threshold calculation
│   ├── watermark.py       # Watermark binarization, bitstream serialization
│   ├── embedding.py       # JND-guided DCT watermark encoder
│   ├── extraction.py      # Blind DCT watermark decoder
│   ├── metrics.py         # PSNR, SSIM, Bit Accuracy, NC, difference visualizations
│   ├── experiments.py     # Section 27 experimental evaluation suite
│   └── main.py            # Complete end-to-end pipeline driver
├── requirements.txt
└── README.md
```

---

## 2. Mathematical Formulations

### 2.1 Discrete Cosine Transform (DCT)
For an $8 \times 8$ block $B(x, y)$:
$$C(u, v) = \alpha(u) \alpha(v) \sum_{x=0}^{7} \sum_{y=0}^{7} B(x, y) \cos\left[\frac{(2x+1)u\pi}{16}\right] \cos\left[\frac{(2y+1)v\pi}{16}\right]$$

### 2.2 Activity-Based JND
For block standard deviation $\sigma_B = \sqrt{\frac{1}{64} \sum_{i=1}^{64} (x_i - \mu)^2}$:
$$JND_B = (\alpha + \beta \sigma_B) \times k$$
- Default parameters: $\alpha = 2.0$, $\beta = 0.1$, $k = 1.0$ (`JND_SCALE`).

### 2.3 Embedding Rule
With mid-frequency coefficient pair $A = C(3, 2)$ and $B = C(2, 3)$ and target threshold $T = JND_B$:
- **For bit 1**: Enforce $A - B \ge T$. If $A - B < T$, let $d = T - (A - B)$, then:
  $$A' = A + \frac{d}{2}, \quad B' = B - \frac{d}{2}$$
- **For bit 0**: Enforce $B - A \ge T$. If $B - A < T$, let $d = T - (B - A)$, then:
  $$B' = B + \frac{d}{2}, \quad A' = A - \frac{d}{2}$$

### 2.4 Extraction Rule
$$W_i' = \begin{cases} 1 & \text{if } C(3, 2) > C(2, 3) \\ 0 & \text{otherwise} \end{cases}$$

---

## 3. Usage & Running Instructions

The project is configured to run with **Python 3.14**.

### Run the Main Pipeline
Executes embedding, extraction, metric calculation, and artifact generation:
```powershell
py -3.14 src/main.py
```

### Run Section 27 Experiments
Executes all 4 experimental evaluations (strength scaling, smooth vs textured blocks, visual zoom crops, and payload scaling):
```powershell
py -3.14 src/experiments.py
```

---

## 4. Output Artifacts

All outputs are saved to the `output/` directory:
- `output/watermarked.png`: Reconstructed watermarked BGR image.
- `output/extracted_watermark.png`: Recovered binary watermark image.
- `output/difference.png`: Magnified difference image ($|I' - I| \times 25$).
- `output/comparison.png`: 2×2 composite comparison board with embedded metrics.
- `output/zoom_inspection.png`: Zoomed crop comparison of smooth vs textured regions.
