"""
AI bot that plays Tetris autonomously to find bugs.
Evaluates all placements, picks the best one, executes via direct game API.
Runs thousands of games and checks for crashes and state corruption.
"""
import sys, os, traceback, random
sys.path.insert(0, os.path.dirname(__file__))

from tetris import Tetris, Piece, SHAPES, GRID_WIDTH, GRID_HEIGHT, COLORS
import copy

random.seed(12345)

class MockCanvas:
    def delete(self, tag): pass
    def create_rectangle(self, *a, **kw): pass
    def create_line(self, *a, **kw): pass
    def create_text(self, *a, **kw): pass

class MockRoot:
    def __init__(self):
        self.after_ids = []
    def after(self, ms, cb):
        tid = len(self.after_ids)
        self.after_ids.append(tid)
        return tid
    def after_cancel(self, tid): pass

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

def clone_game(g):
    """Deep clone game state."""
    c = Tetris.__new__(Tetris)
    c.root = g.root
    c.canvas = g.canvas
    c.origin_x = g.origin_x
    c.origin_y = g.origin_y
    c.play_w = g.play_w
    c.play_h = g.play_h
    c.board = [row[:] for row in g.board]
    c.score = g.score
    c.level = g.level
    c.lines = g.lines
    c.game_over = g.game_over
    c.bag = list(g.bag)
    c.fall_speed = g.fall_speed
    c.fall_counter = g.fall_counter
    c._tick_id = None
    
    # Clone current piece
    c.current = Piece(g.current.shape_name)
    c.current.rotation = g.current.rotation
    c.current.blocks = [list(b) for b in g.current.blocks]
    c.current.x = g.current.x
    c.current.y = g.current.y
    
    # Clone next piece
    c.next = Piece(g.next.shape_name)
    c.next.rotation = g.next.rotation
    c.next.blocks = [list(b) for b in g.next.blocks]
    c.next.x = g.next.x
    c.next.y = g.next.y
    
    return c

def board_height(board):
    """Max column height."""
    for y in range(GRID_HEIGHT):
        if any(board[y][x] is not None for x in range(GRID_WIDTH)):
            return GRID_HEIGHT - y
    return 0

def count_holes(board):
    holes = 0
    for x in range(GRID_WIDTH):
        block_found = False
        for y in range(GRID_HEIGHT):
            if board[y][x] is not None:
                block_found = True
            elif block_found:
                holes += 1
    return holes

def count_wells(board):
    """Count deep wells (empty columns flanked by blocks)."""
    wells = 0
    for x in range(GRID_WIDTH):
        for y in range(GRID_HEIGHT - 1, -1, -1):
            if board[y][x] is not None:
                continue
            left_wall = x == 0 or board[y][x-1] is not None
            right_wall = x == GRID_WIDTH - 1 or board[y][x+1] is not None
            if left_wall and right_wall:
                wells += 1
    return wells

def can_place(board, piece):
    """Check if piece can be placed at its current position."""
    for x, y in piece.positions():
        if x < 0 or x >= GRID_WIDTH or y >= GRID_HEIGHT:
            return False
        if y >= 0 and board[y][x] is not None:
            return False
    return True

def drop_piece(board, piece):
    """Drop piece to lowest valid position, return modified y."""
    while True:
        piece.y += 1
        if not can_place(board, piece):
            piece.y -= 1
            return piece.y

def place_piece(board, piece):
    """Lock piece onto board, return new board."""
    new_board = [row[:] for row in board]
    for x, y in piece.positions():
        if y < 0 or y >= GRID_HEIGHT:
            return None  # Game over
        new_board[y][x] = piece.shape_name
    return new_board

def clear_lines(board):
    """Clear full lines, return (new_board, lines_cleared)."""
    new_board = [row[:] for row in board]
    full = [r for r in range(GRID_HEIGHT)
            if all(new_board[r][c] is not None for c in range(GRID_WIDTH))]
    for row in sorted(full, reverse=True):
        del new_board[row]
    for _ in range(len(full)):
        new_board.insert(0, [None] * GRID_WIDTH)
    return new_board, len(full)

def evaluate_board(board):
    """Heuristic: lower is better."""
    height = board_height(board)
    holes = count_holes(board)
    wells = count_wells(board)
    bumpiness = 0
    heights = []
    for x in range(GRID_WIDTH):
        for y in range(GRID_HEIGHT):
            if board[y][x] is not None:
                heights.append(GRID_HEIGHT - y)
                break
        else:
            heights.append(0)
    for i in range(len(heights) - 1):
        bumpiness += abs(heights[i] - heights[i+1])
    
    return height * 10 + holes * 25 + bumpiness * 2 + wells * 15

def find_best_move(game):
    """Find best placement for current piece. Returns (rotations, left_moves)."""
    piece = game.current
    best_score = float('inf')
    best_rot = 0
    best_x = piece.x
    
    for rot in range(len(piece.shapes)):
        # Test piece at this rotation
        test_piece = Piece(piece.shape_name)
        test_piece.rotation = rot
        test_piece.blocks = [list(b) for b in piece.shapes[rot]]
        
        # Find min/max valid x
        min_x = max(0, -min(bx for bx, _ in test_piece.blocks))
        max_x = min(GRID_WIDTH - 1, GRID_WIDTH - 1 - max(bx for bx, _ in test_piece.blocks))
        
        for x in range(min_x, max_x + 1):
            test_piece.x = x
            test_piece.y = 0
            
            if not can_place(game.board, test_piece):
                continue
            
            # Drop to bottom
            dropped = Piece(piece.shape_name)
            dropped.rotation = rot
            dropped.blocks = [list(b) for b in piece.shapes[rot]]
            dropped.x = x
            dropped.y = 0
            drop_piece(game.board, dropped)
            
            # Simulate placement
            test_board = place_piece(game.board, dropped)
            if test_board is None:
                continue
            test_board, lines = clear_lines(test_board)
            
            score = evaluate_board(test_board) - lines * 500
            if score < best_score:
                best_score = score
                best_rot = rot
                best_x = x
    
    return best_rot, best_x

def execute_move(game, target_rot, target_x):
    """Execute the move on the real game, returning True on success."""
    # Rotate to target
    for _ in range(target_rot):
        game.rotate_piece()
    
    # Move to target x
    dx = target_x - game.current.x
    if dx < 0:
        for _ in range(-dx):
            game.move(-1, 0)
    elif dx > 0:
        for _ in range(dx):
            game.move(1, 0)
    
    # Hard drop
    game.hard_drop()
    return not game.game_over

def verify_state(game):
    """Verify game state consistency."""
    errors = []
    
    # Board dimensions
    if len(game.board) != GRID_HEIGHT:
        errors.append(f"Board height is {len(game.board)}, expected {GRID_HEIGHT}")
    
    for row in game.board:
        if len(row) != GRID_WIDTH:
            errors.append(f"Board row width is {len(row)}, expected {GRID_WIDTH}")
            break
    
    # Score consistency
    if game.score < 0:
        errors.append(f"Negative score: {game.score}")
    
    # Level consistency
    expected_level = game.lines // 10 + 1
    if game.level != expected_level:
        errors.append(f"Level {game.level} != expected {expected_level} (lines={game.lines})")
    
    # Fall speed
    expected_speed = max(80, 800 - (game.level - 1) * 60)
    if game.fall_speed != expected_speed:
        errors.append(f"Fall speed {game.fall_speed} != expected {expected_speed}")
    
    # Current piece validity
    if not game.game_over:
        if not game._valid(game.current.positions()):
            errors.append("Current piece at invalid position")
    
    # Piece attributes
    if game.current.x < 0 or game.current.x >= GRID_WIDTH:
        errors.append(f"Current piece x={game.current.x} out of bounds")
    
    return errors

def run_bot_game(max_moves=500):
    """Run a single bot game, return (moves, score, lines, errors)."""
    g = make_game()
    game_errors = []
    moves = 0
    
    for _ in range(max_moves):
        if g.game_over:
            break
        
        try:
            rot, x = find_best_move(g)
        except Exception as e:
            game_errors.append(f"AI find_best_move error: {e}")
            break
        
        try:
            execute_move(g, rot, x)
        except Exception as e:
            game_errors.append(f"execute_move error: {e}")
            game_errors.append(traceback.format_exc())
            break
        
        moves += 1
        
        # Verify state every 10 moves
        if moves % 10 == 0:
            errors = verify_state(g)
            if errors:
                game_errors.extend(errors)
                break
    
    return moves, g.score, g.lines, game_errors

# ---- Run multiple bot games ----
print("=" * 60)
print("AI BOT TETRIS TEST - Running 100 games...")
print("=" * 60)

total_moves = 0
total_score = 0
total_lines = 0
total_errors = []
crash_count = 0

for game_num in range(1, 101):
    try:
        moves, score, lines, errors = run_bot_game(max_moves=300)
        total_moves += moves
        total_score += score
        total_lines += lines
        
        if errors:
            total_errors.append((game_num, errors))
            crash_count += 1
            print(f"  Game {game_num:3d}: {moves:3d} moves, {score:5d} pts, {lines:3d} lines - {len(errors)} ERROR(S)")
            for e in errors:
                print(f"    ! {e}")
        else:
            print(f"  Game {game_num:3d}: {moves:3d} moves, {score:5d} pts, {lines:3d} lines OK")
            
    except BaseException as e:
        crash_count += 1
        total_errors.append((game_num, [f"CRASH: {type(e).__name__}: {e}"]))
        print(f"  Game {game_num:3d}: HARD CRASH - {type(e).__name__}: {e}")
        traceback.print_exc()

print(f"\n{'='*60}")
print(f"RESULTS OVER 100 GAMES:")
print(f"  Total moves:  {total_moves}")
print(f"  Avg moves:    {total_moves / 100:.1f}")
print(f"  Total score:  {total_score}")
print(f"  Total lines:  {total_lines}")
print(f"  Crashes:      {crash_count}/100")
print(f"  Success rate: {100 - crash_count}%")
print(f"  Error games:  {len(total_errors)}")

if total_errors:
    print(f"\nERROR GAMES ({len(total_errors)}):")
    for game_num, errors in total_errors:
        print(f"  Game {game_num}:")
        for e in errors:
            print(f"    - {e}")
    sys.exit(1)
else:
    print("\nALL 100 GAMES PASSED - No bugs found!")
    sys.exit(0)
