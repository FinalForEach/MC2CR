"""Minecraft Beta 1.7.3 McRegion (.mcr) reader and chunk data extractor."""

from __future__ import annotations

try:
    from isal import igzip as gzip_backend
    from isal import isal_zlib as zlib_backend
except ImportError:
    import gzip as gzip_backend
    import zlib as zlib_backend

import mmap
import os
import struct
from pathlib import Path
from typing import Dict, Generator, Optional, Tuple

from mc2cr.nbt import DEFAULT_SKIP_KEYS, read_nbt

SECTOR_BYTES = 4096


class MCChunk:
    """Represents a loaded Beta 1.7.3 Minecraft chunk."""

    def __init__(
        self,
        x_pos: int,
        z_pos: int,
        blocks: bytes | bytearray,
        data: Optional[bytes | bytearray] = None,
        sky_light: Optional[bytes | bytearray] = None,
        tile_entities: Optional[List[Dict]] = None,
    ):
        self.x_pos = x_pos
        self.z_pos = z_pos
        self.blocks = blocks
        self.data = data
        self.sky_light = sky_light
        self.tile_entities = tile_entities or []

    def get_block_id(self, local_x: int, y: int, local_z: int) -> int:
        """Return the block ID at local coords in 16x16x128 chunk.

        MC block index: (local_x * 16 + local_z) * 128 + y.
        """
        if not (0 <= local_x < 16 and 0 <= local_z < 16 and 0 <= y < 128):
            return 0
        idx = (local_x * 16 + local_z) * 128 + y
        if idx < len(self.blocks):
            return self.blocks[idx]
        return 0

    def get_block_data(self, local_x: int, y: int, local_z: int) -> int:
        """Return the block data/metadata (0-15) at local coords in 16x16x128 chunk."""
        if not self.data or not (0 <= local_x < 16 and 0 <= local_z < 16 and 0 <= y < 128):
            return 0
        idx = (local_x * 16 + local_z) * 128 + y
        byte_idx = idx // 2
        if byte_idx < len(self.data):
            byte_val = self.data[byte_idx]
            if idx % 2 == 0:
                return byte_val & 0x0F
            else:
                return (byte_val >> 4) & 0x0F
        return 0

    def get_sky_light(self, local_x: int, y: int, local_z: int) -> int:
        """Return the sky light level (0-15) at local coords in 16x16x128 chunk."""
        if not self.sky_light or not (0 <= local_x < 16 and 0 <= local_z < 16 and 0 <= y < 128):
            return 15
        idx = (local_x * 16 + local_z) * 128 + y
        byte_idx = idx // 2
        if byte_idx < len(self.sky_light):
            byte_val = self.sky_light[byte_idx]
            if idx % 2 == 0:
                return byte_val & 0x0F
            else:
                return (byte_val >> 4) & 0x0F
        return 15


class McRegionFile:
    """Reads and parses a Minecraft .mcr region file."""

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)
        parts = self.file_path.name.split(".")
        if len(parts) >= 4 and parts[0] == "r":
            self.rx = int(parts[1])
            self.rz = int(parts[2])
        else:
            self.rx = 0
            self.rz = 0

    def iter_chunks(self) -> Generator[MCChunk, None, None]:
        """Iterate over all valid chunks present in the region file using memory mapping."""
        if not self.file_path.exists() or self.file_path.stat().st_size < SECTOR_BYTES:
            return

        with open(self.file_path, "rb") as f:
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                for cz_rel in range(32):
                    for cx_rel in range(32):
                        entry_idx = 4 * (cx_rel + cz_rel * 32)
                        entry = mm[entry_idx : entry_idx + 4]
                        sector_offset = (entry[0] << 16) | (entry[1] << 8) | entry[2]
                        if sector_offset == 0:
                            continue

                        pos = sector_offset * SECTOR_BYTES
                        if pos + 5 > len(mm):
                            continue
                        length = struct.unpack_from(">I", mm, pos)[0]
                        if length <= 1 or pos + 4 + length > len(mm):
                            continue

                        compression_type = mm[pos + 4]
                        compressed_payload = mm[pos + 5 : pos + 4 + length]

                        if compression_type == 1:
                            decompressed = gzip_backend.decompress(compressed_payload)
                        elif compression_type == 2:
                            decompressed = zlib_backend.decompress(compressed_payload)
                        else:
                            continue

                        _, nbt_data = read_nbt(decompressed, skip_keys=DEFAULT_SKIP_KEYS)
                        level = nbt_data.get("Level", {})
                        if not level:
                            continue

                        x_pos = level.get("xPos", self.rx * 32 + cx_rel)
                        z_pos = level.get("zPos", self.rz * 32 + cz_rel)
                        blocks = level.get("Blocks", b"")
                        data = level.get("Data", b"")
                        sky_light = level.get("SkyLight", b"")
                        tile_entities = level.get("TileEntities", [])

                        yield MCChunk(x_pos, z_pos, blocks, data, sky_light, tile_entities)
