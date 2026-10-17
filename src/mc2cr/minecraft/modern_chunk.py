"""Modern Minecraft (1.13+ Palette / Bit-Packed) region and chunk parser."""

from __future__ import annotations

try:
    from isal import igzip as gzip_backend
    from isal import isal_zlib as zlib_backend
except ImportError:
    import gzip as gzip_backend
    import zlib as zlib_backend

import mmap
import struct
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

import numpy as np

from mc2cr.minecraft.modern_blocks import ModernBlockMapper
from mc2cr.nbt import DEFAULT_SKIP_KEYS, read_nbt

SECTOR_BYTES = 4096
CHUNKS_PER_REGION_SIDE = 32
CHUNKS_PER_REGION = CHUNKS_PER_REGION_SIDE * CHUNKS_PER_REGION_SIDE


class ModernSection:
    """Represents an unpacked 16x16x16 modern sub-chunk section."""

    def __init__(self, y: int, block_keys: List[str], skylight: Optional[List[int]] = None):
        self.y = y
        self.block_keys = block_keys  # CR block save keys in (y, x, z) order
        self.skylight = skylight or [15] * 4096


class ModernChunk:
    """Represents a modern chunk with palette-unpacked sections."""

    def __init__(
        self,
        x_pos: int,
        z_pos: int,
        sections: Dict[int, ModernSection],
        tile_entities: Optional[List[Dict[str, Any]]] = None,
    ):
        self.x_pos = x_pos
        self.z_pos = z_pos
        self.sections = sections
        self.tile_entities = tile_entities or []


def unpack_modern_palette_indices(
    palette: List[Any],
    data_arr: Optional[List[int]],
    data_version: int = 4903,
) -> np.ndarray:
    """Unpack 4,096 block palette indices from modern bit-packed long arrays using NumPy broadcasting."""
    palette_len = len(palette)
    if palette_len <= 1 or not data_arr:
        return np.zeros(4096, dtype=np.int32)

    bits_per_block = max(4, (palette_len - 1).bit_length())

    # In 1.16+ (DataVersion >= 2529), indices do not span across 64-bit boundaries
    if data_version >= 2529:
        blocks_per_long = 64 // bits_per_block
        mask = np.uint64((1 << bits_per_block) - 1)
        arr = np.array(data_arr, dtype=np.int64).view(np.uint64)
        shifts = np.arange(blocks_per_long, dtype=np.uint64) * np.uint64(bits_per_block)
        matrix = (arr[:, None] >> shifts[None, :]) & mask
        flattened = matrix.ravel()
        if len(flattened) >= 4096:
            return flattened[:4096].astype(np.int32)
        else:
            padded = np.zeros(4096, dtype=np.int32)
            padded[: len(flattened)] = flattened
            return padded
    else:
        # Pre-1.16: Indices span across 64-bit longs
        mask = (1 << bits_per_block) - 1
        indices = np.empty(4096, dtype=np.int32)
        for i in range(4096):
            bit_start = i * bits_per_block
            long_start = bit_start // 64
            bit_offset = bit_start % 64
            long_end = (bit_start + bits_per_block - 1) // 64

            val0 = data_arr[long_start] & 0xFFFFFFFFFFFFFFFF
            if long_start == long_end:
                idx = (val0 >> bit_offset) & mask
            else:
                val1 = data_arr[long_end] & 0xFFFFFFFFFFFFFFFF
                bits_from_first = 64 - bit_offset
                low = val0 >> bit_offset
                high = (val1 & ((1 << (bits_per_block - bits_from_first)) - 1)) << bits_from_first
                idx = low | high
            indices[i] = idx
        return indices


class ModernRegionFile:
    """Reads modern palette-based .mca files."""

    def __init__(self, region_path: str | Path):
        self.path = Path(region_path)
        if not self.path.exists():
            raise FileNotFoundError(f"Modern region file not found: {self.path}")
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

    def iter_chunks(self, mapper: ModernBlockMapper) -> Iterator[ModernChunk]:
        """Iterate over and decode all modern chunks in this region file using memory mapping."""
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
                        data_version = int(root.get("DataVersion", 4903))
                        x_pos = int(root.get("xPos", cx))
                        z_pos = int(root.get("zPos", cz))
                        raw_sections = root.get("sections", root.get("Level", {}).get("Sections", []))
                        raw_tile_entities = root.get("block_entities", root.get("Level", {}).get("TileEntities", []))

                        sections: Dict[int, ModernSection] = {}
                        for s in raw_sections:
                            y_idx = int(s.get("Y", 0))
                            bs = s.get("block_states")

                            # If block_states is not present, check legacy Blocks
                            if not bs or not isinstance(bs, dict):
                                continue

                            palette = bs.get("palette", [])
                            data_arr = bs.get("data")

                            if not palette:
                                continue

                            # Pre-map palette entries to CR save keys
                            mapped_palette = [mapper.get_block_save_key(p_entry) for p_entry in palette]

                            # Fast-path: Single block palette (e.g. all air)
                            if len(palette) == 1:
                                all_key = mapped_palette[0]
                                block_keys = [all_key] * 4096
                            else:
                                indices = unpack_modern_palette_indices(palette, data_arr, data_version)
                                palette_arr = np.array(mapped_palette, dtype=object)
                                clipped_indices = np.clip(indices, 0, len(mapped_palette) - 1)
                                raw_keys = palette_arr[clipped_indices]
                                block_keys = raw_keys.reshape((16, 16, 16)).transpose((0, 2, 1)).ravel().tolist()

                            # Extract and unpack SkyLight if available
                            raw_sky = s.get("SkyLight")
                            if raw_sky and len(raw_sky) >= 2048:
                                sky_arr = np.frombuffer(raw_sky, dtype=np.uint8)
                                unpacked_sky = np.empty(4096, dtype=np.uint8)
                                unpacked_sky[0::2] = sky_arr & 0x0F
                                unpacked_sky[1::2] = (sky_arr >> 4) & 0x0F
                                cr_sky = unpacked_sky.reshape((16, 16, 16)).transpose((0, 2, 1)).ravel().tolist()
                            else:
                                if all(k == "base:air[default]" for k in block_keys) and y_idx >= 4:
                                    cr_sky = [15] * 4096
                                else:
                                    cr_sky = [0] * 4096

                            sections[y_idx] = ModernSection(y=y_idx, block_keys=block_keys, skylight=cr_sky)

                        yield ModernChunk(x_pos=x_pos, z_pos=z_pos, sections=sections, tile_entities=raw_tile_entities)
