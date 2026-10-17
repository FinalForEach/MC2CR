# MC2CR (Minecraft to Cosmic Reach Converter)

A standalone external Python tool and library for converting Minecraft worlds into Cosmic Reach worlds.

## Project Scope & Goals

- **Supported Minecraft Versions:**
  - Beta 1.7.3 (`.mcr` McRegion format).
  - Release 1.0 – 1.12.2 (`.mca` Anvil format).
  - Release 1.13+ (Modern palette-based Anvil format).
  - Multi-dimension support: Overworld (`0`), Nether (`DIM-1`), and The End (`DIM1`).
- **Target Output:**
  - Latest Cosmic Reach world format with disabled/void active world generation (`base:void`).
  - Native binary chunk serialization, skylight propagation, container tile entities (e.g. chests), and player spawn/position metadata.
- **Block Conversion:**
  - Known blocks map to their closest Cosmic Reach equivalents.
  - Unmapped legacy blocks fall back to numerical debug IDs (`minecraft:<id>[default]`), and unmapped modern blocks fall back to namespaced debug IDs (`minecraft:<name>[default]`). Both are interpreted by Cosmic Reach as missing/debug blocks.
  - Supports user-defined custom JSON mapping overrides.
- **Interfaces:**
  - Command-line interface (`click`).
  - Desktop graphical user interface (`tkinter` / `sv_ttk`).
  - Python library API (`mc2cr`).
- **Non-Goals:**
  - World generation (converts existing chunks only; sets output world generator to void).
  - In-game modding / runtime hooks (standalone external tool and library).
  - Mobs and entities outside of the player.

## Directory Structure & Guidelines

- `src/mc2cr/`: Python source code.
  - `cosmicreach/`: Cosmic Reach binary formats (`.crbin`), region writers, block palettes, and lighting calculations.
  - `minecraft/`: Region parsers (McRegion, Anvil, Modern), block mapping tables, and tile entity converters.
  - `gui/`: Desktop user interface implementation.
  - `converter.py`: Core chunk and world conversion pipeline.
  - `scanner.py`: World save auto-discovery and metadata scanner.
  - `paths.py`: OS-specific save path detection and fallbacks.
  - `cli.py`: CLI commands and argument parsing.
- `tests/`: Automated unit and integration tests.
  - `tests/data/`: Minimal, self-contained test world fixtures (`b1.7.3`, `r1.0`, `r1.2.5`). Tests must never depend on external save folders.
- `packaging/`: PyInstaller build scripts for standalone binary distribution.

## Development Rules & Coding Guidelines

- **No Git Commands:** DO NOT use git commands under any circumstances. All git operations are to be handled by the user.
- **Modular Block Mappings:** Keep block mapping logic modular and separated per Minecraft format/version.
- **File Length Limit:** Clean, modular code; no Python file should exceed 600 LOC (must be refactored if approaching/exceeding this limit).
- **CLI Framework:** Use `click` for CLI argument parsing and commands.
- **Self-Contained Tests:** All tests in `tests/` must remain self-contained, fast, and runnable with `pytest`. New test fixtures should be minimal and placed in `tests/data/`.
