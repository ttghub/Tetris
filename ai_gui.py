"""AI bot playing in real GUI - visual demo"""
import sys, os, traceback, tkinter as tk
sys.path.insert(0, os.path.dirname(__file__))
from tetris import Tetris, Piece, SHAPES, GRID_WIDTH, GRID_HEIGHT

print("Starting AI Tetris Bot (GUI)...", flush=True)
g = Tetris()

def board_height(board):
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

def evaluate_board(board):
    height = board_height(board)
    holes = count_holes(board)
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
    return height * 10 + holes * 25 + bumpiness * 2

def can_place(board, piece):
    for x, y in piece.positions():
        if x < 0 or x >= GRID_WIDTH or y >= GRID_HEIGHT:
            return False
        if y >= 0 and board[y][x] is not None:
            return False
    return True

def drop_to_bottom(board, piece):
    while True:
        piece.y += 1
        if not can_place(board, piece):
            piece.y -= 1
            return

def clear_and_eval(board):
    new = [row[:] for row in board]
    full = [r for r in range(GRID_HEIGHT) if all(new[r][c] is not None for c in range(GRID_WIDTH))]
    for row in sorted(full, reverse=True):
        del new[row]
    for _ in range(len(full)):
        new.insert(0, [None] * GRID_WIDTH)
    return new, len(full)

def find_best(game):
    piece = game.current
    best_score = float('inf')
    best_rot, best_x = 0, piece.x
    
    for rot in range(len(piece.shapes)):
        tp = Piece(piece.shape_name)
        tp.rotation = rot
        tp.blocks = [list(b) for b in piece.shapes[rot]]
        min_x = max(0, -min(bx for bx, _ in tp.blocks))
        max_x = min(GRID_WIDTH - 1, GRID_WIDTH - 1 - max(bx for bx, _ in tp.blocks))
        for x in range(min_x, max_x + 1):
            tp.x, tp.y = x, 0
            if not can_place(game.board, tp):
                continue
            dp = Piece(piece.shape_name)
            dp.rotation = rot
            dp.blocks = [list(b) for b in piece.shapes[rot]]
            dp.x, dp.y = x, 0
            drop_to_bottom(game.board, dp)
            test_board = [row[:] for row in game.board]
            for bx, by in dp.positions():
                if by < 0 or by >= GRID_HEIGHT:
                    break
                test_board[by][bx] = dp.shape_name
            else:
                test_board, lines = clear_and_eval(test_board)
                s = evaluate_board(test_board) - lines * 500
                if s < best_score:
                    best_score, best_rot, best_x = s, rot, x
    return best_rot, best_x

def ai_step():
    if g.game_over:
        print(f"Game Over! Score={g.score} Lines={g.lines}", flush=True)
        g.root.after(2000, g.reset)
        g.root.after(2500, ai_step)
        return
    
    rot, x = find_best(g)
    for _ in range(rot):
        g.rotate_piece()
        g.root.update()
    dx = x - g.current.x
    if dx < 0:
        for _ in range(-dx):
            g.move(-1, 0)
    elif dx > 0:
        for _ in range(dx):
            g.move(1, 0)
    g.hard_drop()
    g.root.update()
    g.root.after(50, ai_step)

g.root.after(500, ai_step)
g.root.mainloop()
