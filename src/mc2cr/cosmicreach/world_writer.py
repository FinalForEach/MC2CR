"""Cosmic Reach world and zone metadata files (worldInfo.json and zoneInfo.json)."""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any, Dict, Optional

from mc2cr.cosmicreach.constants import FILE_VERSION


def calculate_view_direction(yaw: float, pitch: float) -> tuple[float, float, float]:
    """Calculate 3D view direction vector from Minecraft yaw and pitch angles in degrees."""
    rad_yaw = math.radians(yaw)
    rad_pitch = math.radians(pitch)
    vx = -math.sin(rad_yaw) * math.cos(rad_pitch)
    vy = -math.sin(rad_pitch)
    vz = math.cos(rad_yaw) * math.cos(rad_pitch)
    return (round(vx, 4), round(vy, 4), round(vz, 4))


def create_world_info(
    world_display_name: str,
    world_seed: int = 0,
    default_zone_id: str = "base:earth",
    description: str = "Converted from Minecraft by MC2CR",
    created_millis: Optional[int] = None,
    last_played_millis: Optional[int] = None,
    world_tick: int = 0,
) -> Dict[str, Any]:
    """Generate worldInfo.json dictionary."""
    now_ms = int(time.time() * 1000)
    return {
        "latestRegionFileVersion": FILE_VERSION,
        "lastSavedVersion": "0.5.19",
        "defaultZoneId": default_zone_id,
        "worldDisplayName": world_display_name,
        "worldDescription": description,
        "worldSeed": world_seed,
        "worldCreatedEpochMillis": created_millis if created_millis is not None else now_ms,
        "lastPlayedEpochMillis": last_played_millis if last_played_millis is not None else now_ms,
        "worldTick": world_tick,
    }


def create_zone_info(
    zone_id: str = "base:earth",
    world_gen_save_key: str = "base:void",
    seed: int = 0,
    spawn_x: float = 8.0,
    spawn_y: float = 65.0,
    spawn_z: float = 8.0,
    respawn_height: float = -64.0,
    sky_id: str = "base:dynamic_sky",
) -> Dict[str, Any]:
    """Generate zoneInfo.json dictionary for void world generation."""
    return {
        "lastSavedVersion": "0.5.19",
        "zoneId": zone_id,
        "worldGenSaveKey": world_gen_save_key,
        "seed": seed,
        "spawnPoint": {
            "x": spawn_x,
            "y": spawn_y,
            "z": spawn_z,
        },
        "respawnHeight": respawn_height,
        "skyId": sky_id,
        "gravity": {
            "x": 0.0,
            "y": -29.4,
            "z": 0.0,
        },
    }


def create_local_player_info(
    zone_id: str = "base:earth",
    position: tuple[float, float, float] = (8.0, 1.0, 8.0),
    rotation: tuple[float, float] = (0.0, 0.0),
    gamemode: str = "survival",
) -> Dict[str, Any]:
    """Generate localPlayer.json dictionary."""
    vx, vy, vz = calculate_view_direction(rotation[0], rotation[1])
    return {
        "zoneId": zone_id,
        "isProne": False,
        "entity": {
            "entityTypeId": "base:entity_player",
            "position": {
                "x": round(position[0], 4),
                "y": round(position[1], 4),
                "z": round(position[2], 4),
            },
            "viewDirection": {
                "x": vx,
                "y": vy,
                "z": vz,
            },
            "velocity": {
                "x": 0.0,
                "y": 0.0,
                "z": 0.0,
            },
        },
        "gamemode": gamemode,
    }


DIMENSION_CONFIG = {
    0: {
        "mc_dir": "region",
        "alt_mc_dirs": ["dimensions/minecraft/overworld/region"],
        "zone_id": "base:earth",
        "sky_id": "base:dynamic_sky",
        "name": "Earth (Overworld)",
    },
    -1: {
        "mc_dir": "DIM-1/region",
        "alt_mc_dirs": ["dimensions/minecraft/the_nether/region"],
        "zone_id": "base:lux",
        "sky_id": "base:lux_sky",
        "name": "Lux (Nether)",
    },
    1: {
        "mc_dir": "DIM1/region",
        "alt_mc_dirs": ["dimensions/minecraft/the_end/region"],
        "zone_id": "base:moon",
        "sky_id": "base:space_day",
        "name": "Moon (The End)",
    },
}

DIMENSION_MAP_STR = {
    "minecraft:overworld": 0,
    "minecraft:the_nether": -1,
    "minecraft:the_end": 1,
    "overworld": 0,
    "the_nether": -1,
    "the_end": 1,
}


def write_zone_info(
    output_dir: str | Path,
    zone_id: str = "base:earth",
    world_seed: int = 0,
    spawn_coords: tuple[float, float, float] = (8.0, 65.0, 8.0),
    respawn_height: float = -64.0,
    sky_id: Optional[str] = None,
) -> Path:
    """Generate and write zoneInfo.json for a specific zone."""
    root = Path(output_dir)
    zone_rel_path = zone_id.replace(":", "/")
    zone_dir = root / "zones" / zone_rel_path
    zone_dir.mkdir(parents=True, exist_ok=True)

    if sky_id is None:
        if zone_id == "base:lux":
            sky_id = "base:lux_sky"
        elif zone_id == "base:moon":
            sky_id = "base:space_day"
        else:
            sky_id = "base:dynamic_sky"

    zone_info = create_zone_info(
        zone_id=zone_id,
        world_gen_save_key="base:void",
        seed=world_seed,
        spawn_x=spawn_coords[0],
        spawn_y=spawn_coords[1],
        spawn_z=spawn_coords[2],
        respawn_height=respawn_height,
        sky_id=sky_id,
    )
    with open(zone_dir / "zoneInfo.json", "w", encoding="utf-8") as f:
        json.dump(zone_info, f, indent=2)

    return zone_dir


def write_world_structure(
    output_dir: str | Path,
    world_name: str,
    world_seed: int = 0,
    spawn_coords: tuple[float, float, float] = (8.0, 65.0, 8.0),
    default_zone_id: str = "base:earth",
    active_zone_ids: Optional[list[str]] = None,
    player_zone_id: Optional[str] = None,
    player_pos: Optional[tuple[float, float, float]] = None,
    player_rotation: Optional[tuple[float, float]] = None,
    gamemode: str = "survival",
    description: str = "Converted from Minecraft by MC2CR",
    respawn_height: float = -64.0,
) -> Path:
    """Write worldInfo.json, zoneInfo.json for all active zones, and localPlayer.json."""
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    world_info_path = root / "worldInfo.json"
    world_info = create_world_info(
        world_display_name=world_name,
        world_seed=world_seed,
        default_zone_id=default_zone_id,
        description=description,
    )
    with open(world_info_path, "w", encoding="utf-8") as f:
        json.dump(world_info, f, indent=2)

    # Zones folder: zones/<zone>/zoneInfo.json
    zones_to_write = list(active_zone_ids) if active_zone_ids else [default_zone_id]
    if default_zone_id not in zones_to_write:
        zones_to_write.append(default_zone_id)

    for z_id in zones_to_write:
        write_zone_info(
            output_dir=root,
            zone_id=z_id,
            world_seed=world_seed,
            spawn_coords=spawn_coords,
            respawn_height=respawn_height,
        )

    # Players folder: players/localPlayer.json
    players_dir = root / "players"
    players_dir.mkdir(parents=True, exist_ok=True)

    target_player_zone = player_zone_id if player_zone_id is not None else default_zone_id
    pos = player_pos if player_pos is not None else spawn_coords
    rot = player_rotation if player_rotation is not None else (0.0, 0.0)
    player_info = create_local_player_info(
        zone_id=target_player_zone,
        position=pos,
        rotation=rot,
        gamemode=gamemode,
    )
    with open(players_dir / "localPlayer.json", "w", encoding="utf-8") as f:
        json.dump(player_info, f, indent=2)

    return root
