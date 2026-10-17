"""Minecraft Anvil (.mca) region and chunk parser."""

from __future__ import annotations

try:
    from isal import igzip as gzip_backend
    from isal import isal_zlib as zlib_backend
except ImportError:
    import gzip as gzip_backend
    import zlib as zlib_backend

import io
import mmap
import struct
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from mc2cr.nbt import DEFAULT_SKIP_KEYS, read_nbt

SECTOR_BYTES = 4096
CHUNK_HEADER_SIZE = 5  # 4 bytes length, 1 byte compression type
CHUNKS_PER_REGION_SIDE = 32
CHUNKS_PER_REGION = CHUNKS_PER_REGION_SIDE * CHUNKS_PER_REGION_SIDE


class AnvilSection:
    """Represents a single 16x16x16 sub-chunk section in an Anvil chunk."""

    def __init__(
        self,
        y: int,
        blocks: bytes,
        data: bytes,
        sky_light: Optional[bytes] = None,
        block_light: Optional[bytes] = None,
        add: Optional[bytes] = None,
    ):
        self.y = y
        self.blocks = blocks
        self.data = data
        self.sky_light = sky_light
        self.block_light = block_light
        self.add = add


class AnvilChunk:
    """Represents an Anvil chunk consisting of multiple 16x16x16 sub-chunk sections."""

    def __init__(
        self,
        x_pos: int,
        z_pos: int,
        sections: Dict[int, AnvilSection],
        tile_entities: Optional[List[Dict[str, Any]]] = None,
    ):
        self.x_pos = x_pos
        self.z_pos = z_pos
        self.sections = sections
        self.tile_entities = tile_entities or []


class AnvilRegionFile:
    """Reads and parses an Anvil .mca region file containing up to 32x32 chunks."""

    def __init__(self, region_path: str | Path):
        self.path = Path(region_path)
        if not self.path.exists():
            raise FileNotFoundError(f"Anvil region file not found: {self.path}")
        self._offsets: List[int] = []
        self._sector_counts: List[int] = []
        self._read_header()

    def _read_header(self) -> None:
        with open(self.path, "rb") as f:
            location_table = f.read(SECTOR_BYTES)

        for i in range(CHUNKS_PER_REGION):
            entry = location_table[i * 4 : (i + 1) * 4]
            offset = struct.unpack(">I", b"\x00" + entry[:3])[0]
            sector_count = entry[3]
            self._offsets.append(offset)
            self._sector_counts.append(sector_count)

    def read_chunk_data(self, chunk_x: int, chunk_z: int) -> Optional[bytes]:
        """Read and decompress raw NBT bytes for chunk at local coordinates (0..31, 0..31)."""
        idx = (chunk_z % CHUNKS_PER_REGION_SIDE) * CHUNKS_PER_REGION_SIDE + (chunk_x % CHUNKS_PER_REGION_SIDE)
        offset = self._offsets[idx]
        if offset == 0:
            return None

        with open(self.path, "rb") as f:
            f.seek(offset * SECTOR_BYTES)
            length_bytes = f.read(4)
            if len(length_bytes) < 4:
                return None
            length = struct.unpack(">I", length_bytes)[0]
            if length == 0:
                return None
            comp_type = f.read(1)[0]
            payload = f.read(length - 1)

        if comp_type == 2:  # zlib
            return zlib_backend.decompress(payload)
        elif comp_type == 1:  # gzip
            return gzip_backend.decompress(payload)
        else:
            raise ValueError(f"Unsupported compression type: {comp_type}")

    def iter_chunks(self) -> Iterator[AnvilChunk]:
        """Iterate over all existing chunks within this .mca region file using memory mapping."""
        if not self.path.exists() or self.path.stat().st_size < SECTOR_BYTES:
            return

        with open(self.path, "rb") as f:
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                for cz in range(CHUNKS_PER_REGION_SIDE):
                    for cx in range(CHUNKS_PER_REGION_SIDE):
                        idx = cz * CHUNKS_PER_REGION_SIDE + cx
                        offset = self._offsets[idx]
                        if offset == 0:
                            continue

                        pos = offset * SECTOR_BYTES
                        if pos + 5 > len(mm):
                            continue
                        length = struct.unpack_from(">I", mm, pos)[0]
                        if length <= 1 or pos + 4 + length > len(mm):
                            continue
                        comp_type = mm[pos + 4]
                        payload = mm[pos + 5 : pos + 4 + length]

                        if comp_type == 2:  # zlib
                            raw_nbt = zlib_backend.decompress(payload)
                        elif comp_type == 1:  # gzip
                            raw_nbt = gzip_backend.decompress(payload)
                        else:
                            continue

                        _, root = read_nbt(raw_nbt, skip_keys=DEFAULT_SKIP_KEYS)
                        level = root.get("Level", root.get("Data", {}).get("Level", root))

                        x_pos = level.get("xPos", cx)
                        z_pos = level.get("zPos", cz)
                        raw_sections = level.get("Sections", [])
                        tile_entities = level.get("TileEntities", [])

                        sections: Dict[int, AnvilSection] = {}
                        for s in raw_sections:
                            y_idx = int(s.get("Y", 0))
                            blocks = s.get("Blocks", b"")
                            data = s.get("Data", b"")
                            sky_light = s.get("SkyLight", b"")
                            block_light = s.get("BlockLight", b"")
                            add = s.get("Add")

                            sections[y_idx] = AnvilSection(
                                y=y_idx,
                                blocks=blocks,
                                data=data,
                                sky_light=sky_light,
                                block_light=block_light,
                                add=add,
                            )

                        yield AnvilChunk(x_pos=x_pos, z_pos=z_pos, sections=sections, tile_entities=tile_entities)
