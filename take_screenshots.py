"""Take screenshots of Tetris game for README"""
import sys, os, time, tkinter as tk
from PIL import ImageGrab

sys.path.insert(0, os.path.dirname(__file__))
from tetris import Tetris, Piece, GRID_WIDTH, GRID_HEIGHT

os.makedirs('screenshots', exist_ok=True)

def take_screenshot(filename, prepare_fn):
    g = Tetris(ai_mode=False)
    g.root.attributes('-topmost', True)  # force window on top
    g.root.update()
    
    # Populate stats
    g.score = 12500
    g.level = 5
    g.lines = 42
    g.current = Piece('T')
    g.current.x = 4
    g.current.y = GRID_HEIGHT - 9
    g.next = Piece('I')
    
    # Apply prepare function (populate board, set menu, etc.)
    prepare_fn(g)
    
    # Force multiple renders
    for _ in range(10):
        g._draw()
        g.root.update()
    g.root.update_idletasks()
    time.sleep(1.0)
    g.root.update()
    
    # Get ACCURATE window geometry
    g.root.update_idletasks()
    x = g.root.winfo_rootx()
    y = g.root.winfo_rooty()
    w = g.root.winfo_width()
    h = g.root.winfo_height()
    
    print(f"  Window at ({x},{y}) {w}x{h}")
    
    # Bring to front and capture
    g.root.lift()
    g.root.attributes('-topmost', True)
    g.root.update()
    time.sleep(0.5)
    
    img = ImageGrab.grab(bbox=(x, y, x + w, y + h), all_screens=True)
    img.save(filename)
    print(f"  Saved {filename}")
    
    g.root.destroy()
    time.sleep(0.2)


# Screenshot 1: Manual play
def prep_manual(g):
    # Fill rows with blocks for visual interest
    for x in range(GRID_WIDTH):
        if x not in (2, 5, 8):
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

take_screenshot('screenshots/manual_play.png', prep_manual)

# Screenshot 2: Menu
def prep_menu(g):
    prep_manual(g)
    g.in_menu = True

take_screenshot('screenshots/menu.png', prep_menu)

# Screenshot 3: Game over
def prep_gameover(g):
    prep_manual(g)
    g.game_over = True
    g.score = 68000
    g.lines = 112

take_screenshot('screenshots/game_over.png', prep_gameover)

print("Done!")

