from PyQt5.QtCore import QPointF
from PyQt5.QtWidgets import QGraphicsScene, QGraphicsPixmapItem
from PyQt5.QtGui import QBrush, QColor, QPixmap

import turn
from pieces import Pawn, Rook, Knight, Bishop, Queen, King
import items_rc

class Chessboard(QGraphicsScene):
    def __init__(self,fen, parent=None):
        super().__init__(parent)
        self.square_items = []  # Add a list to keep track of square items
        self.setBackgroundBrush(QBrush(QColor(210, 180, 140)))  # Set background color
        self.drawBoard()
        self.setupPieces(fen)

    def drawBoard(self):
        self.square_items = []  # Reset the list when redrawing the board
        board_size = 8
        square_size = 60
        self.colors = [QColor(255, 206, 158), QColor(209, 139, 71)]  # Store default colors

        for row in range(board_size):
            row_items = []
            for col in range(board_size):
                color = self.colors[(row + col) % 2]
                square = self.addRect(col * square_size, row * square_size, square_size, square_size,
                                      brush=QBrush(color))
                row_items.append(square)
            self.square_items.append(row_items)  # Add row of square items to the list

    def addPiece(self, row, col, image_path):
        piece = QGraphicsPixmapItem(QPixmap(image_path))
        piece.setPos(col * 60, row * 60)  # Zakładając, że rozmiar kwadratu to 60
        self.addItem(piece)

    def setupPieces(self, fen):
        parts = fen.split(' ')
        piece_positions = parts[0].split('/')
        active_color = parts[1]
        if active_color == 'w':
            turn.is_white_move = True
        else: turn.is_white_move = False
        castling_availability = parts[2]
        en_passant_target = parts[3]
        turn.en_passant_notation = en_passant_target
        turn.halfmoves = int(parts[4]) if len(parts) > 4 else 0
        turn.total_moves = int(parts[5]) if len(parts) > 5 else 1
        # Define a mapping from FEN notation to the Piece classes and their colors
        piece_map = {
            'p': (Pawn, 'black'), 'r': (Rook, 'black'), 'n': (Knight, 'black'), 'b': (Bishop, 'black'),
            'q': (Queen, 'black'), 'k': (King, 'black'),
            'P': (Pawn, 'white'), 'R': (Rook, 'white'), 'N': (Knight, 'white'), 'B': (Bishop, 'white'),
            'Q': (Queen, 'white'), 'K': (King, 'white')
        }

        for row, row_data in enumerate(piece_positions):
            col = 0
            for char in row_data:
                if char.isdigit():
                    # Skip the number of squares indicated by the digit
                    col += int(char)
                else:
                    # Retrieve the piece class and color, and create a new instance
                    piece_class, color = piece_map[char]
                    piece = piece_class(color)
                    piece.setPos(col * 60, row * 60)
                    self.addItem(piece)

                    if piece_class == Pawn and color == 'white' and row != 6:
                        piece.first_move = False
                        print("lol")
                    if piece_class == Pawn and color == 'black' and row != 1:
                        piece.first_move = False
                    if 'K' not in castling_availability:
                        if piece_class == Rook and color == 'white' and piece.pos() != QPointF(0 * 60, 7 * 60):
                            piece.first_move = False
                    if 'Q' not in castling_availability:
                        if piece_class == Rook and color == 'white' and piece.pos() != QPointF(7 * 60, 7 * 60):
                            piece.first_move = False
                    if 'k' not in castling_availability:
                        if piece_class == Rook and color == 'black' and piece.pos() != QPointF(0 * 60, 0 * 60):
                            piece.first_move = False
                    if 'q' not in castling_availability:
                        if piece_class == Rook and color == 'black' and piece.pos() != QPointF(7 * 60, 0 * 60):
                            piece.first_move = False
                    col += 1

