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
import sqllite3_database
import json
import socket

turn_mutex = QMutex()

def trap_exc_during_debug(*args):
    print(args)

sys.excepthook = trap_exc_during_debug


class ServerThread(QThread):
    received_fen = pyqtSignal(str)  # Sygnał do aktualizacji stanu planszy

    def __init__(self, host, port, parent=None):
        super().__init__(parent=parent)
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.client_socket = None

    def run(self):
        while True:
            self.client_socket, addr = self.server_socket.accept()
            print(f"Connected by {addr}")
            try:
                while True:
                    data = self.client_socket.recv(1024)
                    if not data:
                        break
                    fen_str = data.decode('utf-8')
                    self.received_fen.emit(fen_str)
                    self.send_current_state()
            finally:
                self.client_socket.close()

    def send_current_state(self):
        if self.client_socket:
            fen = turn.last_moves[:1]
            which_turn = "White" if turn.is_white_move else "Black"
            message = f"{fen} | Current turn: {which_turn}"
            self.client_socket.sendall(message.encode('utf-8'))

    def send_message(self, message):
        if self.client_socket:
            self.client_socket.sendall(message.encode('utf-8'))


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

class AIWorker(QThread):
    new_fen_signal = pyqtSignal(str)  # Signal to send FEN string to the main thread
    def run(self):
        while True:
            time.sleep(0.5)  # Check condition half a second
            if turn.ai_player and turn.is_white_move:
                self.parent().make_ai_move()
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
        self.fen_db = sqllite3_database.FenDatabase('fen_database.db')
        self.fen_db.clear_database()  # Clear the database at the start of the program

        self.setWindowTitle("Gra w szachy")
        self.setGeometry(100, 100, 800, 600)

        self.chessboard = Chessboard("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
        self.view = QGraphicsView(self.chessboard, self)
        self.setCentralWidget(self.view)

        self.settings = {
            "ip": "",
            "port": "",
            "mode": "2-player"  # Default mode
        }
        # self.load_settings()

        # Create a dock widget
        self.dock_widget = QDockWidget("Game Status", self)
        self.dock_widget.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        # Widget to hold content in the dock widget
        dock_content = QWidget()
        self.dock_widget.setWidget(dock_content)
        layout = QVBoxLayout()
        dock_content.setLayout(layout)

        # Button for Two-Player Mode
        self.two_player_mode_button = QPushButton("Two-Player Mode")
        layout.addWidget(self.two_player_mode_button)
        self.two_player_mode_button.clicked.connect(self.switch_to_two_player_mode)

        # Button for AI Mode
        self.ai_mode_button = QPushButton("AI Mode")
        layout.addWidget(self.ai_mode_button)
        self.ai_mode_button.clicked.connect(self.switch_to_ai_mode)

        # Label to display the current turn
        self.turn_label = QLabel()
        layout.addWidget(self.turn_label)

        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock_widget)

        # Input field for IP address
        self.ip_label = QLabel("IP Address:")
        layout.addWidget(self.ip_label)
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("Enter IP address")
        layout.addWidget(self.ip_input)

        # Input field for Port
        self.port_label = QLabel("Port:")
        layout.addWidget(self.port_label)
        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText("Enter port number")
        layout.addWidget(self.port_input)

        # Button to update IP and Port
        self.update_ipport_button = QPushButton("Update IP and Port")
        layout.addWidget(self.update_ipport_button)
        self.update_ipport_button.clicked.connect(self.update_ipport_from_input)

        # Start the thread to update turns
        self.turn_thread = TurnWorker()
        self.turn_thread.update_turn.connect(self.update_turn)
        self.turn_thread.start()

        # Load Last FEN Button
        self.load_last_fen_button = QPushButton("Load Last Move")
        layout.addWidget(self.load_last_fen_button)
        self.load_last_fen_button.clicked.connect(self.load_and_display_last_fen)

        self.fen_label = QLabel("FEN")
        layout.addWidget(self.fen_label)
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

        self.server_thread = ServerThread('127.0.0.1', 65432)  # Przykładowy IP i port
        self.server_thread.received_fen.connect(self.update_board_from_fen_ip)
        self.server_thread.start()

        self.ai_worker = AIWorker()
        self.ai_worker.setParent(self)
        self.ai_worker.new_fen_signal.connect(self.update_board)
        self.ai_worker.start()
    def update_ipport_from_input(self):
        self.settings["ip"] = self.ip_input.text().strip()  # Use strip() to remove any leading/trailing whitespace
        self.settings["port"] = self.port_input.text().strip()
        self.save_settings()

    def save_settings(self):
        with open('settings.json', 'w') as f:
            json.dump(self.settings, f, indent=4)

    def load_settings(self):
        try:
            with open('settings.json', 'r') as f:
                self.settings = json.load(f)
            # Update the UI based on loaded settings
            self.ip_input.setText(self.settings.get("ip", ""))
            self.port_input.setText(self.settings.get("port", ""))
            # Update mode based on settings, if necessary
        except FileNotFoundError:
            pass  # File not found, will use default settings

    def switch_to_two_player_mode(self):
        self.settings["mode"] = "2-player"
        self.save_settings()
        # Additional logic for switching to two-player mode...

    def switch_to_ai_mode(self):
        self.settings["mode"] = "AI"
        turn.ai_player = True
        self.save_settings()

    def load_and_display_last_fen(self):
        last_fen = self.fen_db.get_last_fen_string()
        if last_fen:
            self.update_board(last_fen)
            self.fen_db.delete_fen_string(last_fen)  # Delete the FEN string after displaying it
            # Additional logic as needed...
        else:
            self.show_message("No previous moves found in the database.")

    def set_clock_mode(self, mode):
        self.clock_thread.set_mode(mode)

    def update_board_from_fen(self):
        fen_str = self.fen_input.text()  # Get the FEN string from QLineEdit
        self.update_board(fen_str)  # Call the method to update the board with this FEN string

    def update_board_from_fen_ip(self, fen):
        if self.validate_fen(fen):
            print("lol")
            print(fen)
            self.update_board(fen)
            if not turn.is_white_move:  # Zakładając, że 'is_white_move' jest True, gdy ruch mają białe
                self.server_thread.send_message("Aktualnie ruch mają czarne. Ruch bialych jest oczekiwany.")
                return
            self.fen_input.setText(fen)  # Aktualizuje pole tekstowe z FEN
            self.update_board(fen)  # Aktualizuje planszę
        else:
            self.server_thread.send_message("Wiadomosc wyslana.")
            self.show_message(f"Otrzymano wiadomosc: {fen}")

    def validate_fen(self, fen):
        """Sprawdza, czy notacja FEN jest prawidłowa."""
        try:
            board = chess.Board(fen)
            return True
        except ValueError:
            return False

    def show_message(self, message):
        """Wyświetla komunikat o błędzie w formie MessageBox."""
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Warning)
        msgBox.setText(message)
        msgBox.setWindowTitle("Błąd Notacji FEN")
        msgBox.setStandardButtons(QMessageBox.Ok)
        msgBox.exec_()

    def show_winner_popup(self, message):
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setText(message)
        msgBox.setWindowTitle("Game Over")
        msgBox.setStandardButtons(QMessageBox.Ok)
        msgBox.exec_()

    def make_ai_move(self):
        if turn.ai_player:
            current_fen = turn.last_moves[-1]
            board = chess.Board(current_fen)
            best_move = self.select_best_move(board)
            if best_move:
                board.push(best_move)
                new_fen = board.fen()
                turn.last_moves.append(new_fen)
                self.ai_worker.new_fen_signal.emit(new_fen)
    def alpha_beta(self,board, depth, alpha, beta, maximizing_player):
        if depth == 0 or board.is_game_over():
            return self.evaluate_board(board)

        if maximizing_player:
            max_eval = float('-inf')
            for move in board.legal_moves:
                board.push(move)
                eval = self.alpha_beta(board, depth - 1, alpha, beta, False)
                board.pop()
                max_eval = max(max_eval, eval)
                alpha = max(alpha, eval)
                if beta <= alpha:
                    break
            return max_eval
        else:
            min_eval = float('inf')
            for move in board.legal_moves:
                board.push(move)
                eval = self.alpha_beta(board, depth - 1, alpha, beta, True)
                board.pop()
                min_eval = min(min_eval, eval)
                beta = min(beta, eval)
                if beta <= alpha:
                    break
            return min_eval

    def select_best_move(self, board, depth=3):
        best_move = None
        best_value = float('-inf')
        alpha = float('-inf')
        beta = float('inf')

        for move in board.legal_moves:
            board.push(move)
            move_value = self.alpha_beta(board, depth - 1, alpha, beta, False)
            board.pop()
            if move_value > best_value:
                best_value = move_value
                best_move = move
                alpha = max(alpha, move_value)

        return best_move
    def evaluate_board(self,board):
        # A simple evaluation function to score the board position
        # You can develop a more complex function based on position, material, etc.
        score = 0
        for piece in board.piece_map().values():
            if piece.color == chess.WHITE:
                score += 1
            else:
                score -= 1
        return score
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
