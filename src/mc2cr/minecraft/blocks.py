"""Legacy Minecraft numerical block ID mapping loader with JSON config and custom override support."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Union

import numpy as np


def get_default_mapping_path() -> Path:
    """Resolve the default legacy.json mapping file path across dev and frozen environments."""
    candidates = []
    if hasattr(sys, "_MEIPASS"):
        meipass = Path(sys._MEIPASS)
        candidates.append(meipass / "mc2cr" / "mappings" / "legacy.json")
        candidates.append(meipass / "mappings" / "legacy.json")

    base = Path(__file__).resolve().parent.parent
    candidates.append(base / "mappings" / "legacy.json")
    candidates.append(Path(__file__).parent.parent / "mappings" / "legacy.json")

    for p in candidates:
        if p.exists():
            return p
    return candidates[-1]


DEFAULT_MAPPING_PATH = get_default_mapping_path()


class LegacyBlockMapper:
    """Resolves Minecraft pre-flattening numerical block and item IDs to Cosmic Reach identifiers."""

    def __init__(self, override_path_or_dict: Optional[Union[str, Path, Dict[str, Any]]] = None):
        self.default_mappings: Dict[str, str] = {}
        self.default_data_mappings: Dict[str, str] = {}
        self.override_mappings: Dict[str, str] = {}
        self.override_data_mappings: Dict[str, str] = {}
        self._lookup_table: list[str] = []
        self._lookup_arr: np.ndarray = np.empty(0, dtype=object)

        self._load_defaults()
        if override_path_or_dict:
            self.load_overrides(override_path_or_dict)
        else:
            self._build_lookup_table()

    def _load_defaults(self) -> None:
        mapping_path = get_default_mapping_path()
        if mapping_path.exists():
            with open(mapping_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.default_mappings, self.default_data_mappings = self._normalize_mapping_dict(data)
        else:
            raise FileNotFoundError(
                f"Default block mapping file 'legacy.json' not found. Checked: {mapping_path}"
            )

    def load_overrides(self, override_source: Union[str, Path, Dict[str, Any]]) -> None:
        """Load user overrides from a JSON file or a dictionary."""
        if isinstance(override_source, (str, Path)):
            p = Path(override_source)
            if not p.exists():
                raise FileNotFoundError(f"Mapping override file not found: {p}")
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = override_source
        self.override_mappings, self.override_data_mappings = self._normalize_mapping_dict(data)
        self._build_lookup_table()

    def _build_lookup_table(self) -> None:
        """Precompute all 4,096 block_id (0..255) and metadata (0..15) combinations."""
        table = []
        for b_id in range(256):
            for meta in range(16):
                table.append(self._resolve_key(b_id, meta))
        self._lookup_table = table
        self._lookup_arr = np.array(table, dtype=object)

    @staticmethod
    def _normalize_mapping_dict(raw: Dict[str, Any]) -> tuple[Dict[str, str], Dict[str, str]]:
        targets: Dict[str, str] = {}
        data_overrides: Dict[str, str] = {}
        for key, val in raw.items():
            str_key = str(key)
            if isinstance(val, dict):
                target = val.get("target")
                if target:
                    targets[str_key] = target
                sub_data = val.get("data")
                if isinstance(sub_data, dict):
                    for d_key, d_val in sub_data.items():
                        data_overrides[f"{str_key}:{d_key}"] = str(d_val)
            elif isinstance(val, str):
                targets[str_key] = val
        return targets, data_overrides

    def _resolve_key(self, block_id: int, metadata: int = 0) -> str:
        meta_key = f"{block_id}:{metadata}"
        id_key = str(block_id)

        # 1. Check user overrides
        if meta_key in self.override_data_mappings:
            return self.override_data_mappings[meta_key]
        if meta_key in self.override_mappings:
            return self.override_mappings[meta_key]
        if id_key in self.override_mappings:
            return self.override_mappings[id_key]

        # 2. Check defaults
        if meta_key in self.default_data_mappings:
            return self.default_data_mappings[meta_key]
        if meta_key in self.default_mappings:
            return self.default_mappings[meta_key]
        if id_key in self.default_mappings:
            return self.default_mappings[id_key]

        # 3. Fallback
        if block_id == 0:
            return "base:air[default]"
        return f"minecraft:{block_id}[default]"

    def get_block_save_key(self, block_id: int, metadata: int = 0) -> str:
        """Get the Cosmic Reach block save key for a given block ID and optional metadata."""
        if 0 <= block_id < 256 and 0 <= metadata < 16:
            return self._lookup_table[(block_id << 4) | metadata]
        return self._resolve_key(block_id, metadata)


# Backwards compatibility aliases
BlockMapper = LegacyBlockMapper
B173BlockMapper = LegacyBlockMapper

_DEFAULT_MAPPER = LegacyBlockMapper()


def get_block_save_key(block_id: int, metadata: int = 0) -> str:
    """Convenience helper using the default mapper."""
    return _DEFAULT_MAPPER.get_block_save_key(block_id, metadata)


get_b173_block_save_key = get_block_save_key
