"""Take screenshots of Tetris game for README"""
import sys, os, time, subprocess, tkinter as tk
from PIL import ImageGrab

sys.path.insert(0, os.path.dirname(__file__))

# Create the game directly with a pre-populated board for a nice screenshot
from tetris import Tetris, Piece, SHAPES, GRID_WIDTH, GRID_HEIGHT, COLORS, CELL, BG

# Screenshot 1: Manual play state (no menu overlay)
print("Taking screenshot 1: Manual play...")
g = Tetris(ai_mode=False)

# Populate board with some blocks for visual interest
for x in range(GRID_WIDTH):
    if x not in (2, 5, 8):  # leave gaps so not full rows
        g.board[GRID_HEIGHT - 1][x] = 'I'
    if x not in (1, 4, 7, 9):
        g.board[GRID_HEIGHT - 2][x] = 'S'
    if x not in (0, 3, 6):
        g.board[GRID_HEIGHT - 3][x] = 'J'
    if x not in (2, 5, 8):
        g.board[GRID_HEIGHT - 4][x] = 'L'
    if x not in (1, 4, 7):
        g.board[GRID_HEIGHT - 5][x] = 'T'
    if x not in (3, 6, 9):
        g.board[GRID_HEIGHT - 6][x] = 'O'
    if x not in (0, 4, 8):
        g.board[GRID_HEIGHT - 7][x] = 'Z'

# Set some stats
g.score = 12500
g.level = 5
g.lines = 42

# Move piece to interesting position
g.current = Piece('T')
g.current.x = 4
g.current.y = GRID_HEIGHT - 9

g.next = Piece('I')

g._draw()
g.root.update()
g.root.update_idletasks()

# Wait for window to render
time.sleep(0.5)

# Get window position
g.root.update()
x = g.root.winfo_rootx()
y = g.root.winfo_rooty()
w = g.root.winfo_width()
h = g.root.winfo_height()

# Take screenshot
img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
os.makedirs('screenshots', exist_ok=True)
img.save('screenshots/manual_play.png')
print(f"  Saved screenshots/manual_play.png ({w}x{h})")

# Screenshot 2: Menu overlay
print("Taking screenshot 2: Menu state...")
g.in_menu = True
g._draw()
g.root.update()
time.sleep(0.3)
img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
img.save('screenshots/menu.png')
print(f"  Saved screenshots/menu.png ({w}x{h})")

# Screenshot 3: Game over
print("Taking screenshot 3: Game over...")
g.in_menu = False
g.game_over = True
g.score = 68000
g.lines = 112
g._draw()
g.root.update()
time.sleep(0.3)
img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
img.save('screenshots/game_over.png')
print(f"  Saved screenshots/game_over.png ({w}x{h})")

g.root.destroy()
print("Done! All screenshots saved.")
