"""Cosmic Reach region binary serializer (.cosmicreach file format)."""

from __future__ import annotations

try:
    from isal import igzip as gzip_backend
except ImportError:
    import gzip as gzip_backend

import struct
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from mc2cr.cosmicreach.block_data import ChunkBlockData
from mc2cr.cosmicreach.constants import (
    BLOCKENTITY_DATA,
    BLOCKENTITY_NULL,
    BLOCKLIGHTDATA_NEEDS_CALCULATION,
    BLOCKLIGHTDATA_NULL,
    COMPRESSION_TYPE_GZIP,
    FILE_VERSION,
    MAGIC,
    NUMBER_TYPE_INT,
    NUMBER_TYPE_SHORT,
    NUM_BLOCKS_IN_CHUNK,
    NUM_COLUMNS_IN_REGION,
    REGION_WIDTH,
    SKYLIGHTDATA_NULL,
)
from mc2cr.cosmicreach.skylight_data import ChunkSkyLightData


class CRChunk:
    """Represents a 16x16x16 Cosmic Reach chunk."""

    def __init__(
        self,
        chunk_x: int,
        chunk_y: int,
        chunk_z: int,
        block_data: ChunkBlockData,
        skylight_data: Optional[ChunkSkyLightData] = None,
        needs_blocklight_calculation: bool = True,
        block_entities_binary: Optional[bytes] = None,
    ):
        self.chunk_x = chunk_x
        self.chunk_y = chunk_y
        self.chunk_z = chunk_z
        self.block_data = block_data
        self.skylight_data = skylight_data
        self.needs_blocklight_calculation = needs_blocklight_calculation
        self.block_entities_binary = block_entities_binary

    def serialize(self) -> bytes:
        """Serialize individual chunk binary stream."""
        buf = bytearray()
        buf.extend(struct.pack(">iii", self.chunk_x, self.chunk_y, self.chunk_z))
        buf.extend(self.block_data.serialize())
        if self.skylight_data:
            buf.extend(self.skylight_data.serialize())
        else:
            buf.append(SKYLIGHTDATA_NULL)
        if self.needs_blocklight_calculation:
            buf.append(BLOCKLIGHTDATA_NEEDS_CALCULATION)
        else:
            buf.append(BLOCKLIGHTDATA_NULL)
        if self.block_entities_binary:
            buf.append(BLOCKENTITY_DATA)
            buf.extend(struct.pack(">i", len(self.block_entities_binary)))
            buf.extend(self.block_entities_binary)
        else:
            buf.append(BLOCKENTITY_NULL)
        return bytes(buf)


AIR_BLOCK_DATA_BYTES = ChunkBlockData(["base:air[default]"] * NUM_BLOCKS_IN_CHUNK).serialize()
SKY_15_BYTES = ChunkSkyLightData([15] * NUM_BLOCKS_IN_CHUNK).serialize()
SKY_0_BYTES = ChunkSkyLightData([0] * NUM_BLOCKS_IN_CHUNK).serialize()


def serialize_chunk_from_data(
    chunk_x: int,
    chunk_y: int,
    chunk_z: int,
    block_data_bytes: bytes,
    skylight_data_bytes: bytes,
    block_entities_binary: Optional[bytes] = None,
) -> bytes:
    """Serialize a chunk directly from block, skylight, and block-entity binary payloads."""
    buf = bytearray()
    buf.extend(struct.pack(">iii", chunk_x, chunk_y, chunk_z))
    buf.extend(block_data_bytes)
    buf.extend(skylight_data_bytes)
    buf.append(BLOCKLIGHTDATA_NEEDS_CALCULATION)
    if block_entities_binary:
        buf.append(BLOCKENTITY_DATA)
        buf.extend(struct.pack(">i", len(block_entities_binary)))
        buf.extend(block_entities_binary)
    else:
        buf.append(BLOCKENTITY_NULL)
    return bytes(buf)


class CRRegion:
    """Represents a 16x16x16 chunk region (region_rx_ry_rz.cosmicreach)."""

    def __init__(self, rx: int, ry: int, rz: int):
        self.rx = rx
        self.ry = ry
        self.rz = rz
        # Map: (cx_local, cz_local) -> list of CRChunk or (chunk_y, raw_chunk_bytes)
        self.columns: Dict[Tuple[int, int], List[Any]] = {}

    def add_chunk(self, chunk: CRChunk) -> None:
        cx_local = chunk.chunk_x - self.rx * REGION_WIDTH
        cz_local = chunk.chunk_z - self.rz * REGION_WIDTH
        col_key = (cx_local, cz_local)
        if col_key not in self.columns:
            self.columns[col_key] = []
        self.columns[col_key].append(chunk)

    def add_raw_chunk(self, chunk_x: int, chunk_y: int, chunk_z: int, raw_bytes: bytes) -> None:
        cx_local = chunk_x - self.rx * REGION_WIDTH
        cz_local = chunk_z - self.rz * REGION_WIDTH
        col_key = (cx_local, cz_local)
        if col_key not in self.columns:
            self.columns[col_key] = []
        self.columns[col_key].append((chunk_y, raw_bytes))

    def serialize(self, compress_level: int = 1) -> bytes:
        """Serialize entire region into compressed .cosmicreach bytes."""
        # 1. Build bytesOfAllChunks and record column offsets
        bytes_of_all_chunks = bytearray()
        chunk_byte_offsets = [-1] * NUM_COLUMNS_IN_REGION

        for cx_local in range(REGION_WIDTH):
            for cz_local in range(REGION_WIDTH):
                col_key = (cx_local, cz_local)
                if col_key not in self.columns or not self.columns[col_key]:
                    continue

                col_idx = cx_local * REGION_WIDTH + cz_local
                chunks = sorted(self.columns[col_key], key=lambda c: c[0] if isinstance(c, tuple) else c.chunk_y)

                col_start_offset = len(bytes_of_all_chunks)
                chunk_byte_offsets[col_idx] = col_start_offset

                # Column data payload:
                # [int byteSize] [int fileVersion] [byte numChunks] [chunk bytes...]
                col_payload = bytearray()
                col_payload.extend(struct.pack(">i", FILE_VERSION))
                col_payload.append(len(chunks) & 0xFF)
                for item in chunks:
                    if isinstance(item, tuple):
                        col_payload.extend(item[1])
                    else:
                        col_payload.extend(item.serialize())

                total_col_size = 4 + len(col_payload)
                bytes_of_all_chunks.extend(struct.pack(">i", total_col_size))
                bytes_of_all_chunks.extend(col_payload)

        # 2. Build uncompressed region buffer
        uncompressed = bytearray()
        num_columns_written = sum(1 for off in chunk_byte_offsets if off != -1)
        uncompressed.extend(struct.pack(">i", num_columns_written))

        max_offset = max([off for off in chunk_byte_offsets if off != -1], default=-1)
        use_short = max_offset < 32767

        if use_short:
            uncompressed.append(NUMBER_TYPE_SHORT)
            for off in chunk_byte_offsets:
                uncompressed.extend(struct.pack(">h", off))
        else:
            uncompressed.append(NUMBER_TYPE_INT)
            for off in chunk_byte_offsets:
                uncompressed.extend(struct.pack(">i", off))

        uncompressed.extend(bytes_of_all_chunks)

        # 3. Compress with GZIP and prepend file header
        compressed = gzip_backend.compress(bytes(uncompressed), compresslevel=compress_level)

        header = bytearray()
        header.extend(struct.pack(">I", MAGIC))
        header.extend(struct.pack(">i", FILE_VERSION))
        header.extend(struct.pack(">i", COMPRESSION_TYPE_GZIP))
        header.extend(compressed)

        return bytes(header)

    def write_to_file(self, target_path: str | Path, compress_level: int = 1) -> None:
        target = Path(target_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "wb") as f:
            f.write(self.serialize(compress_level=compress_level))
