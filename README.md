# MC2CR (Minecraft to Cosmic Reach Converter)

**MC2CR** is a world converter and Python library for translating Minecraft worlds (Beta 1.7.3 McRegion, Anvil Release 1.0 - 1.13+) into [Cosmic Reach](https://finalforeach.itch.io/cosmic-reach) worlds.

---

## Installation

### Prerequisites
- Python 3.10+

### Install from Source
```bash
git clone https://github.com/finalforeach/mc2cr.git
cd MC2CR
pip install -e .
```

To install development and packaging dependencies:
```bash
pip install -e ".[dev,build]"
```

---

## Running MC2CR

### 1. Graphical User Interface (GUI)
Launch the native desktop interface:
```bash
mc2cr-gui
# or
mc2cr gui
# or
python3 -m mc2cr.gui
```

### 2. Command Line Interface (CLI)
List discovered worlds:
```bash
mc2cr convert --list-worlds
```

Convert a specific world:
```bash
mc2cr convert --input "1.7.3 world" --output "Converted Cosmic Reach World" -y -64
```

CLI options:
- `-i, --input`: Path or folder name of the source Minecraft world.
- `-o, --output`: Target folder name/path in Cosmic Reach saves.
- `-y, --y-offset`: Vertical block offset (default: `-64`).
- `-w, --workers`: Number of parallel worker threads (default: CPU core count).
- `-m, --mapping`: Path to a custom block mapping JSON override file.

---


## Building a Standalone Executable

To produce a single-file static executable (`.exe` on Windows, single binary on Linux/macOS):

```bash
pip install -e ".[build]"
python packaging/build_executable.py
```

The standalone binary will be created in the `dist/` directory.

---

## Running Tests

Run the test suite with `pytest`:

```bash
pytest
```

---

## License

This project is licensed under the [MIT License](LICENSE).
