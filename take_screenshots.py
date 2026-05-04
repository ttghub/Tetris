"""Take screenshots of Tetris game for README"""
import sys, os, time, ctypes, tkinter as tk
from ctypes import wintypes
from PIL import ImageGrab

# Fix DPI scaling mismatch
ctypes.windll.user32.SetProcessDPIAware()

sys.path.insert(0, os.path.dirname(__file__))
from tetris import Tetris, Piece, GRID_WIDTH, GRID_HEIGHT

os.makedirs('screenshots', exist_ok=True)

def get_client_rect(hwnd):
    """Get accurate client area screen coordinates via Windows API."""
    rect = wintypes.RECT()
    ctypes.windll.user32.GetClientRect(hwnd, ctypes.byref(rect))
    pt = wintypes.POINT(0, 0)
    ctypes.windll.user32.ClientToScreen(hwnd, ctypes.byref(pt))
    return pt.x, pt.y, rect.right, rect.bottom

def grab_window(root):
    """Screenshot the tkinter window client area accurately."""
    hwnd = ctypes.windll.user32.FindWindowW(None, root.title())
    if not hwnd:
        hwnd = int(root.frame(), 16)
    x, y, w, h = get_client_rect(hwnd)
    return ImageGrab.grab(bbox=(x, y, x + w, y + h))

def take_screenshot(filename, prepare_fn):
    g = Tetris(ai_mode=False)
    g.root.attributes('-topmost', True)
    g.root.update()

    g.score = 12500
    g.level = 5
    g.lines = 42
    g.current = Piece('T')
    g.current.x = 4
    g.current.y = GRID_HEIGHT - 9
    g.next = Piece('I')

    prepare_fn(g)

    for _ in range(10):
        g._draw()
        g.root.update()
    g.root.update_idletasks()
    time.sleep(1.0)
    g.root.lift()
    g.root.attributes('-topmost', True)
    g.root.update()
    time.sleep(0.5)

    img = grab_window(g.root)
    img.save(filename)
    print(f"  Saved {filename} ({img.width}x{img.height})")

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

