"""Tests for NBT binary parsing."""

import gzip
import struct
from io import BytesIO

from mc2cr.nbt import TAG, read_nbt


def test_nbt_compound_and_primitives():
    # Build a small binary NBT stream
    buf = bytearray()
    buf.append(TAG.COMPOUND)  # Root
    buf.extend(struct.pack(">H", 4))  # Name length
    buf.extend(b"Test")

    # Byte tag "b" = 42
    buf.append(TAG.BYTE)
    buf.extend(struct.pack(">H", 1))
    buf.extend(b"b")
    buf.extend(struct.pack(">b", 42))

    # Int tag "i" = 100000
    buf.append(TAG.INT)
    buf.extend(struct.pack(">H", 1))
    buf.extend(b"i")
    buf.extend(struct.pack(">i", 100000))

    # String tag "str" = "hello"
    buf.append(TAG.STRING)
    buf.extend(struct.pack(">H", 3))
    buf.extend(b"str")
    buf.extend(struct.pack(">H", 5))
    buf.extend(b"hello")

    # TAG_End
    buf.append(TAG.END)

    # Test uncompressed
    name, payload = read_nbt(bytes(buf))
    assert name == "Test"
    assert payload["b"] == 42
    assert payload["i"] == 100000
    assert payload["str"] == "hello"

    # Test gzip compressed
    gzipped = gzip.compress(bytes(buf))
    name_gz, payload_gz = read_nbt(gzipped)
    assert name_gz == "Test"
    assert payload_gz["b"] == 42
