"""
Watermark payload framing, compression, serialization, and reconstruction module.
Converts arbitrary grayscale/RGB images into framed byte streams and reconstructs them.
Supports RAW_ZLIB (lossless), WebP, and JPEG codecs via the 32-byte framing header.
"""

from pathlib import Path
from typing import Tuple, Dict, Any, Union
import binascii
import struct
import zlib
import cv2
import numpy as np

from .config import (
    HEADER_MAGIC,
    HEADER_VERSION,
    HEADER_SIZE_BYTES,
    MAX_WATERMARK_WIDTH,
    MAX_WATERMARK_HEIGHT,
    CODEC_RAW_ZLIB,
    CODEC_WEBP,
    CODEC_JPEG,
)


def serialize_watermark(
    img: np.ndarray,
    channels_used: int = 1,
    codec: int = CODEC_RAW_ZLIB,
    quality: int = 100,
    orig_width: int = 0,
    orig_height: int = 0,
    enforce_limit: bool = True,
) -> bytes:
    """
    Serialize and compress an arbitrary grayscale or RGB watermark image into a framed payload.

    Frame Header (32 bytes):
        [0:4]   Magic: 'JNDW' (4 bytes)
        [4:5]   Version: 2 (1 byte)
        [5:6]   Channels Used in Carrier: 1 (Y) or 3 (Y, Cr, Cb) (1 byte)
        [6:7]   Color Mode: 0 (Grayscale), 1 (RGB/BGR) (1 byte)
        [7:8]   Codec: 0 (RAW_ZLIB), 1 (WebP), 2 (JPEG) (1 byte)
        [8:9]   Quality: 0-100 (1 byte, 100 = lossless)
        [9:10]  Reserved: 0x00 (1 byte)
        [10:12] Original Width: uint16 (2 bytes, big-endian)
        [12:14] Original Height: uint16 (2 bytes, big-endian)
        [14:16] Optimized Width: uint16 (2 bytes, big-endian)
        [16:18] Optimized Height: uint16 (2 bytes, big-endian)
        [18:22] Original Uncompressed Bytes: uint32 (4 bytes, big-endian)
        [22:26] Compressed Payload Bytes: uint32 (4 bytes, big-endian)
        [26:30] CRC32 Checksum: uint32 (4 bytes, big-endian, over compressed payload)
        [30:32] Reserved: 0x0000 (2 bytes)

    Args:
        img: 2D (Grayscale) or 3D (RGB/BGR) numpy array (uint8).
        channels_used: 1 for Y-channel only, 3 for YCrCb multi-channel.
        codec: CODEC_RAW_ZLIB, CODEC_WEBP, or CODEC_JPEG.
        quality: Compression quality (100 = lossless for RAW_ZLIB).
        orig_width: Original watermark width before optimization (0 = same as current).
        orig_height: Original watermark height before optimization (0 = same as current).

    Returns:
        bytes: Complete framed payload (Header + Compressed Data).
    """
    if not isinstance(img, np.ndarray) or img.dtype != np.uint8:
        raise ValueError("Watermark image must be a uint8 numpy array.")

    if img.ndim == 2:
        color_mode = 0  # Grayscale
        h, w = img.shape
    elif img.ndim == 3 and img.shape[2] == 3:
        color_mode = 1  # RGB / BGR
        h, w = img.shape[:2]
    else:
        raise ValueError(
            f"Unsupported watermark array shape: {img.shape}. Expected 2D (grayscale) or 3D 3-channel (color)."
        )

    if w > MAX_WATERMARK_WIDTH or h > MAX_WATERMARK_HEIGHT:
        raise ValueError(
            f"Watermark dimensions ({w}x{h}) exceed maximum supported limits ({MAX_WATERMARK_WIDTH}x{MAX_WATERMARK_HEIGHT})."
        )

    # Use current dimensions as original if not specified
    if orig_width == 0:
        orig_width = w
    if orig_height == 0:
        orig_height = h

    raw_bytes = img.tobytes()
    orig_len = len(raw_bytes)

    # Encode payload based on codec
    if codec == CODEC_RAW_ZLIB:
        compressed_data = zlib.compress(raw_bytes, level=9)
    elif codec == CODEC_WEBP:
        encode_params = [cv2.IMWRITE_WEBP_QUALITY, int(quality)]
        success, encoded = cv2.imencode('.webp', img, encode_params)
        if not success:
            raise ValueError("Failed to encode watermark as WebP.")
        compressed_data = encoded.tobytes()
    elif codec == CODEC_JPEG:
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, int(quality)]
        if img.ndim == 2:
            success, encoded = cv2.imencode('.jpg', img, encode_params)
        else:
            success, encoded = cv2.imencode('.jpg', img, encode_params)
        if not success:
            raise ValueError("Failed to encode watermark as JPEG.")
        compressed_data = encoded.tobytes()
    else:
        raise ValueError(f"Unknown codec identifier: {codec}")

    comp_len = len(compressed_data)
    crc = binascii.crc32(compressed_data) & 0xFFFFFFFF

    # Pack 32-byte header: >4s B B B B B B H H H H I I I H
    header = struct.pack(
        ">4s B B B B B B H H H H I I I H",
        HEADER_MAGIC,
        HEADER_VERSION,
        int(channels_used),
        int(color_mode),
        int(codec),
        int(quality),
        0,  # Reserved byte
        int(orig_width),
        int(orig_height),
        int(w),       # Optimized (current) width
        int(h),       # Optimized (current) height
        int(orig_len),
        int(comp_len),
        int(crc),
        0,  # Reserved 2 bytes
    )

    assert len(header) == HEADER_SIZE_BYTES, f"Header size mismatch: {len(header)} != {HEADER_SIZE_BYTES}"

    payload = header + compressed_data
    return payload


def unpack_header(header_bytes: bytes) -> Dict[str, Any]:
    """
    Unpack and validate the 32-byte payload framing header.
    """
    if len(header_bytes) < HEADER_SIZE_BYTES:
        raise ValueError(
            f"Insufficient header data: got {len(header_bytes)} bytes, expected {HEADER_SIZE_BYTES} bytes."
        )

    (
        magic, ver, channels_used, color_mode, codec, quality, reserved,
        orig_w, orig_h, opt_w, opt_h,
        orig_len, comp_len, crc, reserved2
    ) = struct.unpack(
        ">4s B B B B B B H H H H I I I H", header_bytes[:HEADER_SIZE_BYTES]
    )

    if magic != HEADER_MAGIC:
        raise ValueError(
            "No valid JND watermarking header detected. The image does not appear to contain a compatible embedded payload."
        )

    codec_name_map = {CODEC_RAW_ZLIB: "RAW_ZLIB", CODEC_WEBP: "WebP", CODEC_JPEG: "JPEG"}

    return {
        "magic": magic.decode("latin1", errors="replace"),
        "version": int(ver),
        "channels_used": int(channels_used),
        "color_mode": "Grayscale" if color_mode == 0 else "RGB",
        "color_mode_code": int(color_mode),
        "codec": int(codec),
        "codec_name": codec_name_map.get(int(codec), f"Unknown({codec})"),
        "quality": int(quality),
        "original_width": int(orig_w),
        "original_height": int(orig_h),
        "width": int(opt_w),
        "height": int(opt_h),
        "original_len": int(orig_len),
        "compressed_len": int(comp_len),
        "crc32": int(crc),
        "total_payload_bytes": HEADER_SIZE_BYTES + int(comp_len),
    }


def deserialize_watermark(payload_bytes: bytes, enforce_crc: bool = True) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Deserialize, validate CRC32, decompress/decode, and reconstruct the watermark image.

    For RAW_ZLIB: losslessly decompresses to exact original pixel data.
    For WebP/JPEG: decodes encoded image bytes via cv2.imdecode.

    Args:
        payload_bytes: Complete framed payload (Header + Compressed Data).
        enforce_crc: If True, raises ValueError when CRC32 fails. If False,
            records CRC mismatch in metadata and attempts reconstruction.

    Returns:
        reconstructed_image: 2D (Grayscale) or 3D (RGB/BGR) uint8 numpy array.
        metadata: Dictionary containing parsed header metadata and CRC verification status.
    """
    meta = unpack_header(payload_bytes)
    comp_len = meta["compressed_len"]
    orig_len = meta["original_len"]
    color_mode = 0 if meta["color_mode_code"] == 0 else 1
    codec = meta["codec"]
    w = min(MAX_WATERMARK_WIDTH, max(1, meta["width"]))
    h = min(MAX_WATERMARK_HEIGHT, max(1, meta["height"]))
    expected_crc = meta["crc32"]

    total_expected = HEADER_SIZE_BYTES + comp_len
    if len(payload_bytes) < total_expected:
        if enforce_crc:
            raise ValueError(
                f"Truncated payload: expected {total_expected} bytes, received {len(payload_bytes)} bytes."
            )
        compressed_data = payload_bytes[HEADER_SIZE_BYTES:]
    else:
        compressed_data = payload_bytes[HEADER_SIZE_BYTES : total_expected]

    actual_crc = binascii.crc32(compressed_data) & 0xFFFFFFFF
    crc_match = (actual_crc == expected_crc)
    meta["crc_match"] = crc_match
    meta["actual_crc"] = int(actual_crc)
    meta["expected_crc"] = int(expected_crc)
    meta["crc_status"] = (
        "Passed (CRC32 Verified)"
        if crc_match
        else f"CRC Mismatch (expected {hex(expected_crc)}, got {hex(actual_crc)})"
    )

    if enforce_crc and not crc_match:
        raise ValueError(
            f"Payload integrity check failed: CRC32 mismatch (expected {hex(expected_crc)}, got {hex(actual_crc)}). "
            f"The embedded watermark data is corrupted."
        )

    if codec == CODEC_RAW_ZLIB:
        raw_bytes = None
        try:
            raw_bytes = zlib.decompress(compressed_data)
        except Exception:
            # Salvage partial decompression if possible
            try:
                d = zlib.decompressobj()
                raw_bytes = d.decompress(compressed_data)
            except Exception:
                raw_bytes = b""

        expected_shape_bytes = h * w * (1 if color_mode == 0 else 3)
        if raw_bytes is None:
            raw_bytes = b"\x00" * expected_shape_bytes
        elif len(raw_bytes) < expected_shape_bytes:
            raw_bytes = raw_bytes + b"\x00" * (expected_shape_bytes - len(raw_bytes))
        elif len(raw_bytes) > expected_shape_bytes:
            raw_bytes = raw_bytes[:expected_shape_bytes]

        try:
            if color_mode == 0:
                reconstructed = np.frombuffer(raw_bytes, dtype=np.uint8).reshape((h, w)).copy()
            else:
                reconstructed = np.frombuffer(raw_bytes, dtype=np.uint8).reshape((h, w, 3)).copy()
        except Exception:
            reconstructed = (
                np.zeros((h, w), dtype=np.uint8)
                if color_mode == 0
                else np.zeros((h, w, 3), dtype=np.uint8)
            )

    elif codec in (CODEC_WEBP, CODEC_JPEG):
        nparr = np.frombuffer(compressed_data, np.uint8)
        if color_mode == 0:
            reconstructed = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
        else:
            reconstructed = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if reconstructed is None:
            if color_mode == 0:
                reconstructed = np.zeros((h, w), dtype=np.uint8)
            else:
                reconstructed = np.zeros((h, w, 3), dtype=np.uint8)
        elif reconstructed.shape[:2] != (h, w):
            reconstructed = cv2.resize(reconstructed, (w, h), interpolation=cv2.INTER_NEAREST)
    else:
        if enforce_crc:
            raise ValueError(f"Unknown codec identifier in header: {codec}")
        if color_mode == 0:
            reconstructed = np.zeros((h, w), dtype=np.uint8)
        else:
            reconstructed = np.zeros((h, w, 3), dtype=np.uint8)

    return reconstructed, meta


def load_watermark_image(source: Union[Path, str, np.ndarray, bytes]) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Load an arbitrary image watermark without lossy thresholding or downsizing.
    Handles transparency by stripping alpha channel cleanly onto white background.

    Returns:
        img: np.ndarray (2D grayscale or 3D BGR)
        info: Dictionary of format, dimensions, mode, and byte sizes.
    """
    if isinstance(source, np.ndarray):
        img = source
        detected_format = "NUMPY"
    elif isinstance(source, (bytes, bytearray)):
        nparr = np.frombuffer(source, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
        detected_format = "BUFFER"
    else:
        path_obj = Path(source)
        if not path_obj.exists():
            raise FileNotFoundError(f"Watermark file not found: {source}")
        detected_format = path_obj.suffix.upper().lstrip(".")
        img = cv2.imread(str(path_obj), cv2.IMREAD_UNCHANGED)

    if img is None:
        raise ValueError("Could not decode watermark image from the provided source.")

    # Process channels
    if img.ndim == 2:
        color_mode = "Grayscale"
        h, w = img.shape
        processed_img = img
    elif img.ndim == 3 and img.shape[2] == 4:
        # Strip alpha cleanly onto white background
        b, g, r, a = cv2.split(img)
        alpha = a.astype(float) / 255.0
        bgr = cv2.merge([b, g, r]).astype(float)
        white_bg = np.full_like(bgr, 255.0)
        processed_img = (bgr * alpha[:, :, np.newaxis] + white_bg * (1.0 - alpha[:, :, np.newaxis])).astype(np.uint8)
        color_mode = "RGB"
        h, w = processed_img.shape[:2]
    elif img.ndim == 3 and img.shape[2] == 3:
        # Check if BGR channels are identical (i.e. visually grayscale saved as RGB)
        if np.array_equal(img[:, :, 0], img[:, :, 1]) and np.array_equal(img[:, :, 1], img[:, :, 2]):
            processed_img = img[:, :, 0]
            color_mode = "Grayscale"
            h, w = processed_img.shape
        else:
            processed_img = img
            color_mode = "RGB"
            h, w = processed_img.shape[:2]
    else:
        raise ValueError(f"Unsupported watermark array shape: {img.shape}")

    if w > MAX_WATERMARK_WIDTH or h > MAX_WATERMARK_HEIGHT:
        raise ValueError(
            f"Watermark dimensions ({w}x{h}) exceed maximum allowed dimensions "
            f"({MAX_WATERMARK_WIDTH}x{MAX_WATERMARK_HEIGHT})."
        )

    # Calculate compressed size (lossless RAW_ZLIB estimate)
    raw_size = processed_img.nbytes
    comp_size = len(zlib.compress(processed_img.tobytes(), level=9))
    encoded_payload_size = HEADER_SIZE_BYTES + comp_size

    info = {
        "format": detected_format,
        "width": int(w),
        "height": int(h),
        "color_mode": color_mode,
        "raw_bytes": int(raw_size),
        "compressed_bytes": int(comp_size),
        "payload_bytes": int(encoded_payload_size),
        "compression_ratio": round(raw_size / max(comp_size, 1), 2),
    }

    return processed_img, info
