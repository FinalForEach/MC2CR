# MC2CR (Minecraft to Cosmic Reach Converter)

A standalone external Python tool (not an in-game mod) for converting Minecraft worlds into Cosmic Reach worlds.

## Project Scope & Goals

- **Initial Target Version:** Minecraft Beta 1.7.3 (Region format / McRegion).
- **Target Output:** Latest version of Cosmic Reach world format with disabled/void active world generation.
- **Block Conversion:**
  - Known blocks map to their closest Cosmic Reach equivalents.
  - Unknown/unsupported blocks fall back to verbatim IDs formatted as `minecraft:b173_<id>` (since Beta 1.7.3 lacks string IDs), which Cosmic Reach interprets as debug blocks.
- **Non-Goals:**
  - World generation (tool only converts existing chunks and sets output world to void/no active generator).
  - In-game modding / runtime hooks (this is strictly a standalone external CLI/tool).
  - Mobs and entities outside of the player.
- **Extensibility:** Architecture should be modular to accommodate additional Minecraft versions and region/anvil format variations in the future.

## Directory Structure & Guidelines

- `MC worlds/`: **Read-Only**. Contains source Minecraft world saves to be converted. Never modify or delete files in this folder.
- `CR worlds/`: Destination directory where converted Cosmic Reach worlds are generated.
- `src/`: Python source code containing parsers, block mapping tables, chunk converters, and writers.
- `tests/`: Automated unit and integration tests.

## Development Rules & Coding Guidelines

- Do not use git commands.
- Never write to or mutate `MC worlds/`.
- Keep block mapping logic modular and separated per Minecraft version.
- **File Length Limit:** Clean, modular code; no Python file should exceed 600 LOC (must be refactored if approaching/exceeding this limit).
- **CLI Framework:** Use `click` for CLI argument parsing and commands.
