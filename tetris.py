import tkinter as tk
import random
import traceback
import logging
import sys
import datetime
import atexit

LOG_FILE = f'tetris_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
try:
    _log_fh = open(LOG_FILE, 'w', encoding='utf-8', buffering=1)
except Exception:
    _log_fh = sys.stderr

def _log(msg):
    try:
        ts = datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]
        line = f'{ts} {msg}\n'
        _log_fh.write(line)
        _log_fh.flush()
        print(line, end='', file=sys.stderr, flush=True)
    except Exception:
        pass  # never let logging crash the game

atexit.register(lambda: _log('===== Process exited ====='))

def _crash_handler(typ, val, tb):
    if _log_fh:
        _log_fh.write(f'!!! UNHANDLED EXCEPTION: {typ.__name__}: {val}\n')
        traceback.print_exception(typ, val, tb, file=_log_fh)
        _log_fh.flush()
    traceback.print_exception(typ, val, tb)
    sys.__excepthook__(typ, val, tb)

sys.excepthook = _crash_handler

# Also set up standard logging for backup
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    stream=_log_fh,
)

FONT_FAMILY = 'Consolas'  # available on Windows; fallback to system default on other OS

# 常量
GRID_WIDTH = 10
GRID_HEIGHT = 20
CELL = 28
PREVIEW_CELL = 24
BG = '#0a0a1e'
GRID_COLOR = '#323232'
BORDER = '#464646'
TEXT = '#c8c8c8'

COLORS = {
    'I': '#00ffff', 'O': '#ffff00', 'T': '#800080',
    'S': '#00ff00', 'Z': '#ff0000', 'J': '#0000ff', 'L': '#ffa500',
}

SHAPES = {
    'I': [[(0, -1), (0, 0), (0, 1), (0, 2)],
          [(-1, 0), (0, 0), (1, 0), (2, 0)]],
    'O': [[(0, 0), (0, 1), (1, 0), (1, 1)]],
    'T': [[(-1, 0), (0, 0), (0, 1), (1, 0)],
          [(0, -1), (-1, 0), (0, 0), (0, 1)],
          [(-1, 0), (0, 0), (0, -1), (1, 0)],
          [(0, -1), (0, 0), (1, 0), (0, 1)]],
    'S': [[(-1, 0), (-1, 1), (0, 0), (0, -1)],
          [(-1, -1), (0, -1), (0, 0), (1, 0)]],
    'Z': [[(-1, -1), (-1, 0), (0, 0), (0, 1)],
          [(-1, 0), (0, 0), (0, -1), (1, -1)]],
    'J': [[(-1, -1), (-1, 0), (0, 0), (1, 0)],
          [(0, -1), (0, 0), (-1, 1), (0, 1)],
          [(-1, 0), (0, 0), (1, 0), (1, 1)],
          [(0, -1), (0, 0), (1, -1), (0, 1)]],
    'L': [[(-1, 0), (0, 0), (1, 0), (1, -1)],
          [(0, -1), (0, 0), (0, 1), (1, 1)],
          [(-1, 1), (-1, 0), (0, 0), (1, 0)],
          [(-1, -1), (0, -1), (0, 0), (0, 1)]],
}


class Piece:
    def __init__(self, shape_name):
        self.shape_name = shape_name
        self.rotation = 0
        self.shapes = SHAPES[shape_name]
        self.blocks = [list(b) for b in self.shapes[self.rotation]]
        self.x = GRID_WIDTH // 2
        self.y = 1

    def rotate(self, direction=1):
        old = self.rotation
        self.rotation = (self.rotation + direction) % len(self.shapes)
        self.blocks = [list(b) for b in self.shapes[self.rotation]]
        return old

    def positions(self):
        return [(self.x + bx, self.y + by) for bx, by in self.blocks]


class Tetris:
    def __init__(self, ai_mode=False):
        self.ai_mode = ai_mode
        self.root = tk.Tk()
        self.root.title('Tetris' if not ai_mode else 'Tetris - AI Mode')
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        self.root.report_callback_exception = self._handle_exception

        play_w = GRID_WIDTH * CELL
        play_h = GRID_HEIGHT * CELL
        side_w = 140
        canvas_w = play_w + side_w + 40
        canvas_h = play_h + 60

        self.canvas = tk.Canvas(
            self.root, width=canvas_w, height=canvas_h,
            bg=BG, highlightthickness=0
        )
        self.canvas.pack(padx=10, pady=10)

        self.origin_x = 20
        self.origin_y = 20
        self.play_w = play_w
        self.play_h = play_h

        self.board = [[None] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
        self.score = 0
        self.level = 1
        self.lines = 0
        self.game_over = False
        self.in_menu = False
        self.bag = []
        self.fall_speed = 800
        self.fall_counter = 0

        self.current = self._next_piece()
        self.next = self._next_piece()

        self.root.bind('<Key>', self._on_key)

        self._tick_id = None
        self._ai_tick_id = None
        self.ai_speed = 400  # ms between AI moves (tunable: 100-800)
        self._draw()
        self._tick()

        if self.ai_mode:
            self.ai_move_count = 0
            self._ai_tick_id = self.root.after(500, self._ai_step)
            self.root.title('Tetris - AI Mode (A=Manual)')
        else:
            self.root.title('Tetris - Manual (A=AI)')

        _log(f'[START] mode={"AI" if ai_mode else "Manual"} piece={self.current.shape_name}')

    def toggle_ai(self):
        self.ai_mode = not self.ai_mode
        if self.ai_mode:
            self.root.title('Tetris - AI Mode (A=Manual)')
            self._ai_tick_id = self.root.after(300, self._ai_step)
            _log('[MODE] switched to AI')
        else:
            self.root.title('Tetris - Manual (A=AI)')
            if self._ai_tick_id is not None:
                self.root.after_cancel(self._ai_tick_id)
                self._ai_tick_id = None
            _log('[MODE] switched to Manual')

    def _ai_step(self):
        if self.game_over:
            self._ai_tick_id = self.root.after(2000, self.reset)
            self._ai_tick_id = self.root.after(2500, self._ai_step)
            return
        try:
            rot, x = self._ai_find_best()
            for _ in range(rot):
                self.rotate_piece()
            dx = x - self.current.x
            if dx < 0:
                for _ in range(-dx):
                    self.move(-1, 0)
            elif dx > 0:
                for _ in range(dx):
                    self.move(1, 0)
            self.hard_drop()
            self.ai_move_count += 1
        except Exception:
            logging.error('AI step error', exc_info=True)
        self._ai_tick_id = self.root.after(self.ai_speed, self._ai_step)

    def _ai_find_best(self):
        piece = self.current
        best_score = float('inf')
        best_rot, best_x = 0, GRID_WIDTH // 2

        for rot in range(len(piece.shapes)):
            tp = Piece(piece.shape_name)
            tp.rotation = rot
            tp.blocks = [list(b) for b in piece.shapes[rot]]
            min_x = max(0, -min(bx for bx, _ in tp.blocks))
            max_x = min(GRID_WIDTH - 1, GRID_WIDTH - 1 - max(bx for bx, _ in tp.blocks))
            for x in range(min_x, max_x + 1):
                tp.x, tp.y = x, 1
                if not self._valid(tp.positions()):
                    continue
                dp = Piece(piece.shape_name)
                dp.rotation = rot
                dp.blocks = [list(b) for b in piece.shapes[rot]]
                dp.x, dp.y = x, 1
                self._ai_drop(dp)
                test_board = [row[:] for row in self.board]
                all_in = True
                for bx, by in dp.positions():
                    if by < 0 or by >= GRID_HEIGHT:
                        all_in = False
                        break
                    test_board[by][bx] = dp.shape_name
                if not all_in:
                    continue
                test_board, lines = self._ai_clear(test_board)
                s = self._ai_eval(test_board) - lines * 500
                if s < best_score:
                    best_score, best_rot, best_x = s, rot, x
        return best_rot, best_x

    def _ai_drop(self, piece):
        for _ in range(GRID_HEIGHT + 5):
            piece.y += 1
            if not self._valid(piece.positions()):
                piece.y -= 1
                return

    def _ai_clear(self, board):
        full = [r for r in range(GRID_HEIGHT)
                if all(board[r][c] is not None for c in range(GRID_WIDTH))]
        for row in sorted(full, reverse=True):
            del board[row]
        for _ in range(len(full)):
            board.insert(0, [None] * GRID_WIDTH)
        return board, len(full)

    def _ai_eval(self, board):
        height = 0
        for y in range(GRID_HEIGHT):
            if any(board[y][x] is not None for x in range(GRID_WIDTH)):
                height = GRID_HEIGHT - y
                break
        holes = 0
        for x in range(GRID_WIDTH):
            block_found = False
            for y in range(GRID_HEIGHT):
                if board[y][x] is not None:
                    block_found = True
                elif block_found:
                    holes += 1
        heights = []
        for x in range(GRID_WIDTH):
            for y in range(GRID_HEIGHT):
                if board[y][x] is not None:
                    heights.append(GRID_HEIGHT - y)
                    break
            else:
                heights.append(0)
        bumpiness = sum(abs(heights[i] - heights[i+1]) for i in range(len(heights) - 1))
        return height * 10 + holes * 25 + bumpiness * 2

    def _handle_exception(self, exc, val, tb):
        try:
            logging.error('Tk callback error', exc_info=(exc, val, tb))
        except Exception:
            pass
        try:
            traceback.print_exception(exc, val, tb)
        except Exception:
            print('Tk callback error (print failed)', file=sys.stderr)

    def _next_piece(self):
        if not self.bag:
            self.bag = list(SHAPES.keys())
            random.shuffle(self.bag)
        return Piece(self.bag.pop())

    def _valid(self, positions):
        return all(
            0 <= x < GRID_WIDTH and 0 <= y < GRID_HEIGHT and
            self.board[y][x] is None
            for x, y in positions
        )

    def move(self, dx, dy):
        new_x = self.current.x + dx
        new_y = self.current.y + dy
        positions = [(new_x + bx, new_y + by) for bx, by in self.current.blocks]
        if not self._valid(positions):
            return False
        self.current.x = new_x
        self.current.y = new_y
        return True

    def rotate_piece(self):
        new_rot = (self.current.rotation + 1) % len(self.current.shapes)
        new_blocks = [list(b) for b in self.current.shapes[new_rot]]
        kicks = [(1, 0), (-1, 0), (2, 0), (-2, 0)]

        for ox, oy in [(0, 0)] + kicks:
            tx = self.current.x + ox
            ty = self.current.y + oy
            positions = [(tx + bx, ty + by) for bx, by in new_blocks]
            if self._valid(positions):
                self.current.rotation = new_rot
                self.current.blocks = new_blocks
                self.current.x = tx
                self.current.y = ty
                self._draw()
                return
        self._draw()

    def soft_drop(self):
        if self.move(0, 1):
            self.score += 1
            self.fall_counter = 0
        self._draw()

    def hard_drop(self):
        if self.game_over:
            return
        while self.move(0, 1):
            self.score += 2
        self._lock()

    def _lock(self):
        for x, y in self.current.positions():
            self.board[y][x] = self.current.shape_name
        logging.debug(f'Locked {self.current.shape_name} at ({self.current.x},{self.current.y})')
        self._clear_lines()
        self.current = self.next
        self.next = self._next_piece()
        if not self._valid(self.current.positions()):
            self.game_over = True
            logging.info(f'GAME OVER - spawn blocked (score={self.score}, lines={self.lines})')
        self.fall_counter = 0
        self._draw()

    def _clear_lines(self):
        full = [r for r in range(GRID_HEIGHT)
                if all(self.board[r][c] is not None for c in range(GRID_WIDTH))]
        if not full:
            return
        n = len(full)
        self.lines += n
        for row in sorted(full, reverse=True):
            del self.board[row]
        for _ in range(n):
            self.board.insert(0, [None] * GRID_WIDTH)
        score_table = {1: 100, 2: 300, 3: 500, 4: 800}
        self.score += score_table.get(n, 200 * n) * self.level
        self.level = self.lines // 10 + 1
        self.fall_speed = max(80, 800 - (self.level - 1) * 60)
        _log(f'[CLEAR] {n} rows total={self.lines} score={self.score}')

    def _ghost_y(self):
        gy = self.current.y
        while True:
            gy += 1
            positions = [(self.current.x + bx, gy + by) for bx, by in self.current.blocks]
            if not self._valid(positions):
                return gy - 1

    def _adjust_color(self, hex_color, delta):
        h = hex_color.lstrip('#')
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        r = max(0, min(255, r + delta))
        g = max(0, min(255, g + delta))
        b = max(0, min(255, b + delta))
        return f'#{r:02x}{g:02x}{b:02x}'

    def _draw_block(self, gx, gy, color, ghost=False):
        x1 = self.origin_x + gx * CELL + 1
        y1 = self.origin_y + gy * CELL + 1
        x2 = x1 + CELL - 2
        y2 = y1 + CELL - 2

        inside = self._adjust_color(color, -40)
        if ghost:
            self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline=inside, stipple='gray25')
        else:
            self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline=inside, width=1)
            hl = self._adjust_color(color, 60)
            self.canvas.create_rectangle(x1 + 1, y1 + 1, x2 - 1, y1 + 3, fill=hl, outline='')
            self.canvas.create_rectangle(x1 + 1, y1 + 1, x1 + 3, y2 - 1, fill=hl, outline='')

    def _draw(self):
        try:
            self._do_draw()
        except Exception:
            logging.error('Draw error', exc_info=True)
            traceback.print_exc()

    def _do_draw(self):
        self.canvas.delete('all')

        # 游戏区域背景
        self.canvas.create_rectangle(
            self.origin_x, self.origin_y,
            self.origin_x + self.play_w, self.origin_y + self.play_h,
            fill='#0f0f23', outline=BORDER, width=2
        )

        # 网格线
        for x in range(GRID_WIDTH + 1):
            px = self.origin_x + x * CELL
            self.canvas.create_line(px, self.origin_y, px, self.origin_y + self.play_h, fill=GRID_COLOR)
        for y in range(GRID_HEIGHT + 1):
            py = self.origin_y + y * CELL
            self.canvas.create_line(self.origin_x, py, self.origin_x + self.play_w, py, fill=GRID_COLOR)

        # 已锁定方块
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                if self.board[y][x]:
                    self._draw_block(x, y, COLORS[self.board[y][x]])

        if not self.game_over:
            ghost_y = self._ghost_y()
            if ghost_y > self.current.y:
                for gx, gy in self.current.positions():
                    py_offset = gy - self.current.y
                    real_y = ghost_y + py_offset
                    if 0 <= gx < GRID_WIDTH and 0 <= real_y < GRID_HEIGHT and self.board[real_y][gx] is None:
                        self._draw_block(gx, real_y, COLORS[self.current.shape_name], ghost=True)

            # 当前方块
            for x, y in self.current.positions():
                if y >= 0:
                    self._draw_block(x, y, COLORS[self.current.shape_name])

        # 右侧信息面板
        px = self.origin_x + self.play_w + 15
        py = self.origin_y + 5

        self.canvas.create_text(px, py, text='SCORE', fill=TEXT, anchor='nw',
                                font=(FONT_FAMILY, 14, 'bold'))
        py += 20
        self.canvas.create_text(px, py, text=str(self.score), fill='white', anchor='nw',
                                font=(FONT_FAMILY, 13))
        py += 30
        self.canvas.create_text(px, py, text='LEVEL', fill=TEXT, anchor='nw',
                                font=(FONT_FAMILY, 14, 'bold'))
        py += 20
        self.canvas.create_text(px, py, text=str(self.level), fill='white', anchor='nw',
                                font=(FONT_FAMILY, 13))
        py += 30
        self.canvas.create_text(px, py, text='LINES', fill=TEXT, anchor='nw',
                                font=(FONT_FAMILY, 14, 'bold'))
        py += 20
        self.canvas.create_text(px, py, text=str(self.lines), fill='white', anchor='nw',
                                font=(FONT_FAMILY, 13))
        py += 35
        self.canvas.create_text(px, py, text='NEXT', fill=TEXT, anchor='nw',
                                font=(FONT_FAMILY, 15, 'bold'))
        py += 24

        # 预览框
        pbox_w = PREVIEW_CELL * 4 + 14
        pbox_h = PREVIEW_CELL * 6 + 21
        self.canvas.create_rectangle(px, py, px + pbox_w, py + pbox_h, fill='#141428', outline=BORDER)
        if not self.game_over:
            cx, cy = px + pbox_w // 2, py + pbox_h // 2
            for bx, by in self.next.shapes[0]:
                rx = cx + bx * PREVIEW_CELL
                ry = cy + by * PREVIEW_CELL
                self.canvas.create_rectangle(
                    rx, ry, rx + PREVIEW_CELL - 2, ry + PREVIEW_CELL - 2,
                    fill=COLORS[self.next.shape_name], outline=''
                )

        # 操作提示
        py = self.origin_y + self.play_h + 5
        hints = ['\u2190/\u2192: Move  \u2191: Rotate  \u2193: Soft Drop',
                 'Space: Hard Drop  R: Restart  A: AI Toggle  Esc: Quit']
        for h in hints:
            self.canvas.create_text(self.origin_x + 5, py, text=h, fill='#8c8ca0',
                                    anchor='nw', font=(FONT_FAMILY, 9))
            py += 16

        # 游戏结束
        if self.game_over:
            cx = self.origin_x + self.play_w // 2
            cy = self.origin_y + self.play_h // 2
            self.canvas.create_rectangle(
                self.origin_x, self.origin_y,
                self.origin_x + self.play_w, self.origin_y + self.play_h,
                fill='#000000', stipple='gray50'
            )
            self.canvas.create_text(cx, cy - 15, text='GAME OVER', fill='#ff5050',
                                    font=(FONT_FAMILY, 22, 'bold'))
            self.canvas.create_text(cx, cy + 20, text=f'Final Score: {self.score}', fill=TEXT,
                                    font=(FONT_FAMILY, 13))
            self.canvas.create_text(cx, cy + 45, text='Press R to Restart', fill=TEXT,
                                    font=(FONT_FAMILY, 11))

        if self.in_menu:
            cx = self.origin_x + self.play_w // 2
            cy = self.origin_y + self.play_h // 2
            self.canvas.create_rectangle(
                self.origin_x + 10, self.origin_y + 10,
                self.origin_x + self.play_w - 10, self.origin_y + self.play_h - 10,
                fill='#0a0a30', outline='#ffcc00', width=2
            )
            self.canvas.create_text(cx, cy - 60, text='TETRIS', fill='#ffcc00',
                                    font=(FONT_FAMILY, 28, 'bold'))
            self.canvas.create_text(cx, cy - 15, text='Select Mode', fill=TEXT,
                                    font=(FONT_FAMILY, 14))
            self.canvas.create_text(cx, cy + 25, text='M - Manual Play', fill='#5f5',
                                    font=(FONT_FAMILY, 13))
            self.canvas.create_text(cx, cy + 52, text='A - AI Play', fill='#55f',
                                    font=(FONT_FAMILY, 13))
            self.canvas.create_text(cx, cy + 79, text='Q - Quit', fill='#f55',
                                    font=(FONT_FAMILY, 11))
            self.canvas.create_text(cx, cy + 100, text='ESC - Resume', fill='#888',
                                    font=(FONT_FAMILY, 10))

    def _on_key(self, event):
        try:
            if not hasattr(event, 'keysym'):
                return
            _log(f'[EVT] keysym={event.keysym}')
            self._handle_key(event)
        except Exception as e:
            _log(f'[ERROR] Key handler: {type(e).__name__}: {e}')
            traceback.print_exc(file=_log_fh)
            _log_fh.flush()

    def _handle_key(self, event):
        _log(f'[KEY] {event.keysym}  piece={self.current.shape_name} pos=({self.current.x},{self.current.y})')
        if event.keysym in ('r', 'R'):
            self.in_menu = False
            self.reset()
            return
        if event.keysym == 'Escape':
            self.in_menu = True
            self._draw()
            return
        if self.in_menu:
            if event.keysym in ('q', 'Q'):
                self.root.destroy()
                return
            if event.keysym in ('m', 'M'):
                self.in_menu = False
                if self.ai_mode:
                    self.toggle_ai()  # switch to manual
                self.reset()
                return
            if event.keysym in ('a', 'A'):
                self.in_menu = False
                if not self.ai_mode:
                    self.toggle_ai()  # switch to AI
                self.reset()
                return
            return
        if event.keysym in ('a', 'A'):
            self.toggle_ai()
            return
        if self.game_over:
            return
        if event.keysym == 'space':
            self.hard_drop()
            return
        if event.keysym == 'Left':
            self.move(-1, 0)
        elif event.keysym == 'Right':
            self.move(1, 0)
        elif event.keysym == 'Down':
            self.soft_drop()
            return
        elif event.keysym == 'Up':
            self.rotate_piece()
            return
        else:
            return
        self._draw()

    def _step(self):
        if self.game_over or self.in_menu:
            return
        try:
            if not self.move(0, 1):
                self._lock()
            else:
                self._draw()
        except Exception:
            logging.error('Step error', exc_info=True)
            traceback.print_exc()

    def _tick(self):
        try:
            if not self.game_over:
                self.fall_counter += 50
                if self.fall_counter >= self.fall_speed:
                    self._step()
                    self.fall_counter -= self.fall_speed  # simpler subtraction, sufficient
        except Exception:
            logging.error('Tick error', exc_info=True)
            traceback.print_exc()
        finally:
            self._tick_id = self.root.after(50, self._tick)

    def reset(self):
        _log(f'[RESET] was score={self.score} lines={self.lines}')
        if self._tick_id is not None:
            self.root.after_cancel(self._tick_id)
            self._tick_id = None
        ai_id = getattr(self, '_ai_tick_id', None)
        if ai_id is not None:
            self.root.after_cancel(ai_id)
            self._ai_tick_id = None
        self.board = [[None] * GRID_WIDTH for _ in range(GRID_HEIGHT)]
        self.score = 0
        self.level = 1
        self.lines = 0
        self.game_over = False
        self.fall_speed = 800
        self.fall_counter = 0
        self.bag = []
        self.current = self._next_piece()
        self.next = self._next_piece()
        self._draw()
        self._tick()

    def run(self):
        try:
            self.root.mainloop()
        except Exception:
            logging.error('Mainloop crashed', exc_info=True)
            traceback.print_exc()


def show_menu():
    logging.info('Menu opened')
    menu_root = tk.Tk()
    menu_root.title('Tetris')
    menu_root.configure(bg='#0a0a1e')
    menu_root.resizable(False, False)

    w, h = 340, 280
    sw = menu_root.winfo_screenwidth()
    sh = menu_root.winfo_screenheight()
    menu_root.geometry(f'{w}x{h}+{(sw-w)//2}+{(sh-h)//2}')

    # Title area with decorative line
    tk.Frame(menu_root, height=2, bg='#334').pack(fill='x')
    tk.Label(menu_root, text='T E T R I S', font=(FONT_FAMILY, 30, 'bold'),
             fg='#ffcc00', bg='#0a0a1e').pack(pady=(25, 8))
    tk.Label(menu_root, text='Classic Block Game', font=(FONT_FAMILY, 11),
             fg='#667', bg='#0a0a1e').pack()
    tk.Frame(menu_root, height=6, bg='#0a0a1e').pack()

    tk.Frame(menu_root, height=2, bg='#334').pack(fill='x', pady=(10, 0))

    result = [None]

    def start_manual():
        result[0] = False
        logging.info('User selected: Manual Play')
        menu_root.destroy()

    def start_ai():
        result[0] = True
        logging.info('User selected: AI Play')
        menu_root.destroy()

    def quit_game():
        menu_root.destroy()
        sys.exit(0)

    btn_w, btn_h = 18, 2
    gap = 6

    btn_frame = tk.Frame(menu_root, bg='#0a0a1e')
    btn_frame.pack(pady=(15, 5))

    tk.Button(btn_frame, text='Manual Play', command=start_manual, width=btn_w, height=btn_h, bd=0,
              bg='#2d6b2d', fg='#e0ffe0', activebackground='#3d8b3d', activeforeground='#fff',
              font=(FONT_FAMILY, 13, 'bold'), cursor='hand2').pack(pady=gap)

    tk.Button(btn_frame, text='AI Play', command=start_ai, width=btn_w, height=btn_h, bd=0,
              bg='#2d2d6b', fg='#e0e0ff', activebackground='#3d3d8b', activeforeground='#fff',
              font=(FONT_FAMILY, 13, 'bold'), cursor='hand2').pack(pady=gap)

    tk.Button(btn_frame, text='Quit', command=quit_game, width=btn_w, height=1, bd=0,
              bg='#3a2020', fg='#faa', activebackground='#5a3030', activeforeground='#fff',
              font=(FONT_FAMILY, 10), cursor='hand2').pack(pady=(gap + 4, 0))

    tk.Frame(menu_root, height=2, bg='#334').pack(fill='x', side='bottom')

    menu_root.protocol('WM_DELETE_WINDOW', lambda: sys.exit(0))
    menu_root.mainloop()
    return result[0] if result[0] is not None else False


if __name__ == '__main__':
    logging.info('===== Tetris Starting =====')
    logging.info(f'Python {sys.version}')
    logging.info(f'Tk {tk.TkVersion}')
    ai_mode = show_menu()
    logging.info(f'Mode selected: {"AI" if ai_mode else "Manual"}')
    Tetris(ai_mode=ai_mode).run()
    logging.info('===== Tetris Exited =====')
