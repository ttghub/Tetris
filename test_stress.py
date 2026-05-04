"""Stress test: simulate game play to find crash scenarios"""
import sys, os, traceback
sys.path.insert(0, os.path.dirname(__file__))

import random
random.seed(123)

FONT_FAMILY = 'Consolas'
from tetris import Tetris, GRID_WIDTH, GRID_HEIGHT

class MockCanvas:
    def __init__(self):
        self.items = []
    def delete(self, tag):
        self.items.clear()
    def create_rectangle(self, *a, **kw):
        self.items.append(('rect', a, kw))
        return len(self.items)
    def create_line(self, *a, **kw):
        self.items.append(('line', a, kw))
        return len(self.items)
    def create_text(self, *a, **kw):
        self.items.append(('text', a, kw))
        return len(self.items)

class MockRoot:
    def __init__(self):
        self.after_ids = []
    def after(self, ms, cb):
        tid = len(self.after_ids)
        self.after_ids.append(tid)
        return tid
    def after_cancel(self, tid):
        pass

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
    g.bag = []
    g.fall_speed = 800
    g.fall_counter = 0
    g._tick_id = None
    g.current = g._next_piece()
    g.next = g._next_piece()
    return g

errors = []

def try_call(fn, name):
    try:
        fn()
        return True
    except Exception as e:
        errors.append((name, str(e), traceback.format_exc()))
        return False

print("=== Stress Testing Tetris Game Logic ===")

# Test 1: Spam soft_drop
g = make_game()
print("\n[Test 1] Spamming soft_drop (30 times)...")
for i in range(30):
    if g.game_over:
        break
    if not try_call(g.soft_drop, f"soft_drop #{i}"):
        break

# Test 2: Spam hard_drop + check state
g2 = make_game()
print("[Test 2] Alternating hard_drop + soft_drop...")
for i in range(20):
    if g2.game_over:
        break
    if i % 3 == 0:
        if not try_call(g2.hard_drop, f"hard_drop #{i}"):
            break
    else:
        if not try_call(g2.soft_drop, f"soft_drop #{i}"):
            break

# Test 3: Rotate while falling
g3 = make_game()
print("[Test 3] Rotate + soft_drop combo...")
for i in range(30):
    if g3.game_over:
        break
    try_call(g3.rotate_piece, f"rotate #{i}")
    if not try_call(g3.soft_drop, f"soft_drop #{i}"):
        break

# Test 4: Rapid left/right + down
g4 = make_game()
print("[Test 4] Left/Right/Down spam...")
for i in range(50):
    if g4.game_over:
        break
    actions = [
        (g4.move, (-1, 0)),
        (g4.move, (1, 0)),
        (g4.soft_drop, ()),
        (g4.rotate_piece, ()),
    ]
    for fn, args in actions:
        if g4.game_over:
            break
        if args:
            try_call(lambda: fn(*args), f"{fn.__name__} {args} #{i}")
        else:
            try_call(fn, f"{fn.__name__} #{i}")

# Test 5: Lock piece at edge cases
g5 = make_game()
print("[Test 5] Edge: move to left edge, drop, rotate, drop...")
for i in range(10):
    try_call(lambda: g5.move(-1, 0), f"move left #{i}")
g5.hard_drop()

# Test 6: Fill bottom rows then soft_drop
g6 = make_game()
print("[Test 6] Near-full board soft_drop...")
for row in range(GRID_HEIGHT - 3, GRID_HEIGHT):
    for x in range(GRID_WIDTH):
        g6.board[row][x] = 'S'
for i in range(20):
    if g6.game_over:
        break
    try_call(g6.soft_drop, f"soft_drop #{i}")

# Test 7: Game over reset cycle
g7 = make_game()
print("[Test 7] Game over -> reset -> play cycle x5...")
for cycle in range(5):
    g7.reset()
    for i in range(10):
        if g7.game_over:
            break
        try_call(g7.soft_drop, f"c{cycle} soft_drop #{i}")

# Test 8: _step direct call loop
g8 = make_game()
print("[Test 8] Direct _step() calls to simulate tick...")
for i in range(100):
    if g8.game_over:
        break
    if not try_call(g8._step, f"_step #{i}"):
        break

# Test 9: Ghost calculation stress
g9 = make_game()
print("[Test 9] Ghost Y calculation stress...")
for i in range(50):
    if g9.game_over:
        break
    try_call(lambda: g9._ghost_y(), f"ghost_y #{i}")
    try_call(g9.soft_drop, f"soft_drop #{i}")

# Test 10: Lock with full lines + ghost
g10 = make_game()
print("[Test 10] Hard drop onto full rows...")
for row in range(GRID_HEIGHT - 5, GRID_HEIGHT):
    for x in range(GRID_WIDTH):
        if (x + row) % 2 == 0:
            g10.board[row][x] = 'J'
for i in range(10):
    if g10.game_over:
        break
    try_call(g10.hard_drop, f"hard_drop #{i}")

# Summary
print(f"\n{'='*50}")
if errors:
    print(f"FAILED: {len(errors)} error(s) found:")
    for name, msg, tb in errors:
        print(f"\n  [{name}]")
        print(f"  Error: {msg}")
        print(f"  Trace:")
        for line in tb.strip().split('\n')[-3:]:
            print(f"    {line}")
else:
    print("ALL TESTS PASSED - No exceptions raised")

sys.exit(0 if not errors else 1)
