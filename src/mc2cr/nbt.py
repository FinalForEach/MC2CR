"""Lightweight, high-performance binary NBT parser with selective tag skipping."""

from __future__ import annotations

try:
    from isal import igzip as gzip_backend
    from isal import isal_zlib as zlib_backend
except ImportError:
    import gzip as gzip_backend
    import zlib as zlib_backend

import struct
from io import BytesIO
from typing import Any, BinaryIO, Dict, List, Optional, Set, Tuple


class TAG:
    END = 0
    BYTE = 1
    SHORT = 2
    INT = 3
    LONG = 4
    FLOAT = 5
    DOUBLE = 6
    BYTE_ARRAY = 7
    STRING = 8
    LIST = 9
    COMPOUND = 10
    INT_ARRAY = 11
    LONG_ARRAY = 12


DEFAULT_SKIP_KEYS: Set[str] = {
    "structures",
    "Heightmaps",
    "block_ticks",
    "fluid_ticks",
    "PostProcessing",
    "CarvingMasks",
    "Lights",
    "Entities",
}


def read_nbt(
    data_or_stream: bytes | BinaryIO,
    skip_keys: Optional[Set[str]] = None,
) -> Tuple[str, Dict[str, Any]]:
    """Parse NBT payload from bytes or a stream. Handles gzip/zlib decompression."""
    if isinstance(data_or_stream, bytes):
        raw = data_or_stream
        if raw.startswith(b"\x1f\x8b"):
            raw = gzip_backend.decompress(raw)
        elif raw.startswith(b"\x78\x9c") or raw.startswith(b"\x78\x01") or raw.startswith(b"\x78\xda"):
            try:
                raw = zlib_backend.decompress(raw)
            except Exception:
                pass
        return _FastNBTParser(raw, skip_keys=skip_keys).parse()

    # Stream fallback
    raw = data_or_stream.read()
    return _FastNBTParser(raw, skip_keys=skip_keys).parse()


class _FastNBTParser:
    """Zero-copy buffer NBT parser using struct.unpack_from."""

    __slots__ = ("data", "pos", "skip_keys")

    def __init__(self, data: bytes, skip_keys: Optional[Set[str]] = None):
        self.data = data
        self.pos = 0
        self.skip_keys = skip_keys

    def parse(self) -> Tuple[str, Dict[str, Any]]:
        if self.pos >= len(self.data):
            return "", {}
        tag_type = self.data[self.pos]
        self.pos += 1
        if tag_type == TAG.END:
            return "", {}
        name = self._read_string()
        payload = self._read_payload(tag_type)
        return name, payload

    def _read_string(self) -> str:
        length = struct.unpack_from(">H", self.data, self.pos)[0]
        self.pos += 2
        s = self.data[self.pos : self.pos + length].decode("utf-8", errors="replace")
        self.pos += length
        return s

    def _skip_payload(self, tag_type: int) -> None:
        if tag_type == TAG.BYTE:
            self.pos += 1
        elif tag_type == TAG.SHORT:
            self.pos += 2
        elif tag_type == TAG.INT or tag_type == TAG.FLOAT:
            self.pos += 4
        elif tag_type == TAG.LONG or tag_type == TAG.DOUBLE:
            self.pos += 8
        elif tag_type == TAG.BYTE_ARRAY:
            length = struct.unpack_from(">i", self.data, self.pos)[0]
            self.pos += 4 + length
        elif tag_type == TAG.STRING:
            length = struct.unpack_from(">H", self.data, self.pos)[0]
            self.pos += 2 + length
        elif tag_type == TAG.LIST:
            item_type = self.data[self.pos]
            length = struct.unpack_from(">i", self.data, self.pos + 1)[0]
            self.pos += 5
            for _ in range(length):
                self._skip_payload(item_type)
        elif tag_type == TAG.COMPOUND:
            while self.pos < len(self.data):
                child_type = self.data[self.pos]
                self.pos += 1
                if child_type == TAG.END:
                    break
                name_len = struct.unpack_from(">H", self.data, self.pos)[0]
                self.pos += 2 + name_len
                self._skip_payload(child_type)
        elif tag_type == TAG.INT_ARRAY:
            length = struct.unpack_from(">i", self.data, self.pos)[0]
            self.pos += 4 + length * 4
        elif tag_type == TAG.LONG_ARRAY:
            length = struct.unpack_from(">i", self.data, self.pos)[0]
            self.pos += 4 + length * 8

    def _read_payload(self, tag_type: int) -> Any:
        if tag_type == TAG.BYTE:
            val = struct.unpack_from(">b", self.data, self.pos)[0]
            self.pos += 1
            return val
        elif tag_type == TAG.SHORT:
            val = struct.unpack_from(">h", self.data, self.pos)[0]
            self.pos += 2
            return val
        elif tag_type == TAG.INT:
            val = struct.unpack_from(">i", self.data, self.pos)[0]
            self.pos += 4
            return val
        elif tag_type == TAG.LONG:
            val = struct.unpack_from(">q", self.data, self.pos)[0]
            self.pos += 8
            return val
        elif tag_type == TAG.FLOAT:
            val = struct.unpack_from(">f", self.data, self.pos)[0]
            self.pos += 4
            return val
        elif tag_type == TAG.DOUBLE:
            val = struct.unpack_from(">d", self.data, self.pos)[0]
            self.pos += 8
            return val
        elif tag_type == TAG.BYTE_ARRAY:
            length = struct.unpack_from(">i", self.data, self.pos)[0]
            self.pos += 4
            val = bytearray(self.data[self.pos : self.pos + length])
            self.pos += length
            return val
        elif tag_type == TAG.STRING:
            return self._read_string()
        elif tag_type == TAG.LIST:
            item_type = self.data[self.pos]
            length = struct.unpack_from(">i", self.data, self.pos + 1)[0]
            self.pos += 5
            return [self._read_payload(item_type) for _ in range(length)]
        elif tag_type == TAG.COMPOUND:
            compound: Dict[str, Any] = {}
            while self.pos < len(self.data):
                child_type = self.data[self.pos]
                self.pos += 1
                if child_type == TAG.END:
                    break
                child_name = self._read_string()
                if self.skip_keys and child_name in self.skip_keys:
                    self._skip_payload(child_type)
                else:
                    compound[child_name] = self._read_payload(child_type)
            return compound
        elif tag_type == TAG.INT_ARRAY:
            length = struct.unpack_from(">i", self.data, self.pos)[0]
            self.pos += 4
            vals = list(struct.unpack_from(f">{length}i", self.data, self.pos))
            self.pos += length * 4
            return vals
        elif tag_type == TAG.LONG_ARRAY:
            length = struct.unpack_from(">i", self.data, self.pos)[0]
            self.pos += 4
            vals = list(struct.unpack_from(f">{length}q", self.data, self.pos))
            self.pos += length * 8
            return vals
        else:
            raise ValueError(f"Unknown NBT Tag type: {tag_type}")
