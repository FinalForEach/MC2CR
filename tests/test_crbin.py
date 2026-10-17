"""Unit tests for CRBin V2 binary serializer."""

from mc2cr.cosmicreach.crbin import CRBinSerializer


def test_crbin_primitives():
    s = CRBinSerializer()
    s.write_string("stringId", "base:container")
    s.write_int("x", 10)
    s.write_int("y", -60)
    s.write_int("z", 25)
    s.write_boolean("isTicking", False)

    data = s.to_bytes()
    assert data.startswith(b"CRB\x02")
    assert b"base:container" in data
    assert b"stringId" in data
    assert b"isTicking" in data


def test_crbin_nested_objects():
    s = CRBinSerializer()

    def write_slot(serializer: CRBinSerializer, slot_num: int, item_id: str, amount: int):
        serializer.write_int("slotId", slot_num)

        def write_stack(stack_s: CRBinSerializer):
            stack_s.write_string("id", item_id)
            stack_s.write_int("amount", amount)
            stack_s.write_int("stackLimit", 1000)

        serializer.write_obj("itemStack", write_stack)
        serializer.write_boolean("outputOnly", False)

    def write_container(serializer: CRBinSerializer):
        serializer.write_string("stringId", "base:container")
        serializer.write_int("x", 5)
        serializer.write_int("y", 10)
        serializer.write_int("z", 15)
        serializer.write_boolean("isTicking", False)

        def write_slot_container(sc_s: CRBinSerializer):
            slots = [
                lambda s: write_slot(s, 0, "base:stone_basalt[default]", 64),
                lambda s: write_slot(s, 1, "base:dirt[default]", 32),
            ]
            sc_s.write_obj_array("slots", slots)
            sc_s.write_int("numberOfSlots", 40)

        serializer.write_obj("slotContainer", write_slot_container)

    s.write_obj_array("blockEntities", [write_container])
    data = s.to_bytes()

    assert data.startswith(b"CRB\x02")
    assert b"blockEntities" in data
    assert b"slotContainer" in data
    assert b"base:stone_basalt[default]" in data
    assert b"base:dirt[default]" in data
