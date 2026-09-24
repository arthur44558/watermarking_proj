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
