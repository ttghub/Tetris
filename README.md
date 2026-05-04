# Tetris

A classic Tetris game built with Python and tkinter. Features both manual play and AI auto-play modes.

## Features

- **7 standard tetrominoes** (I/O/T/S/Z/J/L) with rotation and wall kicks
- **Ghost piece** preview showing landing position
- **Next piece** preview panel
- **7-bag randomizer** for fair piece distribution
- **Scoring system** (Single/Double/Triple/Tetris bonuses × level)
- **10-level speed progression** (drop speed increases per level)
- **AI auto-play mode** with heuristic evaluation (height, holes, bumpiness)
- **In-game mode switching** (press `A` to toggle Manual ↔ AI, `ESC` for menu)
- **Robust logging** with instant-flush crash diagnostics

## Controls

| Key | Action |
|-----|--------|
| ← → | Move left/right |
| ↑ | Rotate |
| ↓ | Soft drop (+1 point/cell) |
| Space | Hard drop (+2 points/cell) |
| R | Restart |
| A | Toggle Manual / AI mode |
| ESC | Pause menu (M=Manual, A=AI, Q=Quit) |

## Scoring

| Lines Cleared | Base Points |
|---------------|-------------|
| 1 (Single) | 100 × level |
| 2 (Double) | 300 × level |
| 3 (Triple) | 500 × level |
| 4 (Tetris) | 800 × level |

**Level** = `total_lines // 10 + 1`

## Running from Source

```bash
# No dependencies required (pure Python standard library)
python tetris.py
```

## Running the EXE

Download `Tetris.exe` from [Releases](https://github.com/YOUR_USER/Tetris/releases) and double-click to run.

No installation required — everything is bundled in the single EXE.

## Building the EXE

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name Tetris tetris.py
```

The EXE will be in `dist/Tetris.exe`.

## Running Tests

```bash
# Unit tests (26 cases)
python test_tetris.py

# Stress tests (10 scenarios)
python test_stress.py

# AI bot validation (100 games)
python ai_bot.py
```

## Project Structure

```
Tetris/
├── tetris.py          # Main game (710+ lines)
├── test_tetris.py     # Unit tests
├── test_stress.py     # Stress tests
├── ai_bot.py          # AI automated testing
├── ai_gui.py          # AI visual demo
├── requirements.txt   # Dependencies (none required)
├── .gitignore
└── README.md
```

## AI Mode

The AI evaluates every possible rotation and column position, simulates the drop, clears lines, and scores the resulting board using a heuristic:

- **Height** (×10) — minimize stack height
- **Holes** (×25) — avoid creating gaps
- **Bumpiness** (×2) — keep surface flat

The AI consistently clears 100+ lines and scores 60,000+ points per game.

## License

MIT
