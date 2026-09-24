# Stage 1 --- Fastest Video Watermarking Implementation

## Objective

Prove that the existing JND-DCT image watermarking engine can process a
video frame-by-frame, produce a playable watermarked video, and recover
the watermark without uncontrolled memory usage.

This is a baseline, not the final robust video watermarking algorithm.

## 1. Pipeline

``` text
Input Video
    ↓
VideoCapture
    ↓
read ONE frame
    ↓
existing image watermarking engine
    ↓
write ONE frame
    ↓
discard temporary data
    ↓
next frame
    ↓
VideoWriter
    ↓
Watermarked Video
```

Never load the complete video into memory.

## 2. Reuse the current image engine

For every frame:

``` text
BGR
 ↓
YCrCb
 ↓
Y channel
 ↓
8×8 blocks
 ↓
block activity
 ↓
JND
 ↓
DCT
 ↓
DCT coefficient modulation
 ↓
IDCT
 ↓
reconstruct frame
```

The video layer should call this engine rather than duplicate its
mathematics.

## 3. Watermark strategy

For the first prototype, use the **same optimized payload on every
frame**.

``` text
watermark
   ↓
existing optimizer
   ↓
payload
   ↓
same payload embedded into each frame
```

This gives basic temporal redundancy immediately.

### Capacity check

A frame's capacity can vary with its visual activity. For Stage 1:

1.  inspect the first frame
2.  estimate capacity
3.  optimize the watermark to fit
4.  use that payload for the video
5.  verify capacity during each frame's embedding
6.  if a frame cannot hold the payload, stop with a clear frame-number
    error rather than truncating data

Later stages will use true temporal payload scheduling.

## 4. Video input

Use OpenCV:

``` python
cap = cv2.VideoCapture(input_path)
```

Read:

``` python
fps = cap.get(cv2.CAP_PROP_FPS)
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
```

Preserve width, height, FPS, and frame order.

## 5. Video output

Use:

``` python
writer = cv2.VideoWriter(...)
```

Check:

``` python
writer.isOpened()
```

Use a codec/container combination actually supported by the local
OpenCV/FFmpeg installation. Do not hard-code a codec that may be
unavailable.

Always:

``` python
cap.release()
writer.release()
```

inside reliable cleanup logic.

## 6. Core loop

Conceptually:

``` python
while True:
    ok, frame = cap.read()

    if not ok:
        break

    watermarked = embed_watermark(frame, payload)
    writer.write(watermarked)

    # drop references to temporary arrays
```

The critical rule is:

> ONE FRAME IN → ONE FRAME PROCESSED → ONE FRAME OUT.

Never accumulate frames in a Python list.

## 7. Extraction

Sample several frames rather than extracting from only one.

For example:

``` text
frame 0
frame 30
frame 60
frame 90
...
```

For each sampled frame:

``` text
frame
 ↓
Y channel
 ↓
8×8 blocks
 ↓
DCT
 ↓
payload extraction
 ↓
header check
 ↓
CRC check
```

For Stage 1, accept the first valid payload whose header and CRC pass.

If multiple frames succeed, report how many were valid and whether they
produced the same payload.

Majority voting is a later stage.

## 8. CRC

The extracted payload should already contain CRC-32.

``` text
extract
 ↓
parse header
 ↓
recover payload
 ↓
CRC
```

If CRC passes:

``` text
valid frame
```

If it fails:

``` text
try another frame
```

CRC detects corruption; it does not correct it.

## 9. CPU performance plan

### Baseline

First implement and benchmark sequential CPU processing.

Record:

-   total runtime
-   frames/sec
-   peak RAM

### Threaded version

After the sequential implementation is correct, test a bounded thread
pool.

Conceptually:

``` text
Decoder
   ↓
Queue(maxsize=4–8)
   ↓
2/4/... workers
   ↓
Queue(maxsize=4–8)
   ↓
Writer
```

Start with approximately:

``` python
workers = min(4, os.cpu_count() or 1)
```

Then benchmark 2, 4, and other reasonable values.

Do not assume that using every logical core is fastest.

OpenCV operations execute in native code and may release the Python GIL,
but actual scaling must be measured.

## 10. Memory-safety requirements

Use:

``` text
frame: uint8
DCT temporary block: float32
```

Avoid: - all-frames lists - unbounded queues - unnecessary full-frame
copies - float64 unless required - storing every DCT block - retaining
processed frames

Bounded queues are mandatory for the threaded version.

The decoder must stop getting ahead when the queues are full.

## 11. Long-run memory test

Record RAM at intervals:

``` text
start
100 frames
500 frames
1000 frames
2000 frames
...
```

Memory should remain approximately bounded.

A continuously increasing RSS with frame count is a bug, not an
acceptable trade-off.

Run a long/high-resolution video before declaring Stage 1 stable.

## 12. GPU policy

Do not immediately move the pipeline to the GPU.

The current machine has an Intel Arc GPU, so CUDA should not be assumed.

First benchmark:

``` text
sequential CPU
vs
threaded CPU
```

Only then evaluate available Intel-compatible/OpenCL GPU paths.

Never upload the whole video to GPU memory.

If GPU processing is tested, use small bounded batches:

``` text
small batch
 ↓
GPU
 ↓
CPU
 ↓
write
```

Retain the GPU path only if it is measurably faster and remains stable.

## 13. First UI additions

Add:

### Input

-   Cover Video
-   Watermark Image

### Video information

-   resolution
-   FPS
-   duration
-   frame count

### Processing status

-   current frame / total frames
-   progress
-   frames/sec
-   RAM usage

### Result

-   Watermarked Video
-   Extracted Watermark
-   total processing time
-   average FPS
-   peak RAM
-   extraction status
-   CRC status

For the first prototype, sample frames for PSNR/SSIM instead of
performing expensive full-video metric calculations.

## 14. Validation tests

### Test A --- short video

720p, 10--30 seconds.

Verify: - playable output - correct FPS - correct resolution - watermark
extraction

### Test B --- long video

Verify: - stable RAM - no progressive slowdown - clean resource release

### Test C --- different content

Test: - static scene - detailed scene - high-motion scene - dark scene -
bright scene

### Test D --- extraction

Verify: - valid header - CRC verified - reconstructed watermark

## 15. Stage 1 completion checklist

-   [x] Video input works.
-   [x] Frame-by-frame processing works.
-   [x] Existing JND-DCT engine is reused.
-   [x] Output video is playable.
-   [x] Resolution is preserved.
-   [x] FPS is preserved.
-   [x] Watermark is extractable.
-   [x] CRC verification works.
-   [x] Memory remains bounded.
-   [x] Sequential CPU benchmark recorded.
-   [x] Threaded CPU benchmark recorded.
-   [x] Faster stable CPU configuration selected.
-   [x] GPU is used only if benchmarking proves a real benefit.

## 16. Deliberately postponed

Do not implement yet:

-   motion-aware JND
-   scene detection
-   temporal synchronization
-   chunk scheduling
-   Reed--Solomon/BCH ECC
-   pseudo-random/keyed embedding
-   advanced attack resistance
-   sophisticated frame selection
-   large GPU batches

The goal is to get the first video version working **quickly, correctly,
and safely**, then build robustness on top of this baseline.
