"""单元测试：只测核心逻辑，不依赖 tkinter GUI"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

FONT_FAMILY = 'Consolas'
import random
random.seed(42)

from tetris import Piece, SHAPES, GRID_WIDTH, GRID_HEIGHT, COLORS

# ---- Piece tests ----
def test_piece_init():
    p = Piece('I')
    assert p.shape_name == 'I'
    assert p.rotation == 0
    assert p.x == GRID_WIDTH // 2
    assert p.y == 1
    assert len(p.blocks) == 4

def test_piece_positions():
    p = Piece('O')
    pos = p.positions()
    cx, cy = GRID_WIDTH // 2, 1
    expected = [(cx, cy), (cx+1, cy), (cx, cy+1), (cx+1, cy+1)]
    assert sorted(pos) == sorted(expected)

def test_piece_rotate():
    p = Piece('I')
    old = p.rotation
    p.rotate()
    assert p.rotation != old
    assert len(p.blocks) == 4

def test_piece_rotate_all_shapes():
    for name in SHAPES:
        p = Piece(name)
        for _ in range(len(p.shapes)):
            p.rotate()
        assert p.rotation == 0

def test_piece_positions_format():
    p = Piece('T')
    for x, y in p.positions():
        assert isinstance(x, int)
        assert isinstance(y, int)

# ---- Board logic tests (mocked without tkinter) ----
class MockCanvas:
    def delete(self, tag): pass
    def create_rectangle(self, *a, **kw): pass
    def create_line(self, *a, **kw): pass
    def create_text(self, *a, **kw): pass

class MockRoot:
    def after(self, ms, cb): return 1
    def after_cancel(self, tid): pass

class MockEvent:
    def __init__(self, keysym):
        self.keysym = keysym

from tetris import Tetris

def make_game():
    g = Tetris.__new__(Tetris)
    g.root = MockRoot()
    g.canvas = MockCanvas()
    g.origin_x = 20
    g.origin_y = 20
    g.play_w = GRID_WIDTH * 28
    g.play_h = GRID_HEIGHT * 28
    g.board = [[None] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
    g.score = 0
    g.level = 1
    g.lines = 0
    g.game_over = False
    g.in_menu = False
    g.bag = []
    g.fall_speed = 800
    g.fall_counter = 0
    g._tick_id = None
    g.current = g._next_piece()
    g.next = g._next_piece()
    return g


def test_valid_empty():
    g = make_game()
    assert g._valid(g.current.positions()) == True

def test_valid_out_of_bounds_left():
    g = make_game()
    g.current.x = -5
    assert g._valid(g.current.positions()) == False

def test_valid_out_of_bounds_right():
    g = make_game()
    g.current.x = GRID_WIDTH + 5
    assert g._valid(g.current.positions()) == False

def test_valid_out_of_bounds_bottom():
    g = make_game()
    g.current.y = GRID_HEIGHT
    assert g._valid(g.current.positions()) == False

def test_move_left():
    g = make_game()
    old_x = g.current.x
    g.move(-1, 0)
    assert g.current.x == old_x - 1

def test_move_left_blocked():
    g = make_game()
    g.current.x = 0
    assert g.move(-1, 0) == False
    assert g.current.x == 0

def test_move_down():
    g = make_game()
    old_y = g.current.y
    g.move(0, 1)
    assert g.current.y == old_y + 1

def test_move_down_blocked():
    g = make_game()
    g.current.y = GRID_HEIGHT - 2
    for x in range(GRID_WIDTH):
        g.board[GRID_HEIGHT - 1][x] = 'I'
    assert g.move(0, 1) == False

def test_clear_lines_single():
    g = make_game()
    for x in range(GRID_WIDTH):
        g.board[GRID_HEIGHT - 1][x] = 'I'
    g._clear_lines()
    assert all(g.board[GRID_HEIGHT - 1][c] is None for c in range(GRID_WIDTH))
    assert g.lines == 1
    assert g.score == 100

def test_clear_lines_multiple():
    g = make_game()
    for row in [GRID_HEIGHT - 1, GRID_HEIGHT - 2, GRID_HEIGHT - 3]:
        for x in range(GRID_WIDTH):
            g.board[row][x] = 'T'
    g._clear_lines()
    assert g.lines == 3
    assert g.score == 500  # 3 lines = 500
    assert all(g.board[GRID_HEIGHT - 1][c] is None for c in range(GRID_WIDTH))

def test_clear_lines_tetris():
    g = make_game()
    for row in [GRID_HEIGHT - 1, GRID_HEIGHT - 2, GRID_HEIGHT - 3, GRID_HEIGHT - 4]:
        for x in range(GRID_WIDTH):
            g.board[row][x] = 'S'
    g._clear_lines()
    assert g.lines == 4
    assert g.score == 800
    for c in range(GRID_WIDTH):
        assert g.board[GRID_HEIGHT - 1][c] is None
        assert g.board[GRID_HEIGHT - 4][c] is None

def test_clear_lines_respect_order():
    """Test that non-contiguous full rows are cleared correctly (Bug 1 fix verification)"""
    g = make_game()
    for row in [0, 5, 10, 15, 19]:
        for x in range(GRID_WIDTH):
            g.board[row][x] = 'J'
    g._clear_lines()
    assert g.lines == 5
    assert g.score == 1000  # 5 * 200
    assert all(g.board[0][c] is None for c in range(GRID_WIDTH))

def test_score_formula_level():
    g = make_game()
    g.level = 5
    for x in range(GRID_WIDTH):
        g.board[GRID_HEIGHT - 1][x] = 'I'
    g._clear_lines()
    assert g.score == 100 * 5  # 100 * level

def test_lock_spawn_valid():
    """Lock completes without crashing and toggles game_over if spawn blocked."""
    g = make_game()
    assert not g.game_over
    # Lock with known piece: fill the spawn area completely so next piece
    # definitely overlaps, causing game_over
    cx = GRID_WIDTH // 2
    for dy in range(3):
        for dx in range(-2, 3):
            ny = 1 + dy
            nx = cx + dx
            if 0 <= ny < GRID_HEIGHT and 0 <= nx < GRID_WIDTH:
                g.board[ny][nx] = 'I'
    g._lock()
    assert g.game_over == True

def test_lock_spawn_gameover():
    """Lock when new piece's spawn position is blocked"""
    g = make_game()
    cx = GRID_WIDTH // 2
    g.board[1][cx] = 'I'
    g.board[1][cx + 1] = 'I'
    g._lock()
    assert g.game_over

def test_hard_drop():
    g = make_game()
    g.hard_drop()
    y_positions = [y for _, y in g.current.positions()]
    assert g.game_over == False

def test_next_piece_7bag():
    """A fresh bag contains 7 unique pieces (one of each type)."""
    g = make_game()
    g.bag = []  # reset bag to get a fresh full bag
    seen = set()
    for _ in range(7):
        p = g._next_piece()
        seen.add(p.shape_name)
    assert len(seen) == 7  # one of each type

def test_reset():
    g = make_game()
    g.score = 999
    g.level = 99
    g.lines = 500
    g.game_over = True
    g.reset()
    assert g.score == 0
    assert g.level == 1
    assert g.lines == 0
    assert not g.game_over
    assert g.fall_speed == 800

def test_key_r_restarts():
    g = make_game()
    g.game_over = True
    g.score = 5000
    g._on_key(MockEvent('r'))
    assert not g.game_over
    assert g.score == 0

def test_key_space_during_gameover():
    g = make_game()
    g.game_over = True
    saved = g.current.shape_name if g.current else None
    g._on_key(MockEvent('space'))
    assert g.game_over == True  # hard_drop should be skipped

def test_ghost_y():
    g = make_game()
    gy = g._ghost_y()
    assert isinstance(gy, int)
    assert gy >= 0

# ---- Run all tests ----
if __name__ == '__main__':
    tests = [fn for name, fn in sorted(globals().items())
             if name.startswith('test_') and callable(fn)]
    passed = 0
    for fn in tests:
        try:
            fn()
            print(f'  PASS  {fn.__name__}')
            passed += 1
        except Exception as e:
            print(f'  FAIL  {fn.__name__}: {e}')
    print(f'\n{passed}/{len(tests)} tests passed')
    if passed != len(tests):
        sys.exit(1)
