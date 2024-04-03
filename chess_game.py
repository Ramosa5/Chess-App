from PyQt5.QtWidgets import QMainWindow, QApplication, QLabel, QVBoxLayout, QWidget, QDockWidget, QMessageBox, QLineEdit
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot
import sys
from PyQt5.QtWidgets import QMainWindow, QGraphicsView, QDockWidget, QVBoxLayout, QPushButton, QColorDialog, QWidget
from PyQt5.QtCore import Qt
from chessboard import Chessboard
import turn
from PyQt5.QtCore import QMutex, QMutexLocker
import time
import chess

turn_mutex = QMutex()

def trap_exc_during_debug(*args):
    print(args)

sys.excepthook = trap_exc_during_debug

class TurnWorker(QThread):
    update_turn = pyqtSignal(str)  # Signal to update the turn

    def __init__(self):
        super().__init__()

    def run(self):
        last_turn = None
        while True:
            time.sleep(0.2)  # Use a short sleep to prevent high CPU usage
            with QMutexLocker(turn_mutex):
                current_turn = "White" if turn.is_white_move else "Black"  # Convert the boolean to a string
            if current_turn != last_turn:
                self.update_turn.emit(current_turn)  # Emit the user-friendly turn information
                last_turn = current_turn


class ClockWorker(QThread):
    update_time = pyqtSignal(str, str)  # Signal to update the time for both players
    time_out = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.mode = "def"  # Default mode
        self.white_time = self.initial_time()  # Initialize time for White
        self.black_time = self.initial_time()  # Initialize time for Black
        self.last_update = time.time()
        self.current_turn = "White"
        self.running = True

    def set_mode(self, mode):
        self.mode = mode
        self.white_time = self.initial_time()
        self.black_time = self.initial_time()
        self.last_update = time.time()

    def initial_time(self):
        # Set the initial time based on the mode
        if self.mode == "10min" or self.mode == "10min_increment":
            return 10 * 60  # 10 minutes
        elif self.mode == "5min":
            return 5 * 60  # 5 minutes
        elif self.mode == "def":
            return 10 * 3600  # 5 minutes
        return 10 * 3600  # Default to 10 minutes

    def run(self):
        start = False
        while self.running:
            time.sleep(1)  # Update the clock every second
            if turn.game_over:
                self.running = False  # Stop the loop if the game is over
                break
            current_time = time.time()
            elapsed = current_time - self.last_update
            self.last_update = current_time

            with QMutexLocker(turn_mutex):
                new_turn = "White" if turn.is_white_move else "Black"

                if self.mode == "10min_increment" and new_turn != self.current_turn:
                    # Add 15 seconds increment for the new turn
                    if new_turn == "Black":
                        self.white_time += 15
                    else:
                        self.black_time += 15

                if new_turn == "Black":
                    start = True
                if start:
                    if new_turn == "White":
                        self.white_time -= elapsed
                    else:
                        self.black_time -= elapsed

                if self.white_time <= 0:
                    turn.win_by_time = "black"
                    self.time_out.emit("Black wins by time!")
                    self.running = False  # Stop the clock
                elif self.black_time <= 0:
                    turn.win_by_time = "white"
                    self.time_out.emit("White wins by time!")
                    self.running = False  # Stop the clock
                # Check for turn change
                self.current_turn = new_turn  # Update the turn for the next iteration

            # Emit the updated times
            self.update_time.emit(self.format_time(max(0, self.white_time)),
                                  self.format_time(max(0, self.black_time)))

    def format_time(self, seconds):
        # Format the time as H:M:S
        return time.strftime('%H:%M:%S', time.gmtime(seconds))
class MoveWorker(QThread):
    update_last_move = pyqtSignal(str)  # Signal to update the last move made

    def __init__(self):
        super().__init__()
        self.last_checked = -2  # Initialize to check the first two moves initially
        self.running = True

    def run(self):
        while self.running:
            time.sleep(1)  # Update the clock every second
            if turn.game_over:
                self.running = False  # Stop the loop if the game is over
                break  # Check for new moves every 0.2 seconds
            with QMutexLocker(turn_mutex):
                moves_count = len(turn.last_moves)
                if moves_count > self.last_checked and moves_count >= 2:
                    last_move = self.determine_last_move(turn.last_moves[-2], turn.last_moves[-1])
                    self.update_last_move.emit(last_move)
                    self.last_checked = moves_count

    def determine_last_move(self, prev_fen, current_fen):
        board_prev = chess.Board(prev_fen)
        board_current = chess.Board(current_fen)
        move = None
        for move in board_prev.legal_moves:
            board_prev.push(move)
            if board_prev.fen() == board_current.fen():
                return move.uci()  # Returns the move in UCI (Universal Chess Interface) notation
            board_prev.pop()
        return "Unknown Move"

class FenWorker(QThread):
    update_board = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.mode = "def"  # Default mode
        self.last_update = time.time()
        self.current_turn = "White"
        self.running = True

    def run(self):
        start = False
        while self.running:
            time.sleep(1)  # Update the clock every second

class ChessGame(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gra w szachy")
        self.setGeometry(100, 100, 800, 600)

        self.chessboard = Chessboard("Default")
        self.view = QGraphicsView(self.chessboard, self)
        self.setCentralWidget(self.view)

        # Create a dock widget
        self.dock_widget = QDockWidget("Game Status", self)
        self.dock_widget.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        # Widget to hold content in the dock widget
        dock_content = QWidget()
        self.dock_widget.setWidget(dock_content)
        layout = QVBoxLayout()
        dock_content.setLayout(layout)

        # Label to display the current turn
        self.turn_label = QLabel()
        layout.addWidget(self.turn_label)

        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock_widget)

        # Start the thread to update turns
        self.turn_thread = TurnWorker()
        self.turn_thread.update_turn.connect(self.update_turn)
        self.turn_thread.start()

        self.fen_input = QLineEdit()
        self.fen_input.setPlaceholderText("Enter FEN string")
        layout.addWidget(self.fen_input)

        # Button to update the board with the FEN string
        self.update_fen_button = QPushButton("Update Board from FEN")
        layout.addWidget(self.update_fen_button)
        self.update_fen_button.clicked.connect(self.update_board_from_fen)

        # Label to display the last move
        self.last_move_label = QLabel("Last Move: ")
        layout.addWidget(self.last_move_label)

        # Start the thread to update the last move
        self.move_thread = MoveWorker()
        self.move_thread.update_last_move.connect(self.update_last_move)
        self.move_thread.start()

        self.btn_10min = QPushButton("10 Min Countdown")
        layout.addWidget(self.btn_10min)
        self.btn_10min_increment = QPushButton("10 Min + 15 Sec Increment")
        layout.addWidget(self.btn_10min_increment)
        self.btn_5min = QPushButton("5 Min Countdown")
        layout.addWidget(self.btn_5min)

        # Connect buttons to their respective slot functions
        self.btn_10min.clicked.connect(lambda: self.set_clock_mode("10min"))
        self.btn_10min_increment.clicked.connect(lambda: self.set_clock_mode("10min_increment"))
        self.btn_5min.clicked.connect(lambda: self.set_clock_mode("5min"))


        # Chess clock labels
        self.white_clock_label = QLabel("White Time: 00:00:00")
        self.black_clock_label = QLabel("Black Time: 00:00:00")
        layout.addWidget(self.white_clock_label)
        layout.addWidget(self.black_clock_label)

        # Start the thread to update the chess clock
        self.clock_thread = ClockWorker()
        self.clock_thread.update_time.connect(self.update_clock)
        self.clock_thread.time_out.connect(self.show_winner_popup)  # Connect the time_out signal
        self.clock_thread.start()

    def set_clock_mode(self, mode):
        self.clock_thread.set_mode(mode)

    def update_board_from_fen(self):
        fen_str = self.fen_input.text()  # Get the FEN string from QLineEdit
        self.update_board(fen_str)  # Call the method to update the board with this FEN string


    def show_winner_popup(self, message):
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setText(message)
        msgBox.setWindowTitle("Game Over")
        msgBox.setStandardButtons(QMessageBox.Ok)
        msgBox.exec_()
    @pyqtSlot(str)
    def update_turn(self, turn):
        print(turn)
        self.turn_label.setText(f"Current turn: {turn}")

    @pyqtSlot(str)
    def update_board(self, fen):
        self.chessboard = Chessboard(fen)
        self.view = QGraphicsView(self.chessboard, self)
        self.setCentralWidget(self.view)

    @pyqtSlot(str)
    def update_last_move(self, move):
        self.last_move_label.setText(f"Last Move: {move}")

    @pyqtSlot(str, str)
    def update_clock(self, white_time, black_time):
        self.white_clock_label.setText(f"White Time: {white_time}")
        self.black_clock_label.setText(f"Black Time: {black_time}")