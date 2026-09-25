# Original User Request

## Initial Request — 2026-09-24T18:20:36Z

Add memory-bounded Stage 1 video watermarking to the existing JND-guided DCT image watermarking studio, supporting dual image/video uploads with in-browser playback, comprehensive automated tests, and self-updating technical documentation.

Working directory: c:/Users/ASUS/Desktop/Projects/Macro_proj
Integrity mode: development

## Partitioned Agent Roles & Environments

### Agent 1: Video Core Engine (`src/watermarking/video_pipeline.py`)
- Strictly restricted to core video processing logic.
- Must implement frame-by-frame streaming via OpenCV (`VideoCapture` -> embed -> `VideoWriter`) without accumulating frames in memory.
- Provide codec fallback (`mp4v`, `avc1`, `XVID`) and robust resource release (`release()` in `finally`).
- Implement sampled frame extraction with CRC32 verification.

### Agent 2: Web API & UI Integration (`src/web/`, `frontend/`)
- Strictly restricted to endpoint routing and browser interface.
- Keep the current image watermarking workflow 100% functional.
- Enhance the cover dropzone to accept video files (`.mp4`, `.avi`, `.mov`, `.webm`) as well as images.
- Display an interactive `<video controls>` element in the watermarked results card when video is processed, while showing image comparisons for image inputs.

### Agent 3: Test Verification & Benchmarks (`tests/test_video_pipeline.py`)
- Strictly restricted to test suite creation and benchmark validations.
- Create automated test cases verifying short video embedding, FPS/resolution preservation, watermark extraction, and bounded memory behavior.
- Ensure all existing 24 tests remain passing.

### Agent 4: Architecture Documentation (`ARCHITECTURE.md`)
- Strictly restricted to creating reference documentation so future engineers and AI agents do not have to parse the entire codebase.
- Embed a mandatory directive at the top requiring any future AI/agent to update `ARCHITECTURE.md` after modifying the project.

## Acceptance Criteria

### Dual-Media Support & Playback
- [ ] Users can upload either an image or video to the cover carrier slot.
- [ ] When a video is input, the watermarked output displays and plays back seamlessly in the UI.
- [ ] When an image is input, the existing side-by-side image comparison remains completely intact.

### Memory-Safe Streaming
- [ ] Video watermarking operates frame-by-frame; memory does not grow proportionally with video length.
- [ ] Extracted watermark passes header checks and CRC32 verification across sampled frames.

### Quality & Regression Guardrails
- [ ] All 24 existing unit, optimizer, robustness, and API tests pass without regression.
- [ ] New video pipeline tests pass successfully.
- [ ] `start.bat` launches the server and opens the application without error.

### Documentation Directive
- [ ] `ARCHITECTURE.md` is generated covering components, dataflow, and API/UI specs.
- [ ] Prominent directive included at the top instructing any AI agent to update the documentation upon making changes.

## Follow-up — 2026-09-24T19:00:25Z

**Task**: implement the JND_watermarking_universal_aspect_ratio_resolution_support.md file

Working directory: c:/Users/ASUS/Desktop/Projects/Macro_proj
Integrity mode: development

## Requirements
### R1. Universal Aspect Ratio & Resolution Handling
Support universal aspect ratios (e.g. 1:1, 16:9, 9:16, 4:3, 21:9, arbitrary non-standard dimensions, and odd dimensions) for both cover media (images and video) and watermark payloads according to `JND_watermarking_universal_aspect_ratio_resolution_support.md`.

### R2. Core Engine & Optimizer Integration
Ensure the block partitioning, padding/unpadding, carrier capacity calculations, and watermark optimization adapt seamlessly to any resolution and aspect ratio without distortion or cropping.

### R3. Automated Test Verification & Regression Guard
Ensure all 32 existing tests pass, and add comprehensive unit and integration tests verifying universal aspect ratio and resolution support.

### R4. Self-Updating Documentation
Update `ARCHITECTURE.md` and `README.md` with the new capability specifications, preserving the mandatory AI directive at the top.

## Acceptance Criteria
- [ ] Universal aspect ratios and arbitrary non-multiple-of-8 resolutions embed and extract with 100% bit accuracy and CRC32 verification.
- [ ] All existing 32 tests pass without regression.
- [ ] `start.bat` continues to operate cleanly.
- [ ] `ARCHITECTURE.md` is updated.

