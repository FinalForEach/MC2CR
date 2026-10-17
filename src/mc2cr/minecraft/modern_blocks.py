"""Block mapper for modern Minecraft 1.13+ (The Flattening) to Cosmic Reach."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

# Default fallback mappings for modern blocks (1.13 through 1.21)
MODERN_DEFAULT_MAPPINGS: Dict[str, str] = {
    #1.13 Update Aquatic
    "minecraft:seagrass": "base:leaves[type=permament]",
    "minecraft:tall_seagrass": "base:leaves[type=permament]",
    "minecraft:kelp_plant": "base:leaves[type=permament]",
    "minecraft:cave_air": "base:air[default]",
    "minecraft:bubble_column": "base:water[default]",
    # Deepslate and ores
    "minecraft:deepslate": "base:stone_shale[default]",
    "minecraft:cobbled_deepslate": "base:cobblestone_basalt[default]",
    "minecraft:polished_deepslate": "base:stone_basalt[default]",
    "minecraft:deepslate_bricks": "base:stone_bricks[default]",
    "minecraft:deepslate_tiles": "base:stone_bricks[default]",
    "minecraft:reinforced_deepslate": "base:stone_basalt[default]",
    "minecraft:deepslate_coal_ore": "base:coal[default]",
    "minecraft:deepslate_iron_ore": "base:ore_iron[default]",
    "minecraft:deepslate_gold_ore": "base:ore_gold[default]",
    "minecraft:deepslate_redstone_ore": "base:magma[default]",
    "minecraft:deepslate_diamond_ore": "base:ore_ruby[default]",
    "minecraft:deepslate_lapis_ore": "base:ore_sapphire[default]",
    "minecraft:deepslate_emerald_ore": "base:ore_sapphire[default]",
    "minecraft:deepslate_copper_ore": "base:ore_bauxite[default]",
    "minecraft:copper_ore": "base:ore_bauxite[default]",
    "minecraft:copper_block": "base:metal_panel[default]",
    "minecraft:cut_copper": "base:metal_panel[default]",
    "minecraft:raw_iron_block": "base:metal_panel[default]",
    "minecraft:raw_copper_block": "base:metal_panel[default]",
    "minecraft:raw_gold_block": "base:gold_block[default]",
    # 1.17+ Stones & Geodes
    "minecraft:tuff": "base:stone_shale[default]",
    "minecraft:tuff_bricks": "base:stone_bricks[default]",
    "minecraft:calcite": "base:stone_limestone[default]",
    "minecraft:dripstone_block": "base:stone_shale[default]",
    "minecraft:pointed_dripstone": "base:stone_shale[default]",
    "minecraft:smooth_basalt": "base:stone_basalt[default]",
    "minecraft:amethyst_block": "base:sapphire_block[default]",
    "minecraft:budding_amethyst": "base:sapphire_block[default]",
    "minecraft:amethyst_cluster": "base:light[default]",
    "minecraft:tinted_glass": "base:glass[default]",
    # 1.16 Nether Update
    "minecraft:blackstone": "base:stone_basalt[default]",
    "minecraft:polished_blackstone": "base:stone_basalt[default]",
    "minecraft:polished_blackstone_bricks": "base:stone_bricks[default]",
    "minecraft:gilded_blackstone": "base:ore_gold[default]",
    "minecraft:basalt": "base:stone_basalt[default]",
    "minecraft:ancient_debris": "base:stone_komatiite[default]",
    "minecraft:netherite_block": "base:metal_panel[default]",
    "minecraft:crying_obsidian": "base:asphalt[default]",
    "minecraft:respawn_anchor": "base:light[default]",
    "minecraft:lodestone": "base:metal_panel[default]",
    "minecraft:target": "base:wood_planks[default]",
    "minecraft:shroomlight": "base:light[power=on,lightRed=13,lightGreen=7,lightBlue=0]",
    "minecraft:soul_sand": "base:stone_shale[default]",
    "minecraft:soul_soil": "base:stone_shale[default]",
    "minecraft:soul_fire": "base:magma[default]",
    "minecraft:soul_torch": "base:torch[level=4,type=ground]",
    "minecraft:soul_lantern": "base:torch[level=4,type=ground]",
    "minecraft:soul_campfire": "base:magma[default]",
    "minecraft:crimson_nylium": "base:stone_komatiite[default]",
    "minecraft:warped_nylium": "base:plastic_block[color=cyan]",
    "minecraft:crimson_stem": "base:tree_log[axis=Y]",
    "minecraft:warped_stem": "base:tree_log[axis=Y]",
    "minecraft:stripped_crimson_stem": "base:tree_log[axis=Y]",
    "minecraft:stripped_warped_stem": "base:tree_log[axis=Y]",
    "minecraft:crimson_planks": "base:wood_planks[default]",
    "minecraft:warped_planks": "base:wood_planks[default]",
    "minecraft:crimson_slab": "base:wood_planks[slab_type=bottom]",
    "minecraft:warped_slab": "base:wood_planks[slab_type=bottom]",
    "minecraft:crimson_stairs": "base:wood_planks[default]",
    "minecraft:warped_stairs": "base:wood_planks[default]",
    "minecraft:crimson_roots": "base:grass_blades_lux[default]",
    "minecraft:warped_roots": "base:grass_blades_lux[default]",
    "minecraft:nether_sprouts": "base:grass_blades_lux[default]",
    "minecraft:weeping_vines": "base:plastic_block[color=red]",
    "minecraft:twisting_vines": "base:plastic_block[color=cyan]",
    # 1.14 Village & Pillage / Functional
    "minecraft:lantern": "base:torch[level=4,type=ground]",
    "minecraft:barrel": "base:crate[default]",
    "minecraft:smoker": "base:furnace[default]",
    "minecraft:blast_furnace": "base:furnace[default]",
    "minecraft:cartography_table": "base:wood_planks[default]",
    "minecraft:fletching_table": "base:wood_planks[default]",
    "minecraft:grindstone": "base:stone_basalt[default]",
    "minecraft:smithing_table": "base:wood_planks[default]",
    "minecraft:stonecutter": "base:stone_basalt[slab_type=bottom]",
    "minecraft:bell": "base:gold_block[default]",
    "minecraft:campfire": "base:magma[default]",
    "minecraft:composter": "base:wood_planks[default]",
    "minecraft:sweet_berry_bush": "base:grass_blades_lux[default]",
    # 1.15 Bees
    "minecraft:bee_nest": "base:wood_planks[default]",
    "minecraft:beehive": "base:wood_planks[default]",
    "minecraft:honey_block": "base:cheese[default]",
    "minecraft:honeycomb_block": "base:cheese[default]",
    # 1.19 Deep Dark & Mangrove
    "minecraft:sculk": "base:stone_komatiite[default]",
    "minecraft:sculk_catalyst": "base:stone_komatiite[default]",
    "minecraft:sculk_shrieker": "base:stone_komatiite[default]",
    "minecraft:sculk_sensor": "base:laser_switch[default]",
    "minecraft:sculk_vein": "base:grass_blades_lux[default]",
    "minecraft:mud": "base:dirt[default]",
    "minecraft:mud_bricks": "base:stone_bricks[default]",
    "minecraft:packed_mud": "base:dirt[default]",
    "minecraft:mangrove_log": "base:tree_log[axis=Y]",
    "minecraft:mangrove_planks": "base:wood_planks[default]",
    "minecraft:mangrove_leaves": "base:leaves_poplar[dist=1,type=decaying]",
    "minecraft:mangrove_roots": "base:tree_log[axis=Y]",
    "minecraft:muddy_mangrove_roots": "base:dirt[default]",
    # 1.20 Trails & Tales
    "minecraft:cherry_log": "base:tree_log[axis=Y]",
    "minecraft:cherry_planks": "base:wood_planks[default]",
    "minecraft:cherry_leaves": "base:leaves_poplar[dist=1,type=decaying]",
    "minecraft:cherry_sapling": "base:sapling_poplar[default]",
    "minecraft:bamboo_block": "base:tree_log[axis=Y]",
    "minecraft:bamboo_planks": "base:wood_planks[default]",
    "minecraft:chiseled_bookshelf": "base:wood_planks[default]",
    "minecraft:decorated_pot": "base:cardboard_box[default]",
    "minecraft:suspicious_sand": "base:sand[default]",
    "minecraft:suspicious_gravel": "base:stone_gravel[default]",
    "minecraft:short_grass": "base:grass_blades[default]",
    # 1.25 Spring to Life
    "minecraft:leaf_litter": "base:grass_blades_lux[default]"
}


class ModernBlockMapper:
    """Maps modern namespaced Minecraft block states (1.13+) to Cosmic Reach save keys with caching."""

    def __init__(self, override_path_or_dict: Optional[str | Path | Dict] = None):
        self.modern_map: Dict[str, str] = {}
        self._cache: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], str] = {}
        self._load_from_legacy()
        self._load_builtins()

        if override_path_or_dict:
            if isinstance(override_path_or_dict, dict):
                self.modern_map.update(override_path_or_dict)
            else:
                p = Path(override_path_or_dict)
                if p.exists():
                    with open(p, "r", encoding="utf-8") as f:
                        self.modern_map.update(json.load(f))

    def _load_from_legacy(self) -> None:
        legacy_path = Path(__file__).parent.parent / "mappings" / "legacy.json"
        if not legacy_path.exists():
            return
        with open(legacy_path, "r", encoding="utf-8") as f:
            legacy_data = json.load(f)

        for _, entry in legacy_data.items():
            target = entry.get("target")
            modern_id = entry.get("modern")
            if modern_id and target:
                self.modern_map[modern_id] = target

            # Variant modern IDs
            data_map = entry.get("data", {})
            data_modern = entry.get("data_modern", {})
            for d_key, mod_variant in data_modern.items():
                var_target = data_map.get(d_key, target)
                if mod_variant and var_target:
                    self.modern_map[mod_variant] = var_target

    def _load_builtins(self) -> None:
        for mod_id, target in MODERN_DEFAULT_MAPPINGS.items():
            if mod_id not in self.modern_map:
                self.modern_map[mod_id] = target

    def get_block_save_key(self, block_state: str | Dict[str, Any]) -> str:
        """Resolve a modern block state string or compound tag to a Cosmic Reach block save key."""
        if isinstance(block_state, str):
            if block_state in self.modern_map:
                return self.modern_map[block_state]
            clean = block_state.removeprefix("minecraft:")
            return f"minecraft:{clean}[default]"

        name = block_state.get("Name", "minecraft:air")
        props = block_state.get("Properties")
        if not props:
            if name in self.modern_map:
                return self.modern_map[name]
            clean = name.removeprefix("minecraft:")
            return f"minecraft:{clean}[default]"

        # Check cache for compound block state
        props_tuple = tuple(sorted(props.items()))
        cache_key = (name, props_tuple)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        # 1. Exact string match if properties exist
        prop_str = ",".join(f"{k}={v}" for k, v in props_tuple)
        full_state = f"{name}[{prop_str}]"
        if full_state in self.modern_map:
            res = self.modern_map[full_state]
            self._cache[cache_key] = res
            return res

        # Check individual directional properties (facing/axis)
        if "facing" in props:
            facing_state = f"{name}[facing={props['facing']}]"
            if facing_state in self.modern_map:
                res = self.modern_map[facing_state]
                self._cache[cache_key] = res
                return res

        # 2. Base name match
        if name in self.modern_map:
            res = self.modern_map[name]
            self._cache[cache_key] = res
            return res

        # 3. Fallback to verbatim name formatted for Cosmic Reach debug block
        clean_name = name.removeprefix("minecraft:")
        res = f"minecraft:{clean_name}[default]"
        self._cache[cache_key] = res
        return res
