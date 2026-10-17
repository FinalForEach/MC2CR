"""World conversion pipeline from Minecraft Beta 1.7.3 to Cosmic Reach."""

from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

import numpy as np

from mc2cr.cosmicreach.block_data import ChunkBlockData, serialize_from_palette_ids
from mc2cr.cosmicreach.constants import CHUNK_WIDTH, NUM_BLOCKS_IN_CHUNK, REGION_WIDTH
from mc2cr.cosmicreach.region_writer import (
    AIR_BLOCK_DATA_BYTES,
    SKY_0_BYTES,
    SKY_15_BYTES,
    CRChunk,
    CRRegion,
    serialize_chunk_from_data,
)
from mc2cr.cosmicreach.skylight_data import ChunkSkyLightData
from mc2cr.cosmicreach.world_writer import DIMENSION_CONFIG, DIMENSION_MAP_STR, write_world_structure
from mc2cr.minecraft.anvil import AnvilRegionFile
from mc2cr.minecraft.blocks import LegacyBlockMapper, get_block_save_key
from mc2cr.minecraft.mcregion import McRegionFile
from mc2cr.minecraft.modern_blocks import ModernBlockMapper
from mc2cr.minecraft.modern_chunk import ModernRegionFile
from mc2cr.minecraft.tile_entities import build_chunk_block_entities_binary
from mc2cr.nbt import read_nbt


def read_level_dat(level_dat_path: str | Path) -> Dict:
    """Read level.dat metadata if present."""
    path = Path(level_dat_path)
    if not path.exists():
        return {}
    with open(path, "rb") as f:
        _, nbt_data = read_nbt(f.read())
        return nbt_data.get("Data", nbt_data)


def detect_mc_version(level_data: Dict, mc_world_dir: Path, is_anvil: bool) -> str:
    """Detect Minecraft version string from level.dat or region format."""
    ver_tag = level_data.get("Version")
    if isinstance(ver_tag, dict) and ver_tag.get("Name"):
        v_name = ver_tag["Name"]
        return f"Minecraft {v_name}"

    names = [str(level_data.get("LevelName", "")), mc_world_dir.name]
    for n in names:
        normalized = n.replace("_", ".")
        m = re.search(r"\b(?:(b(?:eta)?|r(?:elease)?)[\s._-]*)?(\d+\.\d+(?:\.\d+)?)\b", normalized, re.IGNORECASE)
        if m:
            prefix_match = (m.group(1) or "").lower()
            ver_num = m.group(2)
            is_beta = "b" in prefix_match
            is_release = "r" in prefix_match
            if is_beta or (ver_num.startswith("1.") and len(ver_num) > 3 and int(ver_num.split(".")[1]) >= 3 and not is_anvil and ver_num != "1.0"):
                return f"Minecraft Beta {ver_num}"
            elif is_release or ver_num in ["1.0", "1.1"] or is_anvil:
                return f"Minecraft Release {ver_num}"
            return f"Minecraft {ver_num}"

    version_id = level_data.get("version")
    if version_id == 19133 or is_anvil:
        return "Minecraft 1.2+ (Anvil)"
    elif version_id == 19132:
        return "Minecraft Beta 1.3 - 1.1 (McRegion)"
    return "Minecraft"


from concurrent.futures import ProcessPoolExecutor, as_completed


def _convert_single_region_worker(
    region_path: Path,
    regions_dir: Path,
    fmt: str,
    is_modern: bool,
    chunk_y_offset: int,
    y_offset: int,
    mapping_override: Optional[Dict],
) -> Tuple[int, int, int]:
    """Process a single .mca / .mcr file and write CR region files directly to disk."""
    mc_chunks_count = 0
    cr_chunks_count = 0
    cr_regions: Dict[Tuple[int, int, int], CRRegion] = {}

    if is_modern and fmt == "anvil":
        modern_mapper = ModernBlockMapper(override_path_or_dict=mapping_override)
        mca_modern = ModernRegionFile(region_path)
        for mc_chunk in mca_modern.iter_chunks(modern_mapper):
            mc_chunks_count += 1
            for y_idx, sec in mc_chunk.sections.items():
                cr_cy = y_idx + chunk_y_offset

                if all(k == "base:air[default]" for k in sec.block_keys):
                    block_data_bytes = AIR_BLOCK_DATA_BYTES
                else:
                    block_data_bytes = ChunkBlockData(sec.block_keys).serialize()

                if len(set(sec.skylight)) == 1:
                    sky_bytes = SKY_15_BYTES if sec.skylight[0] == 15 else (SKY_0_BYTES if sec.skylight[0] == 0 else ChunkSkyLightData(sec.skylight).serialize())
                else:
                    sky_bytes = ChunkSkyLightData(sec.skylight).serialize()

                chunk_raw = serialize_chunk_from_data(
                    mc_chunk.x_pos,
                    cr_cy,
                    mc_chunk.z_pos,
                    block_data_bytes,
                    sky_bytes,
                    block_entities_binary=None,
                )
                cr_chunks_count += 1

                rx = mc_chunk.x_pos // REGION_WIDTH
                ry = cr_cy // REGION_WIDTH
                rz = mc_chunk.z_pos // REGION_WIDTH
                region_key = (rx, ry, rz)

                if region_key not in cr_regions:
                    cr_regions[region_key] = CRRegion(rx, ry, rz)
                cr_regions[region_key].add_raw_chunk(mc_chunk.x_pos, cr_cy, mc_chunk.z_pos, chunk_raw)

    elif fmt == "anvil":
        mca = AnvilRegionFile(region_path)
        legacy_mapper = LegacyBlockMapper(override_path_or_dict=mapping_override)
        lookup_arr = legacy_mapper._lookup_arr
        for mc_chunk in mca.iter_chunks():
            mc_chunks_count += 1
            for y_idx, sec in mc_chunk.sections.items():
                cr_cy = y_idx + chunk_y_offset

                blocks_arr = np.frombuffer(sec.blocks, dtype=np.uint8).reshape((16, 16, 16))
                cr_blocks = blocks_arr.transpose((0, 2, 1)).ravel()

                if sec.add and len(sec.add) >= 2048:
                    add_arr = np.frombuffer(sec.add, dtype=np.uint8)
                    unpacked_add = np.empty(4096, dtype=np.uint8)
                    unpacked_add[0::2] = add_arr & 0x0F
                    unpacked_add[1::2] = (add_arr >> 4) & 0x0F
                    cr_add = unpacked_add.reshape((16, 16, 16)).transpose((0, 2, 1)).ravel()
                    b_ids = cr_blocks.astype(np.int32) | (cr_add.astype(np.int32) << 8)
                else:
                    b_ids = cr_blocks.astype(np.int32)

                data_arr = np.frombuffer(sec.data, dtype=np.uint8)
                unpacked_data = np.empty(4096, dtype=np.uint8)
                unpacked_data[0::2] = data_arr & 0x0F
                unpacked_data[1::2] = (data_arr >> 4) & 0x0F
                cr_data = unpacked_data.reshape((16, 16, 16)).transpose((0, 2, 1)).ravel()

                if sec.sky_light and len(sec.sky_light) >= 2048:
                    sky_arr = np.frombuffer(sec.sky_light, dtype=np.uint8)
                    unpacked_sky = np.empty(4096, dtype=np.uint8)
                    unpacked_sky[0::2] = sky_arr & 0x0F
                    unpacked_sky[1::2] = (sky_arr >> 4) & 0x0F
                    cr_sky = unpacked_sky.reshape((16, 16, 16)).transpose((0, 2, 1)).ravel()
                else:
                    cr_sky = np.full(4096, 15, dtype=np.uint8)

                if not np.any(b_ids):
                    block_data_bytes = AIR_BLOCK_DATA_BYTES
                else:
                    indices = (b_ids << 4) | cr_data.astype(np.int32)
                    unique_indices, inverse_pids = np.unique(indices, return_inverse=True)
                    unique_keys = lookup_arr[unique_indices].tolist()
                    palette_dict = dict.fromkeys(unique_keys)
                    if len(palette_dict) == 1:
                        block_data_bytes = serialize_from_palette_ids(unique_keys[:1], inverse_pids)
                    else:
                        palette = list(palette_dict.keys())
                        palette_map = {b: i for i, b in enumerate(palette)}
                        remapper = np.array([palette_map[k] for k in unique_keys], dtype=np.uint16)
                        pids_all = remapper[inverse_pids]
                        block_data_bytes = serialize_from_palette_ids(palette, pids_all)

                if np.all(cr_sky == 15):
                    sky_bytes = SKY_15_BYTES
                elif np.all(cr_sky == 0):
                    sky_bytes = SKY_0_BYTES
                else:
                    sky_bytes = ChunkSkyLightData(cr_sky.tolist()).serialize()

                chunk_tes = [
                    te for te in mc_chunk.tile_entities
                    if (int(te.get("y", 0)) // CHUNK_WIDTH) == y_idx
                ]
                be_binary = (
                    build_chunk_block_entities_binary(chunk_tes, legacy_mapper, y_offset=y_offset)
                    if chunk_tes
                    else None
                )

                chunk_raw = serialize_chunk_from_data(
                    mc_chunk.x_pos,
                    cr_cy,
                    mc_chunk.z_pos,
                    block_data_bytes,
                    sky_bytes,
                    be_binary,
                )
                cr_chunks_count += 1

                rx = mc_chunk.x_pos // REGION_WIDTH
                ry = cr_cy // REGION_WIDTH
                rz = mc_chunk.z_pos // REGION_WIDTH
                region_key = (rx, ry, rz)

                if region_key not in cr_regions:
                    cr_regions[region_key] = CRRegion(rx, ry, rz)
                cr_regions[region_key].add_raw_chunk(mc_chunk.x_pos, cr_cy, mc_chunk.z_pos, chunk_raw)

    else:
        # McRegion format (.mcr)
        mcr = McRegionFile(region_path)
        legacy_mapper = LegacyBlockMapper(override_path_or_dict=mapping_override)
        lookup_arr = legacy_mapper._lookup_arr
        for mc_chunk in mcr.iter_chunks():
            mc_chunks_count += 1

            blocks_raw = mc_chunk.blocks
            if len(blocks_raw) < 32768:
                blocks_raw = (blocks_raw or b"").ljust(32768, b"\x00")
            mc_blocks = np.frombuffer(blocks_raw, dtype=np.uint8).reshape((16, 16, 128))

            data_raw = mc_chunk.data or b""
            if len(data_raw) < 16384:
                data_raw = data_raw.ljust(16384, b"\x00")
            data_arr = np.frombuffer(data_raw, dtype=np.uint8)
            unpacked_data = np.empty(32768, dtype=np.uint8)
            unpacked_data[0::2] = data_arr & 0x0F
            unpacked_data[1::2] = (data_arr >> 4) & 0x0F
            mc_data = unpacked_data.reshape((16, 16, 128))

            sky_raw = mc_chunk.sky_light or b""
            if len(sky_raw) < 16384:
                sky_raw = sky_raw.ljust(16384, b"\xFF")
            sky_arr = np.frombuffer(sky_raw, dtype=np.uint8)
            unpacked_sky = np.empty(32768, dtype=np.uint8)
            unpacked_sky[0::2] = sky_arr & 0x0F
            unpacked_sky[1::2] = (sky_arr >> 4) & 0x0F
            mc_sky = unpacked_sky.reshape((16, 16, 128))

            for cy in range(8):
                y_start = cy * CHUNK_WIDTH
                y_end = y_start + CHUNK_WIDTH
                sub_blocks = mc_blocks[:, :, y_start:y_end]

                if not np.any(sub_blocks):
                    block_data_bytes = AIR_BLOCK_DATA_BYTES
                else:
                    cr_blocks = sub_blocks.transpose((2, 0, 1)).ravel()
                    cr_data = mc_data[:, :, y_start:y_end].transpose((2, 0, 1)).ravel()
                    indices = (cr_blocks.astype(np.int32) << 4) | cr_data.astype(np.int32)
                    unique_indices, inverse_pids = np.unique(indices, return_inverse=True)
                    unique_keys = lookup_arr[unique_indices].tolist()
                    palette_dict = dict.fromkeys(unique_keys)
                    if len(palette_dict) == 1:
                        block_data_bytes = serialize_from_palette_ids(unique_keys[:1], inverse_pids)
                    else:
                        palette = list(palette_dict.keys())
                        palette_map = {b: i for i, b in enumerate(palette)}
                        remapper = np.array([palette_map[k] for k in unique_keys], dtype=np.uint16)
                        pids_all = remapper[inverse_pids]
                        block_data_bytes = serialize_from_palette_ids(palette, pids_all)

                sub_sky = mc_sky[:, :, y_start:y_end].transpose((2, 0, 1)).ravel()
                if np.all(sub_sky == 15):
                    sky_bytes = SKY_15_BYTES
                elif np.all(sub_sky == 0):
                    sky_bytes = SKY_0_BYTES
                else:
                    sky_bytes = ChunkSkyLightData(sub_sky.tolist()).serialize()

                cr_cy = cy + chunk_y_offset

                chunk_tes = [
                    te for te in mc_chunk.tile_entities
                    if (int(te.get("y", 0)) // CHUNK_WIDTH) == cy
                ]
                be_binary = (
                    build_chunk_block_entities_binary(chunk_tes, legacy_mapper, y_offset=y_offset)
                    if chunk_tes
                    else None
                )

                chunk_raw = serialize_chunk_from_data(
                    mc_chunk.x_pos,
                    cr_cy,
                    mc_chunk.z_pos,
                    block_data_bytes,
                    sky_bytes,
                    be_binary,
                )
                cr_chunks_count += 1

                rx = mc_chunk.x_pos // REGION_WIDTH
                ry = cr_cy // REGION_WIDTH
                rz = mc_chunk.z_pos // REGION_WIDTH
                region_key = (rx, ry, rz)

                if region_key not in cr_regions:
                    cr_regions[region_key] = CRRegion(rx, ry, rz)
                cr_regions[region_key].add_raw_chunk(mc_chunk.x_pos, cr_cy, mc_chunk.z_pos, chunk_raw)

    saved_regions_count = len(cr_regions)
    for (rx, ry, rz), region in cr_regions.items():
        region_filename = f"region_{rx}_{ry}_{rz}.cosmicreach"
        region.write_to_file(regions_dir / region_filename, compress_level=1)

    return (mc_chunks_count, cr_chunks_count, saved_regions_count)


def convert_mc_world(
    mc_world_dir: str | Path | None = None,
    cr_world_dir: str | Path | None = None,
    mapping_override: Optional[str | Path | Dict] = None,
    progress_callback: Optional[Callable[[str, int, int, str], None]] = None,
    y_offset: int = -64,
    max_workers: Optional[int] = None,
    **kwargs,
) -> Dict:
    """Convert any Minecraft McRegion (.mcr), Legacy Anvil, or Modern Anvil (1.13+) world into Cosmic Reach."""
    mc_in = mc_world_dir or kwargs.get("input_world")
    cr_out = cr_world_dir or kwargs.get("output_world")
    if not mc_in or not cr_out:
        raise ValueError("Both source Minecraft world and destination Cosmic Reach world paths are required.")

    mc_path = Path(mc_in)
    cr_path = Path(cr_out)

    if not mc_path.exists():
        raise FileNotFoundError(f"Source Minecraft world not found: {mc_path}")

    start_time = time.time()

    # 1. Read level.dat
    level_data = read_level_dat(mc_path / "level.dat")
    data_version = int(level_data.get("DataVersion", 0))
    is_modern = data_version >= 1451

    world_name = level_data.get("LevelName", mc_path.name)
    world_seed = level_data.get("RandomSeed", 0)

    # Spawn coordinates
    spawn_coords_tag = level_data.get("spawn")
    if isinstance(spawn_coords_tag, dict):
        spawn_x = float(spawn_coords_tag.get("x", 0))
        spawn_y = float(spawn_coords_tag.get("y", 64))
        spawn_z = float(spawn_coords_tag.get("z", 0))
    else:
        spawn_x = float(level_data.get("SpawnX", 0))
        spawn_y = float(level_data.get("SpawnY", 64))
        spawn_z = float(level_data.get("SpawnZ", 0))

    spawn_y += float(y_offset)

    # Player position & rotation
    player_data = level_data.get("Player", {})
    player_pos_tag = player_data.get("Pos", [])
    if len(player_pos_tag) >= 3:
        px, py, pz = [float(c) for c in player_pos_tag[:3]]
        player_pos = (px, py + float(y_offset), pz)
    else:
        player_pos = (spawn_x, spawn_y, spawn_z)

    player_rot_tag = player_data.get("Rotation", [0.0, 0.0])
    player_rot = (float(player_rot_tag[0]), float(player_rot_tag[1])) if len(player_rot_tag) >= 2 else (0.0, 0.0)

    player_dim = int(player_data.get("Dimension", 0))
    player_zone_id = DIMENSION_CONFIG.get(player_dim, DIMENSION_CONFIG[0])["zone_id"]

    game_type = level_data.get("GameType", 0)
    gamemode_str = "creative" if game_type == 1 else "survival"

    # 2. Detect dimensions
    detected_dims = []
    for dim_id, conf in DIMENSION_CONFIG.items():
        candidate_dirs = [mc_path / conf["mc_dir"]]
        for alt in conf.get("alt_mc_dirs", []):
            candidate_dirs.append(mc_path / alt)

        found_dir = None
        for c_dir in candidate_dirs:
            if c_dir.exists():
                found_dir = c_dir
                break

        if found_dir:
            mca_files = sorted(list(found_dir.glob("*.mca")))
            mcr_files = sorted(list(found_dir.glob("*.mcr")))
            files = mca_files if mca_files else mcr_files
            fmt = "anvil" if mca_files else "mcregion"
            if files or dim_id == 0:
                detected_dims.append((dim_id, conf, found_dir, files, fmt))

    if not detected_dims:
        detected_dims.append((0, DIMENSION_CONFIG[0], mc_path / "region", [], "mcregion"))

    # 3. Initialize CR World structure
    active_zone_ids = [conf["zone_id"] for _, conf, _, _, _ in detected_dims]
    has_anvil = any(fmt == "anvil" for _, _, _, _, fmt in detected_dims)
    mc_version_str = detect_mc_version(level_data, mc_path, has_anvil)
    world_desc = f"Converted from {mc_version_str} by MC2CR"

    min_y = -64.0 if data_version >= 2844 else 0.0
    respawn_h = min_y + float(y_offset)

    write_world_structure(
        output_dir=cr_path,
        world_name=world_name,
        world_seed=world_seed,
        spawn_coords=(spawn_x, spawn_y, spawn_z),
        default_zone_id="base:earth",
        active_zone_ids=active_zone_ids,
        player_zone_id=player_zone_id,
        player_pos=player_pos,
        player_rotation=player_rot,
        gamemode=gamemode_str,
        description=world_desc,
        respawn_height=respawn_h,
    )

    total_region_files = sum(len(file_list) for _, _, _, file_list, _ in detected_dims)
    total_mc_chunks = 0
    total_cr_chunks = 0
    total_cr_regions = 0
    chunk_y_offset = y_offset // CHUNK_WIDTH
    processed_count = 0

    # Clean dict mapping override if string path
    cleaned_mapping = None
    if isinstance(mapping_override, dict):
        cleaned_mapping = mapping_override
    elif mapping_override:
        import json
        with open(mapping_override, "r") as f:
            cleaned_mapping = json.load(f)

    # 4. Process each dimension
    tasks = []
    for dim_id, conf, dim_region_dir, region_files, fmt in detected_dims:
        if not region_files:
            continue
        zone_id = conf["zone_id"]
        regions_dir = cr_path / "zones" / zone_id.replace(":", "/") / "regions"
        regions_dir.mkdir(parents=True, exist_ok=True)
        for r_file in region_files:
            tasks.append((r_file, regions_dir, fmt, is_modern, chunk_y_offset, y_offset, cleaned_mapping, conf["name"]))

    if max_workers == 1 or len(tasks) <= 1:
        for r_file, r_dir, fmt, is_mod, cy_off, y_off, map_ov, conf_name in tasks:
            mc_c, cr_c, cr_r = _convert_single_region_worker(r_file, r_dir, fmt, is_mod, cy_off, y_off, map_ov)
            total_mc_chunks += mc_c
            total_cr_chunks += cr_c
            total_cr_regions += cr_r
            processed_count += 1
            if progress_callback:
                progress_callback(f"{conf_name}: {r_file.name}", processed_count, total_region_files, "convert")
    else:
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            future_to_task = {
                executor.submit(
                    _convert_single_region_worker,
                    t[0], t[1], t[2], t[3], t[4], t[5], t[6]
                ): (t[0], t[7])
                for t in tasks
            }
            for future in as_completed(future_to_task):
                r_file, conf_name = future_to_task[future]
                mc_c, cr_c, cr_r = future.result()
                total_mc_chunks += mc_c
                total_cr_chunks += cr_c
                total_cr_regions += cr_r
                processed_count += 1
                if progress_callback:
                    progress_callback(f"{conf_name}: {r_file.name}", processed_count, total_region_files, "convert")

    elapsed = time.time() - start_time
    return {
        "world_name": world_name,
        "mcr_files_processed": total_region_files,
        "mc_chunks_converted": total_mc_chunks,
        "cr_chunks_generated": total_cr_chunks,
        "cr_regions_saved": total_cr_regions,
        "elapsed_seconds": elapsed,
    }


convert_b173_world = convert_mc_world
