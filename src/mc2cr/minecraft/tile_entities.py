"""Conversion of Minecraft Beta 1.7.3 TileEntities (e.g. Chests) to Cosmic Reach BlockEntities."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from mc2cr.cosmicreach.crbin import CRBinSerializer
from mc2cr.minecraft.b173_blocks import B173BlockMapper


def convert_chest_tile_entity(
    te_data: Dict[str, Any],
    mapper: B173BlockMapper,
    y_offset: int = -64,
    num_slots: int = 40,
) -> Callable[[CRBinSerializer], None]:
    """Convert a Minecraft Beta 1.7.3 Chest TileEntity into a Cosmic Reach CRBin writer."""
    gx = int(te_data.get("x", 0))
    gy = int(te_data.get("y", 0)) + y_offset
    gz = int(te_data.get("z", 0))
    raw_items = te_data.get("Items", [])

    items_by_slot = {}
    for item_data in raw_items:
        slot_idx = int(item_data.get("Slot", 0))
        item_id = int(item_data.get("id", 0))
        count = int(item_data.get("Count", 1))
        cr_item_key = mapper.get_block_save_key(item_id)
        items_by_slot[slot_idx] = (cr_item_key, count)

    slots_to_write = []
    for s_idx in range(num_slots):
        item_info = items_by_slot.get(s_idx)

        def make_slot_writer(slot_num: int, info: Optional[Tuple[str, int]]):
            def write_slot(slot_s: CRBinSerializer):
                slot_s.write_int("slotId", slot_num)
                if info is not None:
                    k, cnt = info

                    def write_stack(stack_s: CRBinSerializer):
                        stack_s.write_string("id", k)
                        stack_s.write_int("amount", cnt)
                        stack_s.write_int("stackLimit", 1000)

                    slot_s.write_obj("itemStack", write_stack)
                else:
                    slot_s.write_obj("itemStack", None)
                slot_s.write_boolean("outputOnly", False)

            return write_slot

        slots_to_write.append(make_slot_writer(s_idx, item_info))

    def write_container(serializer: CRBinSerializer):
        serializer.write_string("stringId", "base:container")
        serializer.write_int("x", gx)
        serializer.write_int("y", gy)
        serializer.write_int("z", gz)
        serializer.write_boolean("isTicking", False)

        def write_slot_container(sc_s: CRBinSerializer):
            sc_s.write_obj_array("slots", slots_to_write)
            sc_s.write_int("numberOfSlots", num_slots)

        serializer.write_obj("slotContainer", write_slot_container)

    return write_container


def build_chunk_block_entities_binary(
    tile_entities: List[Dict[str, Any]],
    mapper: B173BlockMapper,
    y_offset: int = -64,
) -> Optional[bytes]:
    """Serialize all supported tile entities in a CR chunk into a CRBin V2 binary stream."""
    writers = []
    for te in tile_entities:
        te_id = str(te.get("id", ""))
        if te_id == "Chest":
            writers.append(convert_chest_tile_entity(te, mapper, y_offset=y_offset))

    if not writers:
        return None

    serializer = CRBinSerializer()
    serializer.write_obj_array("blockEntities", writers)
    return serializer.to_bytes()
