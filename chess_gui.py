"""
中国象棋 PyQt 图形界面。

功能：
- 人机对弈（支持 Random/Minimax/AlphaBeta/MCTS AI）
- AI vs AI 对弈（红方和黑方各选一个 AI）
- 棋盘可视化（9x10 网格，圆形棋子）
- 状态提示（轮次、AI 思考状态）
- 控制功能（重新开始、悔棋、暂停）
"""

import sys
from typing import Optional
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QComboBox,
    QMessageBox, QStackedWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPoint, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QBrush

from cchess import GameState, Player, Point, PieceType, Move

# 棋子文字映射（来自 play_chess.py）
PIECE_CHARS = {
    (Player.red, PieceType.GENERAL):  '帥',
    (Player.red, PieceType.ADVISOR):  '仕',
    (Player.red, PieceType.ELEPHANT): '相',
    (Player.red, PieceType.HORSE):    '馬',
    (Player.red, PieceType.CHARIOT):  '車',
    (Player.red, PieceType.CANNON):   '炮',
    (Player.red, PieceType.PAWN):     '兵',
    (Player.black, PieceType.GENERAL):  '将',
    (Player.black, PieceType.ADVISOR):  '士',
    (Player.black, PieceType.ELEPHANT): '象',
    (Player.black, PieceType.HORSE):    '马',
    (Player.black, PieceType.CHARIOT):  '车',
    (Player.black, PieceType.CANNON):   '炮',
    (Player.black, PieceType.PAWN):     '卒',
}


class GameThread(QThread):
    """AI 思考线程，避免界面卡顿"""
    move_ready = pyqtSignal(object)  # Move

    def __init__(self, game_state, agent_fn):
        super().__init__()
        self.game_state = game_state
        self.agent_fn = agent_fn

    def run(self):
        """调用 AI select_move"""
        move = self.agent_fn(self.game_state)
        self.move_ready.emit(move)


class ChessBoardWidget(QWidget):
    """自定义棋盘绘制组件"""

    # 布局常量
    MARGIN = 40
    CAPTURED_AREA_WIDTH = 200  # 被吃棋子区域宽度
    CELL_SIZE = 60
    PIECE_RADIUS = 25

    def __init__(self, parent=None):
        super().__init__(parent)
        self.game_state: Optional[GameState] = None
        self.selected: Optional[Point] = None
        self.legal_moves: list = []
        self.setMinimumSize(
            (9 - 1) * self.CELL_SIZE + self.CAPTURED_AREA_WIDTH * 2 + self.MARGIN * 2,
            (10 - 1) * self.CELL_SIZE + self.MARGIN * 2
        )
        self.last_move: Optional[Move] = None  # 最后一步走法
        self.red_captured = []    # 红方被吃的棋子
        self.black_captured = []  # 黑方被吃的棋子
        self._thinking_from = None  # AI 正在思考的棋子位置

    def set_game_state(self, state: GameState, clear_selection=True, last_move=None,
                      red_captured=None, black_captured=None, thinking_from=None):
        self.game_state = state
        if clear_selection:
            self.selected = None
            self.legal_moves = []
        if last_move is not None:
            self.last_move = last_move
        if red_captured is not None:
            self.red_captured = red_captured
        if black_captured is not None:
            self.black_captured = black_captured
        self._thinking_from = thinking_from
        self.update()

    def set_selected(self, point: Optional[Point], legal_moves: list = None):
        self.selected = point
        self.legal_moves = legal_moves or []
        self.update()

    def paintEvent(self, event):
        """绘制棋盘和棋子"""
        if self.game_state is None:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        self._draw_board(painter)           # 1. 先画棋盘背景（fillRect 在这里）
        self._draw_captured_pieces(painter) # 2. 再画被吃棋子（不会被背景覆盖）
        self._draw_pieces(painter)          # 3. 画棋盘上的棋子
        self._draw_overlays(painter)        # 4. 画高亮

    def _draw_board(self, painter: QPainter):
        """绘制棋盘格子"""
        # 背景
        painter.fillRect(0, 0, self.width(), self.height(), QColor(240, 230, 210))

        # 使用统一的居中坐标
        x0, y0 = self._get_board_offset()
        board_width = (self.game_state.board.NUM_COLS - 1) * self.CELL_SIZE
        board_height = (self.game_state.board.NUM_ROWS - 1) * self.CELL_SIZE

        # 外框
        painter.setPen(QPen(QColor(101, 67, 33), 3))
        painter.drawRect(x0 - 5, y0 - 5, board_width + 10, board_height + 10)

        # 内部网格线
        painter.setPen(QPen(QColor(101, 67, 33), 1))
        for r in range(self.game_state.board.NUM_ROWS):
            y = y0 + r * self.CELL_SIZE
            painter.drawLine(x0, y, x0 + board_width, y)

        for c in range(self.game_state.board.NUM_COLS):
            x = x0 + c * self.CELL_SIZE
            painter.drawLine(x, y0, x, y0 + board_height)

        # 楚河汉界（清除中间两条线的中间部分）
        river_y1 = y0 + 4 * self.CELL_SIZE
        river_y2 = y0 + 5 * self.CELL_SIZE
        painter.fillRect(x0, river_y1, board_width, self.CELL_SIZE, QColor(240, 230, 210))

        # 绘制楚河汉界文字
        painter.setPen(QPen(QColor(101, 67, 33), 2))
        font = QFont("SimHei", 16)
        painter.setFont(font)
        painter.drawText(x0 + board_width // 4 - 20, river_y1, 100, self.CELL_SIZE,
                        Qt.AlignmentFlag.AlignCenter, "楚 河")
        painter.drawText(x0 + 3 * board_width // 4 - 30, river_y1, 100, self.CELL_SIZE,
                        Qt.AlignmentFlag.AlignCenter, "汉 界")

    def _draw_captured_pieces(self, painter: QPainter):
        """绘制被吃掉的棋子（在棋盘左侧）"""
        if not self.red_captured and not self.black_captured:
            return

        try:
            board_x, board_y = self._get_board_offset()
        except Exception:
            return

        board_height = (self.game_state.board.NUM_ROWS - 1) * self.CELL_SIZE

        # 被吃棋子区域：紧贴棋盘左侧
        x0 = board_x - self.CAPTURED_AREA_WIDTH + 5
        y0 = board_y
        width = self.CAPTURED_AREA_WIDTH - 10
        height = board_height

        # 背景
        painter.fillRect(x0, y0, width, height, QColor(230, 220, 200))

        # 标题
        painter.setPen(QPen(QColor(101, 67, 33), 2))
        font = QFont("SimHei", 12)
        painter.setFont(font)

        red_y_start = y0 + 20
        painter.drawText(x0, red_y_start - 22, width, 20, Qt.AlignmentFlag.AlignCenter, "红方被吃")

        black_y_start = y0 + height // 2 + 20
        painter.drawText(x0, black_y_start - 22, width, 20, Qt.AlignmentFlag.AlignCenter, "黑方被吃")

        # 棋子尺寸
        small_r = int(self.PIECE_RADIUS * 0.65)
        piece_size = small_r * 2
        gap = 6

        for i, piece_type in enumerate(self.red_captured):
            col, row = i % 4, i // 4
            x = x0 + 10 + col * (piece_size + gap)
            y = red_y_start + row * (piece_size + gap)
            if y + piece_size > black_y_start - 28:
                break
            painter.setBrush(QBrush(QColor(245, 222, 179)))
            painter.setPen(QPen(QColor(180, 80, 80), 2))
            painter.drawEllipse(x, y, piece_size, piece_size)
            painter.setPen(QPen(QColor(200, 0, 0), 2))
            painter.setFont(QFont("SimHei", 10, QFont.Weight.Bold))
            painter.drawText(x, y, piece_size, piece_size, Qt.AlignmentFlag.AlignCenter,
                             PIECE_CHARS[(Player.red, piece_type)])

        for i, piece_type in enumerate(self.black_captured):
            col, row = i % 4, i // 4
            x = x0 + 10 + col * (piece_size + gap)
            y = black_y_start + row * (piece_size + gap)
            if y + piece_size > y0 + height - 5:
                break
            painter.setBrush(QBrush(QColor(245, 222, 179)))
            painter.setPen(QPen(QColor(80, 80, 80), 2))
            painter.drawEllipse(x, y, piece_size, piece_size)
            painter.setPen(QPen(QColor(50, 50, 50), 2))
            painter.setFont(QFont("SimHei", 10, QFont.Weight.Bold))
            painter.drawText(x, y, piece_size, piece_size, Qt.AlignmentFlag.AlignCenter,
                             PIECE_CHARS[(Player.black, piece_type)])

    def _draw_pieces(self, painter: QPainter):
        """绘制所有棋子"""
        board = self.game_state.board

        for pt, piece in board.pieces_for_player(Player.red):
            self._draw_piece(painter, piece, pt)

        for pt, piece in board.pieces_for_player(Player.black):
            self._draw_piece(painter, piece, pt)

    def _draw_piece(self, painter: QPainter, piece, point: Point):
        """绘制单个棋子（圆形背景 + 文字）"""
        # 计算屏幕坐标
        screen_x, screen_y = self._board_to_screen(point)

        # 圆形背景
        painter.setBrush(QBrush(QColor(245, 222, 179)))  # 小麦色
        painter.setPen(QPen(QColor(139, 69, 19), 2))     # 深棕色边框
        painter.drawEllipse(
            screen_x - self.PIECE_RADIUS,
            screen_y - self.PIECE_RADIUS,
            self.PIECE_RADIUS * 2,
            self.PIECE_RADIUS * 2
        )

        # 文字
        char = PIECE_CHARS[(piece.player, piece.piece_type)]
        color = Qt.GlobalColor.red if piece.player == Player.red else Qt.GlobalColor.black

        painter.setPen(QPen(color, 2))
        font = QFont("SimHei", 18, QFont.Weight.Bold)
        painter.setFont(font)

        rect_x = screen_x - self.PIECE_RADIUS
        rect_y = screen_y - self.PIECE_RADIUS
        rect_size = self.PIECE_RADIUS * 2

        painter.drawText(
            rect_x, rect_y, rect_size, rect_size,
            Qt.AlignmentFlag.AlignCenter,
            char
        )

    def _draw_overlays(self, painter: QPainter):
        """绘制选中状态和合法走法"""
        # AI 正在思考的棋子（橙色高亮）
        if self._thinking_from:
            x, y = self._board_to_screen(self._thinking_from)
            painter.setPen(QPen(QColor(255, 165, 0), 3))  # 橙色
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(
                x - self.PIECE_RADIUS - 3,
                y - self.PIECE_RADIUS - 3,
                self.PIECE_RADIUS * 2 + 6,
                self.PIECE_RADIUS * 2 + 6
            )

        # 选中高亮（绿色）
        if self.selected:
            x, y = self._board_to_screen(self.selected)
            painter.setPen(QPen(QColor(0, 255, 0), 3))  # 绿色
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(
                x - self.PIECE_RADIUS - 5,
                y - self.PIECE_RADIUS - 5,
                self.PIECE_RADIUS * 2 + 10,
                self.PIECE_RADIUS * 2 + 10
            )

        # 合法走法提示
        painter.setBrush(QBrush(QColor(0, 200, 0)))
        painter.setPen(Qt.PenStyle.NoPen)
        for move in self.legal_moves:
            x, y = self._board_to_screen(move.to_point)
            painter.drawEllipse(x - 5, y - 5, 10, 10)

    def _get_board_offset(self):
        """计算棋盘的偏移量（棋盘本身居中）"""
        board_width = (self.game_state.board.NUM_COLS - 1) * self.CELL_SIZE
        board_height = (self.game_state.board.NUM_ROWS - 1) * self.CELL_SIZE
        board_x = (self.width() - board_width) // 2   # 棋盘水平居中
        board_y = (self.height() - board_height) // 2  # 棋盘垂直居中
        return board_x, board_y

    def _board_to_screen(self, point: Point):
        """棋盘坐标 → 屏幕坐标"""
        board_x, board_y = self._get_board_offset()
        x = board_x + point.col * self.CELL_SIZE
        y = board_y + (self.game_state.board.NUM_ROWS - 1 - point.row) * self.CELL_SIZE
        return x, y

    def _screen_to_board(self, x: int, y: int):
        """屏幕坐标 → 棋盘坐标"""
        board_x, board_y = self._get_board_offset()
        col = round((x - board_x) / self.CELL_SIZE)
        row = self.game_state.board.NUM_ROWS - 1 - round((y - board_y) / self.CELL_SIZE)
        return Point(row, col)

    def mousePressEvent(self, event):
        """处理鼠标点击"""
        if self.game_state is None:
            return

        # 转换坐标
        board_point = self._screen_to_board(event.position().x(), event.position().y())

        # 检查是否在棋盘范围内
        if not (0 <= board_point.row < self.game_state.board.NUM_ROWS and
                0 <= board_point.col < self.game_state.board.NUM_COLS):
            return

        # 发送信号到主窗口
        self.parent().parent().on_board_click(board_point)


class ChessMainWindow(QMainWindow):
    """主窗口"""

    # 对战模式枚举
    MODE_HUMAN_VS_AI = 0  # 人机对弈
    MODE_AI_VS_AI = 1     # AI vs AI

    def __init__(self):
        super().__init__()
        self.setWindowTitle("中国象棋 AI")
        self.game_state = GameState.new_game()
        self.history = [self.game_state]  # 历史记录，用于悔棋
        self.ai_thread: Optional[GameThread] = None
        self.is_player_turn = True  # 是否轮到玩家
        self.game_mode = self.MODE_HUMAN_VS_AI  # 对战模式
        self.ai_vs_ai_paused = False  # AI vs AI 暂停状态

        # AI 设置
        self.player_color = Player.red  # 玩家执红
        self.ai_agent_fn = None  # AI 函数（人机模式）
        self.red_ai_fn = None    # 红方 AI 函数（AI vs AI 模式）
        self.black_ai_fn = None  # 黑方 AI 函数（AI vs AI 模式）

        # 被吃棋子列表
        self.red_captured = []    # 红方被吃的棋子（棋子类型列表）
        self.black_captured = []  # 黑方被吃的棋子（棋子类型列表）

        self.setup_ui()

    def setup_ui(self):
        """创建界面组件"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 设置栏
        settings_layout = QHBoxLayout()

        # 对战模式选择
        settings_layout.addWidget(QLabel("对战模式:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["人机对弈", "AI vs AI"])
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        settings_layout.addWidget(self.mode_combo)

        settings_layout.addSpacing(20)

        # 使用 QStackedWidget 切换不同模式的设置
        self.settings_stack = QStackedWidget()

        # 人机模式设置
        self.human_ai_widget = QWidget()
        human_ai_layout = QHBoxLayout(self.human_ai_widget)
        human_ai_layout.addWidget(QLabel("玩家执棋:"))
        self.player_combo = QComboBox()
        self.player_combo.addItems(["红方", "黑方"])
        self.player_combo.currentIndexChanged.connect(self.on_player_color_changed)
        human_ai_layout.addWidget(self.player_combo)
        human_ai_layout.addSpacing(20)
        human_ai_layout.addWidget(QLabel("AI:"))
        self.ai_combo = QComboBox()
        self.ai_combo.addItems(["Random", "Minimax", "AlphaBeta", "MCTS"])
        self.ai_combo.currentIndexChanged.connect(self.on_ai_changed)
        human_ai_layout.addWidget(self.ai_combo)
        human_ai_layout.addStretch()

        # AI vs AI 模式设置
        self.ai_ai_widget = QWidget()
        ai_ai_layout = QHBoxLayout(self.ai_ai_widget)
        ai_ai_layout.addWidget(QLabel("红方 AI:"))
        self.red_ai_combo = QComboBox()
        self.red_ai_combo.addItems(["Random", "Minimax", "AlphaBeta", "MCTS"])
        self.red_ai_combo.currentIndexChanged.connect(self.on_ai_ai_changed)
        ai_ai_layout.addWidget(self.red_ai_combo)
        ai_ai_layout.addSpacing(20)
        ai_ai_layout.addWidget(QLabel("黑方 AI:"))
        self.black_ai_combo = QComboBox()
        self.black_ai_combo.addItems(["Random", "Minimax", "AlphaBeta", "MCTS"])
        self.black_ai_combo.currentIndexChanged.connect(self.on_ai_ai_changed)
        ai_ai_layout.addWidget(self.black_ai_combo)
        ai_ai_layout.addStretch()

        self.settings_stack.addWidget(self.human_ai_widget)
        self.settings_stack.addWidget(self.ai_ai_widget)

        settings_layout.addWidget(self.settings_stack)
        settings_layout.addStretch()
        main_layout.addLayout(settings_layout)

        # 棋盘
        self.board_widget = ChessBoardWidget(self)
        self.board_widget.set_game_state(self.game_state)
        main_layout.addWidget(self.board_widget, alignment=Qt.AlignmentFlag.AlignCenter)

        # 状态栏
        status_layout = QHBoxLayout()
        self.turn_label = QLabel("当前轮次: 红方")
        self.status_label = QLabel("状态: 等待开始")
        status_layout.addWidget(self.turn_label)
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        main_layout.addLayout(status_layout)

        # 按钮栏
        button_layout = QHBoxLayout()

        self.start_btn = QPushButton("开始")
        self.start_btn.clicked.connect(self.start_game)
        button_layout.addWidget(self.start_btn)

        self.restart_btn = QPushButton("重新开始")
        self.restart_btn.clicked.connect(self.restart_game)
        button_layout.addWidget(self.restart_btn)

        self.undo_btn = QPushButton("悔棋")
        self.undo_btn.clicked.connect(self.undo_move)
        self.undo_btn.setEnabled(False)
        button_layout.addWidget(self.undo_btn)

        # AI vs AI 模式的暂停/继续按钮
        self.pause_btn = QPushButton("暂停")
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setVisible(False)
        button_layout.addWidget(self.pause_btn)

        button_layout.addStretch()
        main_layout.addLayout(button_layout)

        # 初始化 AI 函数（不触发对弈）
        self.on_ai_changed(0)
        self.on_ai_ai_changed()
        # 显示初始棋盘，等待用户点击开始
        self.restart_game()

    def on_mode_changed(self, index):
        """对战模式改变"""
        self.game_mode = index

        if index == self.MODE_HUMAN_VS_AI:
            # 人机模式
            self.settings_stack.setCurrentIndex(0)
            self.undo_btn.setVisible(True)
            self.pause_btn.setVisible(False)
        else:
            # AI vs AI 模式
            self.settings_stack.setCurrentIndex(1)
            self.undo_btn.setVisible(False)
            self.pause_btn.setVisible(True)
            self.pause_btn.setEnabled(True)

        # 不自动重新开始，等待用户点击重新开始按钮

    def on_ai_ai_changed(self, index=None):
        """AI vs AI 模式下的 AI 选择改变"""
        red_ai_name = self.red_ai_combo.currentText()
        black_ai_name = self.black_ai_combo.currentText()

        # 创建红方 AI
        if red_ai_name == "Random":
            from agents.chess_random_agent import ChessRandomAgent
            self.red_ai_fn = ChessRandomAgent().select_move
        elif red_ai_name == "Minimax":
            from agents.chess_minimax_agent import ChessMinimaxAgent
            agent = ChessMinimaxAgent(time_limit=5.0, max_depth=3, verbose=False)
            self.red_ai_fn = agent.select_move
        elif red_ai_name == "AlphaBeta":
            from agents.chess_alphabeta_agent import ChessAlphaBetaAgent
            agent = ChessAlphaBetaAgent(time_limit=5.0, verbose=False)
            self.red_ai_fn = agent.select_move
        elif red_ai_name == "MCTS":
            from agents.chess_mcts_agent import ChessMCTSAgent
            agent = ChessMCTSAgent(time_limit=5.0, verbose=False)
            self.red_ai_fn = agent.select_move

        # 创建黑方 AI
        if black_ai_name == "Random":
            from agents.chess_random_agent import ChessRandomAgent
            self.black_ai_fn = ChessRandomAgent().select_move
        elif black_ai_name == "Minimax":
            from agents.chess_minimax_agent import ChessMinimaxAgent
            agent = ChessMinimaxAgent(time_limit=5.0, max_depth=3, verbose=False)
            self.black_ai_fn = agent.select_move
        elif black_ai_name == "AlphaBeta":
            from agents.chess_alphabeta_agent import ChessAlphaBetaAgent
            agent = ChessAlphaBetaAgent(time_limit=5.0, verbose=False)
            self.black_ai_fn = agent.select_move
        elif black_ai_name == "MCTS":
            from agents.chess_mcts_agent import ChessMCTSAgent
            agent = ChessMCTSAgent(time_limit=5.0, verbose=False)
            self.black_ai_fn = agent.select_move

        # 不自动重新开始，等待用户点击重新开始按钮

    def toggle_pause(self):
        """切换 AI vs AI 暂停状态"""
        self.ai_vs_ai_paused = not self.ai_vs_ai_paused
        if self.ai_vs_ai_paused:
            self.pause_btn.setText("继续")
            self.status_label.setText("状态: 已暂停")
        else:
            self.pause_btn.setText("暂停")
            # 如果轮到某方，触发 AI 落子
            if not self.game_state.is_over():
                self.trigger_ai_move()

    def on_player_color_changed(self, index):
        """玩家执棋颜色改变"""
        self.player_color = Player.red if index == 0 else Player.black
        self.restart_game()

    def on_ai_changed(self, index):
        """AI 选择改变"""
        ai_name = self.ai_combo.currentText()

        if ai_name == "Random":
            from agents.chess_random_agent import ChessRandomAgent
            agent = ChessRandomAgent()
        elif ai_name == "Minimax":
            from agents.chess_minimax_agent import ChessMinimaxAgent
            agent = ChessMinimaxAgent(time_limit=5.0, max_depth=3, verbose=False)
        elif ai_name == "AlphaBeta":
            from agents.chess_alphabeta_agent import ChessAlphaBetaAgent
            agent = ChessAlphaBetaAgent(time_limit=5.0, verbose=False)
        elif ai_name == "MCTS":
            from agents.chess_mcts_agent import ChessMCTSAgent
            agent = ChessMCTSAgent(time_limit=5.0, verbose=False)
        else:
            return

        self.ai_agent_fn = agent.select_move
        # 不自动重新开始，等待用户点击重新开始按钮

    def restart_game(self):
        """重置棋盘到初始状态，等待点击开始"""
        self.game_state = GameState.new_game()
        self.history = [self.game_state]
        self.ai_vs_ai_paused = False
        self.pause_btn.setText("暂停")
        self.pause_btn.setEnabled(False)
        self.red_captured = []
        self.black_captured = []

        if self.game_mode == self.MODE_HUMAN_VS_AI:
            self.is_player_turn = (self.game_state.next_player == self.player_color)
            self.undo_btn.setEnabled(False)
        else:
            self.is_player_turn = False

        self.board_widget.set_game_state(
            self.game_state,
            red_captured=self.red_captured,
            black_captured=self.black_captured
        )
        self.start_btn.setEnabled(True)
        self.status_label.setText("状态: 点击「开始」开始对弈")
        current_player = self.game_state.next_player
        self.turn_label.setText(f"当前轮次: {'红方' if current_player == Player.red else '黑方'}")

    def start_game(self):
        """开始对弈"""
        self.start_btn.setEnabled(False)

        if self.game_mode == self.MODE_AI_VS_AI:
            self.pause_btn.setEnabled(True)

        self.update_status()

        # 触发 AI（人机模式 AI 先手，或 AI vs AI 模式）
        if not self.is_player_turn and not self.game_state.is_over():
            self.trigger_ai_move()

    def update_status(self):
        """更新状态显示"""
        current_player = self.game_state.next_player
        turn_text = "红方" if current_player == Player.red else "黑方"
        self.turn_label.setText(f"当前轮次: {turn_text}")

        if self.game_state.is_over():
            winner = self.game_state.winner()
            if winner:
                winner_text = "红方" if winner == Player.red else "黑方"
                self.status_label.setText(f"状态: {winner_text}获胜！")
            else:
                self.status_label.setText("状态: 平局")
            self.pause_btn.setEnabled(False)
        elif self.game_mode == self.MODE_AI_VS_AI:
            # AI vs AI 模式
            if self.ai_vs_ai_paused:
                self.status_label.setText("状态: 已暂停")
            else:
                ai_name = self.red_ai_combo.currentText() if current_player == Player.red else self.black_ai_combo.currentText()
                self.status_label.setText(f"状态: {ai_name} 思考中...")
        elif self.is_player_turn:
            self.status_label.setText("状态: 请走棋")
        else:
            ai_name = self.ai_combo.currentText()
            self.status_label.setText(f"状态: {ai_name} 思考中...")

        # 更新悔棋按钮（仅人机模式）
        if self.game_mode == self.MODE_HUMAN_VS_AI:
            self.undo_btn.setEnabled(len(self.history) > 1)

    def on_board_click(self, point: Point):
        """处理棋盘点击"""
        # AI vs AI 模式下禁用点击交互
        if self.game_mode == self.MODE_AI_VS_AI:
            return

        if not self.is_player_turn or self.game_state.is_over():
            return

        board = self.game_state.board
        clicked_piece = board.get(point)

        # 获取当前选中状态
        selected = self.board_widget.selected

        if selected is None:
            # 选择棋子
            if clicked_piece and clicked_piece.player == self.player_color:
                # 显示合法走法
                legal_moves = [
                    move for move in self.game_state.legal_moves()
                    if move.from_point == point
                ]
                self.board_widget.set_selected(point, legal_moves)
        else:
            # 尝试移动
            move = Move(selected, point)
            legal_moves = self.game_state.legal_moves()

            if move in legal_moves:
                # 执行移动
                self.make_move(move)
                self.board_widget.set_selected(None, [])
            elif clicked_piece and clicked_piece.player == self.player_color:
                # 重新选择
                legal_moves = [
                    m for m in self.game_state.legal_moves()
                    if m.from_point == point
                ]
                self.board_widget.set_selected(point, legal_moves)
            else:
                # 取消选择
                self.board_widget.set_selected(None, [])

    def make_move(self, move: Move):
        """执行走法"""
        # 保存最后一步走法
        last_move = move

        # 检测是否吃子
        captured_piece = self.game_state.board.get(move.to_point)
        if captured_piece is not None:
            # 记录被吃的棋子
            if captured_piece.player == Player.red:
                # 红方棋子被黑方吃掉，添加到红方被吃列表
                self.red_captured.append(captured_piece.piece_type)
            else:
                # 黑方棋子被红方吃掉，添加到黑方被吃列表
                self.black_captured.append(captured_piece.piece_type)

        self.game_state = self.game_state.apply_move(move)
        self.history.append(self.game_state)

        # 更新棋盘，传入被吃棋子信息，清除 thinking_from
        self.board_widget.set_game_state(
            self.game_state,
            last_move=last_move,
            red_captured=self.red_captured,
            black_captured=self.black_captured,
            thinking_from=None  # 清除高亮
        )

        # 检查游戏是否结束
        if self.game_state.is_over():
            self.update_status()
            self.show_game_over()
            return

        # 先切换轮次判断，再更新状态显示
        if self.game_mode == self.MODE_HUMAN_VS_AI:
            self.is_player_turn = not self.is_player_turn
        else:
            # AI vs AI 模式
            pass

        # 切换轮次后再更新状态，确保显示正确
        self.update_status()

        # 触发 AI 落子（人机模式的 AI 回合，或 AI vs AI 模式）
        if (self.game_mode == self.MODE_AI_VS_AI or not self.is_player_turn) and not self.game_state.is_over():
            if not self.ai_vs_ai_paused:
                # AI vs AI 模式下，延迟触发下一个 AI，让棋盘显示更清晰
                if self.game_mode == self.MODE_AI_VS_AI:
                    QTimer.singleShot(500, self.trigger_ai_move)  # 增加到 500ms
                else:
                    QTimer.singleShot(50, self.trigger_ai_move)  # 人机模式也稍微延迟

    def trigger_ai_move(self):
        """触发 AI 走棋"""
        # 防止重复触发
        if self.ai_thread is not None and self.ai_thread.isRunning():
            return

        # 检查游戏状态
        if self.game_state.is_over() or self.ai_vs_ai_paused:
            return

        # 选择当前玩家的 AI
        if self.game_mode == self.MODE_AI_VS_AI:
            current_player = self.game_state.next_player
            if current_player == Player.red:
                ai_fn = self.red_ai_fn
            else:
                ai_fn = self.black_ai_fn
        else:
            # 人机模式
            ai_fn = self.ai_agent_fn

        # 显示思考中状态
        if self.game_mode == self.MODE_AI_VS_AI or not self.is_player_turn:
            self.update_status()

        # 创建并启动 AI 线程
        self.ai_thread = GameThread(self.game_state, ai_fn)
        self.ai_thread.move_ready.connect(self.on_ai_move)
        # 线程结束后自动清理
        self.ai_thread.finished.connect(lambda: setattr(self, 'ai_thread', None))
        self.ai_thread.start()

    def on_ai_move(self, move: Move):
        """AI 走棋完成：先显示橙色框，300ms 后执行移动"""
        if move is None:
            self.update_status()
            return
        # 高亮即将移动的棋子（橙色框），同时保留被吃棋子列表
        self.board_widget.set_game_state(
            self.game_state,
            clear_selection=False,
            thinking_from=move.from_point,
            red_captured=self.red_captured,
            black_captured=self.black_captured
        )
        QTimer.singleShot(300, lambda: self._execute_ai_move(move))

    def _execute_ai_move(self, move: Move):
        """实际执行 AI 的移动"""
        # 检查走法是否在合法走法列表中
        legal_moves = self.game_state.legal_moves()
        if move in legal_moves:
            self.make_move(move)
        else:
            # AI 返回了无效走法，跳过
            print(f"[WARN] AI 返回无效走法: {move}")
            self.update_status()

    def undo_move(self):
        """悔棋（仅人机模式）"""
        if self.game_mode == self.MODE_AI_VS_AI:
            return
        if len(self.history) < 2:
            return

        # 撤销两步（玩家一步，AI 一步）
        if len(self.history) >= 3:
            self.history.pop()  # AI 的一步
            self.history.pop()  # 玩家的一步
        elif len(self.history) == 2:
            self.history.pop()  # 只有一步时，撤销一步

        self.game_state = self.history[-1]
        self.is_player_turn = (self.game_state.next_player == self.player_color)

        # 重新计算被吃棋子列表
        self._recalculate_captured_pieces()

        self.board_widget.set_game_state(
            self.game_state,
            red_captured=self.red_captured,
            black_captured=self.black_captured
        )
        self.update_status()

    def _recalculate_captured_pieces(self):
        """重新计算被吃棋子列表（从初始状态到当前状态）"""
        self.red_captured = []
        self.black_captured = []

        # 获取初始棋盘的所有棋子
        initial_state = GameState.new_game()
        initial_pieces = set()
        for pt, piece in initial_state.board.pieces_for_player(Player.red):
            initial_pieces.add((Player.red, piece.piece_type))
        for pt, piece in initial_state.board.pieces_for_player(Player.black):
            initial_pieces.add((Player.black, piece.piece_type))

        # 获取当前棋盘的所有棋子
        current_pieces = set()
        for pt, piece in self.game_state.board.pieces_for_player(Player.red):
            current_pieces.add((Player.red, piece.piece_type))
        for pt, piece in self.game_state.board.pieces_for_player(Player.black):
            current_pieces.add((Player.black, piece.piece_type))

        # 被吃的棋子 = 初始 - 当前
        captured = initial_pieces - current_pieces
        for player, piece_type in captured:
            if player == Player.red:
                self.red_captured.append(piece_type)
            else:
                self.black_captured.append(piece_type)

    def show_game_over(self):
        """显示游戏结束"""
        winner = self.game_state.winner()
        if winner:
            winner_text = "红方" if winner == Player.red else "黑方"
            QMessageBox.information(self, "游戏结束", f"{winner_text}获胜！")
        else:
            QMessageBox.information(self, "游戏结束", "平局！")


def main():
    app = QApplication(sys.argv)
    window = ChessMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
