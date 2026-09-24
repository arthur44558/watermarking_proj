"""
Watermark extraction algorithms for JND-guided DCT watermarking.
Extracts framed multi-bit payloads blindly from carrier blocks and reconstructs arbitrary watermark images.
"""

from typing import Tuple, Dict, Any, List
import numpy as np

from .config import (
    BLOCK_SIZE,
    COEFF_PAIRS_16,
    BITS_PER_BLOCK,
    HEADER_SIZE_BYTES,
    HEADER_BLOCKS,
    COEFF_A,
    COEFF_B,
)
from .dct import apply_dct
from .image_utils import pad_image, split_into_blocks, bgr_to_ycrcb
from .payload import unpack_header, deserialize_watermark


def extract_block_bits(
    block: np.ndarray,
    pairs: List[Tuple[Tuple[int, int], Tuple[int, int]]] = COEFF_PAIRS_16,
    max_bits: int = BITS_PER_BLOCK,
) -> List[int]:
    """
    Extract up to 16 bits from an 8x8 spatial domain image block using multi-pair DCT coefficient comparison.

    Rule:
        For each pair (C_a, C_b):
        If C_a > C_b => bit 1, else bit 0.

    Args:
        block: 8x8 spatial domain numpy array.
        pairs: List of DCT coordinate pairs.
        max_bits: Maximum bits to extract from this block.

    Returns:
        List[int]: Binary bits (0 or 1).
    """
    dct_blk = apply_dct(block.astype(np.float32))
    num_to_read = min(len(pairs), max_bits)
    bits = []
    for i in range(num_to_read):
        ca, cb = pairs[i]
        bits.append(1 if dct_blk[ca] > dct_blk[cb] else 0)
    return bits


def extract_bit(
    block: np.ndarray,
    coeff_a: Tuple[int, int] = COEFF_A,
    coeff_b: Tuple[int, int] = COEFF_B,
) -> int:
    """Legacy 1-bit extraction helper for backward compatibility."""
    bits = extract_block_bits(block, pairs=[(coeff_a, coeff_b)], max_bits=1)
    return bits[0]


def extract_bits_from_channel(
    channel: np.ndarray,
    num_bits: int,
    start_block: int = 0,
) -> np.ndarray:
    """
    Extract a sequence of bits from an image channel's 8x8 blocks in raster order.
    """
    orig_h, orig_w = channel.shape[:2]
    full_rows = orig_h // BLOCK_SIZE
    full_cols = orig_w // BLOCK_SIZE
    total_full_blocks = full_rows * full_cols

    padded_channel, _ = pad_image(channel, block_size=BLOCK_SIZE)
    blocks = split_into_blocks(padded_channel, block_size=BLOCK_SIZE)
    num_w = blocks.shape[1]
    flat_blocks = blocks.reshape(-1, BLOCK_SIZE, BLOCK_SIZE)

    extracted_bits = []
    cur_block = start_block

    while len(extracted_bits) < num_bits and cur_block < total_full_blocks:
        r = cur_block // full_cols
        c = cur_block % full_cols
        padded_idx = r * num_w + c

        needed = num_bits - len(extracted_bits)
        blk_bits = extract_block_bits(flat_blocks[padded_idx], pairs=COEFF_PAIRS_16, max_bits=min(BITS_PER_BLOCK, needed))
        extracted_bits.extend(blk_bits)
        cur_block += 1

    return np.array(extracted_bits, dtype=np.uint8)


def extract_framed_payload(watermarked_bgr: np.ndarray) -> bytes:
    """
    Blindly extract the full framed payload bytes from a watermarked carrier image.
    1. Extracts 32-byte header from the first 16 blocks of Y channel.
    2. Parses header to determine compressed length and channels used.
    3. Extracts remaining payload bytes from Y (or Y, Cr, Cb) channels.

    Returns:
        bytes: Raw framed payload bytes (Header + Compressed Data).
    """
    orig_h, orig_w = watermarked_bgr.shape[:2]
    full_rows = orig_h // BLOCK_SIZE
    full_cols = orig_w // BLOCK_SIZE
    total_blocks = full_rows * full_cols
    y_capacity_bits = total_blocks * BITS_PER_BLOCK

    y_chan, cr_chan, cb_chan = bgr_to_ycrcb(watermarked_bgr)

    # 1. Extract 32-byte header (256 bits = 16 blocks @ 16 bits/block)
    header_bits = extract_bits_from_channel(y_chan, num_bits=HEADER_SIZE_BYTES * 8, start_block=0)
    if len(header_bits) < HEADER_SIZE_BYTES * 8:
        raise ValueError("Image does not contain enough blocks for the 32-byte watermarking header.")

    header_bytes = bytearray()
    for i in range(HEADER_SIZE_BYTES):
        val = 0
        for s in range(8):
            val = (val << 1) | int(header_bits[i * 8 + s])
        header_bytes.append(val)

    # 2. Parse and validate header
    meta = unpack_header(bytes(header_bytes))
    comp_len = meta["compressed_len"]
    channels_used = meta["channels_used"]
    total_payload_bytes = HEADER_SIZE_BYTES + comp_len
    total_payload_bits = total_payload_bytes * 8

    # 3. Extract remaining payload bits
    if channels_used == 1:
        all_bits = extract_bits_from_channel(y_chan, num_bits=total_payload_bits, start_block=0)
    else:
        # Multi-channel: Y, then Cr, then Cb
        bits_y = extract_bits_from_channel(y_chan, num_bits=min(total_payload_bits, y_capacity_bits), start_block=0)
        rem_bits = total_payload_bits - len(bits_y)

        if rem_bits > 0:
            bits_cr = extract_bits_from_channel(cr_chan, num_bits=min(rem_bits, y_capacity_bits), start_block=0)
            rem_bits -= len(bits_cr)

            if rem_bits > 0:
                bits_cb = extract_bits_from_channel(cb_chan, num_bits=rem_bits, start_block=0)
                all_bits = np.concatenate([bits_y, bits_cr, bits_cb])
            else:
                all_bits = np.concatenate([bits_y, bits_cr])
        else:
            all_bits = bits_y

    # Convert bits to byte stream
    payload_bytes = bytearray()
    for i in range(total_payload_bytes):
        val = 0
        for s in range(8):
            bit_idx = i * 8 + s
            if bit_idx < len(all_bits):
                val = (val << 1) | int(all_bits[bit_idx])
        payload_bytes.append(val)

    return bytes(payload_bytes)


def extract_and_reconstruct(watermarked_bgr: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Blindly extract and losslessly reconstruct the embedded watermark image.
    Does not require the original watermark.

    Returns:
        reconstructed_image: 2D (Grayscale) or 3D (RGB) uint8 image with original dimensions.
        metadata: Dictionary with extracted dimensions, format, compression ratio, etc.
    """
    payload_bytes = extract_framed_payload(watermarked_bgr)
    reconstructed_wm, meta = deserialize_watermark(payload_bytes)
    return reconstructed_wm, meta


def extract_watermark(
    y_channel: np.ndarray,
    num_bits: int,
    coeff_a: Tuple[int, int] = COEFF_A,
    coeff_b: Tuple[int, int] = COEFF_B,
    block_size: int = BLOCK_SIZE,
) -> np.ndarray:
    """Legacy helper for backward compatibility."""
    return extract_bits_from_channel(y_channel, num_bits=num_bits, start_block=0)
