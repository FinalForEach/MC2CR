"""Cosmic Reach chunk block data representations and serialization."""

from __future__ import annotations

import struct
from typing import List, Sequence

import numpy as np

from mc2cr.cosmicreach.constants import (
    BLOCK_LAYER_BIT,
    BLOCK_LAYER_BYTE,
    BLOCK_LAYER_HALFNIBBLE,
    BLOCK_LAYER_NIBBLE,
    BLOCK_LAYER_SHORT,
    BLOCK_LAYER_SINGLE_BYTE,
    BLOCK_LAYER_SINGLE_INT,
    BLOCK_LAYERED,
    BLOCK_SINGLE,
    CHUNK_WIDTH,
    NUM_BLOCKS_IN_CHUNK,
)


def write_cr_string(buffer: bytearray, s: str | None) -> None:
    """Serialize a string in Cosmic Reach format: 4-byte length + UTF-8 bytes (-1 if null)."""
    if s is None:
        buffer.extend(struct.pack(">i", -1))
        return
    encoded = s.encode("utf-8")
    buffer.extend(struct.pack(">i", len(encoded)))
    buffer.extend(encoded)


def serialize_from_palette_ids(palette: Sequence[str], pids_all: np.ndarray) -> bytes:
    """Serialize chunk block data directly from a palette list and uint16 palette ID array."""
    if len(palette) == 1:
        buf = bytearray()
        buf.append(BLOCK_SINGLE)
        write_cr_string(buf, palette[0])
        return bytes(buf)

    buf = bytearray()
    buf.append(BLOCK_LAYERED)

    # Write palette
    buf.extend(struct.pack(">i", len(palette)))
    for key in palette:
        write_cr_string(buf, key)

    # Write each layer (local_y from 0 to 15)
    for y in range(CHUNK_WIDTH):
        layer_pids = pids_all[y * 256 : (y + 1) * 256]
        first_id = int(layer_pids[0])

        # Fast single block layer check
        if (layer_pids == first_id).all():
            if first_id <= 255:
                buf.append(BLOCK_LAYER_SINGLE_BYTE)
                buf.append(first_id)
            else:
                buf.append(BLOCK_LAYER_SINGLE_INT)
                buf.extend(struct.pack(">i", first_id))
            continue

        max_id = int(layer_pids.max())
        pids_2d = layer_pids.reshape((CHUNK_WIDTH, CHUNK_WIDTH))

        # 2. Bit Layer (max ID <= 1)
        if max_id <= 1:
            buf.append(BLOCK_LAYER_BIT)
            b0 = (pids_2d[0::8, :] != 0).astype(np.uint8)
            b1 = (pids_2d[1::8, :] != 0).astype(np.uint8) << 1
            b2 = (pids_2d[2::8, :] != 0).astype(np.uint8) << 2
            b3 = (pids_2d[3::8, :] != 0).astype(np.uint8) << 3
            b4 = (pids_2d[4::8, :] != 0).astype(np.uint8) << 4
            b5 = (pids_2d[5::8, :] != 0).astype(np.uint8) << 5
            b6 = (pids_2d[6::8, :] != 0).astype(np.uint8) << 6
            b7 = (pids_2d[7::8, :] != 0).astype(np.uint8) << 7
            p = b0 | b1 | b2 | b3 | b4 | b5 | b6 | b7
            buf.extend(np.ascontiguousarray(p.T).tobytes())
            continue

        # 3. Half-Nibble Layer (max ID <= 3)
        if max_id <= 3:
            buf.append(BLOCK_LAYER_HALFNIBBLE)
            p = ((pids_2d[0::4, :] & 0x03) |
                 ((pids_2d[1::4, :] & 0x03) << 2) |
                 ((pids_2d[2::4, :] & 0x03) << 4) |
                 ((pids_2d[3::4, :] & 0x03) << 6)).astype(np.uint8)
            buf.extend(np.ascontiguousarray(p.T).tobytes())
            continue

        # 4. Nibble Layer (max ID <= 15)
        if max_id <= 15:
            buf.append(BLOCK_LAYER_NIBBLE)
            even_x = pids_2d[0::2, :] & 0x0F
            odd_x = (pids_2d[1::2, :] & 0x0F) << 4
            p = (even_x | odd_x).astype(np.uint8)
            buf.extend(np.ascontiguousarray(p.T).tobytes())
            continue

        # 5. Byte Layer (max ID <= 255)
        if max_id <= 255:
            buf.append(BLOCK_LAYER_BYTE)
            buf.extend(np.ascontiguousarray(pids_2d.T).astype(np.uint8).tobytes())
            continue

        # 6. Short Layer (max ID <= 65535)
        buf.append(BLOCK_LAYER_SHORT)
        buf.extend(layer_pids.astype(">h").tobytes())

    return bytes(buf)


class ChunkBlockData:
    """Encapsulates a 16x16x16 block grid and handles conversion to compact CR binary format."""

    def __init__(self, blocks: Sequence[str]):
        """Initialize with 4096 block save keys in Cosmic Reach format."""
        if len(blocks) != NUM_BLOCKS_IN_CHUNK:
            raise ValueError(f"Expected {NUM_BLOCKS_IN_CHUNK} blocks, got {len(blocks)}")
        self.blocks = list(blocks)

    @classmethod
    def from_3d_array(cls, array_3d: List[List[List[str]]]) -> ChunkBlockData:
        """Construct from a 16x16x16 3D array [y][x][z]."""
        flat = []
        for y in range(CHUNK_WIDTH):
            for x in range(CHUNK_WIDTH):
                for z in range(CHUNK_WIDTH):
                    flat.append(array_3d[y][x][z])
        return cls(flat)

    def get_block(self, x: int, y: int, z: int) -> str:
        return self.blocks[(y * CHUNK_WIDTH + x) * CHUNK_WIDTH + z]

    def serialize(self) -> bytes:
        """Serialize chunk block data into binary Cosmic Reach format."""
        palette_dict = dict.fromkeys(self.blocks)
        if len(palette_dict) == 1:
            buf = bytearray()
            buf.append(BLOCK_SINGLE)
            write_cr_string(buf, self.blocks[0])
            return bytes(buf)

        palette = list(palette_dict.keys())
        palette_map = {b: i for i, b in enumerate(palette)}
        pids_all = np.array([palette_map[b] for b in self.blocks], dtype=np.uint16)
        return serialize_from_palette_ids(palette, pids_all)
