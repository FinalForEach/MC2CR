"""Pure-Python CRBin V2 binary serializer matching Cosmic Reach's CRBin format."""

from __future__ import annotations

import struct
from typing import Any, Callable, Dict, List, Optional, Tuple


class SchemaType:
    SCHEMA_END = 0

    BYTE = 1
    SHORT = 2
    INT = 3
    LONG = 4
    FLOAT = 5
    DOUBLE = 6
    BOOLEAN = 7
    STRING = 9

    OBJ = 10

    BYTE_ARRAY = 11
    SHORT_ARRAY = 12
    INT_ARRAY = 13
    LONG_ARRAY = 14
    FLOAT_ARRAY = 15
    DOUBLE_ARRAY = 16
    BOOLEAN_ARRAY = 17
    STRING_ARRAY = 18
    OBJ_ARRAY = 19


def write_varint(buf: bytearray, value: int) -> None:
    """Write ZigZag encoded VarInt."""
    zz = (value << 1) ^ (value >> 31)
    while (zz & ~0x7F) != 0:
        buf.append((zz & 0x7F) | 0x80)
        zz >>= 7
    buf.append(zz & 0x7F)


class CRBinSchema:
    """Schema descriptor containing ordered list of (name, type)."""

    def __init__(self):
        self.items: List[Tuple[str, int]] = []

    def add(self, name: str, item_type: int) -> None:
        if name is None:
            return
        for n, _ in self.items:
            if n.lower() == name.lower():
                raise ValueError(f"Duplicate name in schema: {name}")
        self.items.append((name, item_type))

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, CRBinSchema):
            return False
        return self.items == other.items

    def __repr__(self) -> str:
        return f"CRBinSchema({self.items})"


class CRBinSerializer:
    """Serializes structured objects into Cosmic Reach Binary (CRBin V2) format."""

    def __init__(self):
        self.schema = CRBinSchema()
        self.alt_schemas: List[CRBinSchema] = []
        self.strings: List[str] = []
        self.bytes = bytearray()

    def _register_string(self, value: Optional[str]) -> int:
        if value is None:
            return -1
        if value in self.strings:
            return self.strings.index(value)
        idx = len(self.strings)
        self.strings.append(value)
        return idx

    def write_boolean(self, name: Optional[str], value: bool) -> None:
        if name is not None:
            self.schema.add(name, SchemaType.BOOLEAN)
        self.bytes.append(1 if value else 0)

    def write_byte(self, name: Optional[str], value: int) -> None:
        if name is not None:
            self.schema.add(name, SchemaType.BYTE)
        self.bytes.append(value & 0xFF)

    def write_short(self, name: Optional[str], value: int) -> None:
        if name is not None:
            self.schema.add(name, SchemaType.SHORT)
        self.bytes.extend(struct.pack(">h", value))

    def write_int(self, name: Optional[str], value: int) -> None:
        if name is not None:
            self.schema.add(name, SchemaType.INT)
        write_varint(self.bytes, value)

    def write_long(self, name: Optional[str], value: int) -> None:
        if name is not None:
            self.schema.add(name, SchemaType.LONG)
        self.bytes.extend(struct.pack(">q", value))

    def write_float(self, name: Optional[str], value: float) -> None:
        if name is not None:
            self.schema.add(name, SchemaType.FLOAT)
        self.bytes.extend(struct.pack(">f", value))

    def write_double(self, name: Optional[str], value: float) -> None:
        if name is not None:
            self.schema.add(name, SchemaType.DOUBLE)
        self.bytes.extend(struct.pack(">d", value))

    def write_string(self, name: Optional[str], value: Optional[str]) -> None:
        if name is not None:
            self.schema.add(name, SchemaType.STRING)
        str_id = self._register_string(value)
        write_varint(self.bytes, str_id)

    def write_obj(self, name: Optional[str], obj_writer: Optional[Callable[[CRBinSerializer], None]]) -> None:
        if name is not None:
            self.schema.add(name, SchemaType.OBJ)

        if obj_writer is None:
            write_varint(self.bytes, -1)
            return

        old_schema = self.schema
        old_bytes = self.bytes

        self.schema = CRBinSchema()
        self.bytes = bytearray()

        obj_writer(self)

        curr_schema = self.schema
        obj_bytes = self.bytes

        # Find or register alt schema
        if curr_schema not in self.alt_schemas:
            self.alt_schemas.append(curr_schema)
        schema_idx = self.alt_schemas.index(curr_schema)

        self.schema = old_schema
        self.bytes = old_bytes

        write_varint(self.bytes, schema_idx)
        self.bytes.extend(obj_bytes)

    def write_obj_array(
        self,
        name: Optional[str],
        items: Optional[List[Optional[Callable[[CRBinSerializer], None]]]],
    ) -> None:
        if name is not None:
            self.schema.add(name, SchemaType.OBJ_ARRAY)

        if items is None:
            write_varint(self.bytes, -1)
            return

        write_varint(self.bytes, len(items))
        for item_writer in items:
            self.write_obj(None, item_writer)

    def to_bytes(self) -> bytes:
        """Construct full CRBin V2 binary payload."""
        # 1. Register schema item names into string pool
        for name, _ in self.schema.items:
            self._register_string(name)
        for alt in self.alt_schemas:
            for name, _ in alt.items:
                self._register_string(name)

        out = bytearray()

        # 2. V2 Header
        out.extend(b"CRB\x02")

        # 3. String pool
        write_varint(out, len(self.strings))
        for s in self.strings:
            if s is None:
                write_varint(out, -1)
            else:
                encoded = s.encode("utf-8")
                write_varint(out, len(encoded))
                out.extend(encoded)

        # 4. Root schema
        for name, item_type in self.schema.items:
            out.append(item_type)
            write_varint(out, self.strings.index(name))
        out.append(SchemaType.SCHEMA_END)

        # 5. Alt schemas
        write_varint(out, len(self.alt_schemas))
        for alt in self.alt_schemas:
            for name, item_type in alt.items:
                out.append(item_type)
                write_varint(out, self.strings.index(name))
            out.append(SchemaType.SCHEMA_END)

        # 6. Payload data
        out.extend(self.bytes)
        return bytes(out)
