from PyQt5.QtWidgets import QGraphicsScene, QGraphicsPixmapItem
from PyQt5.QtGui import QBrush, QColor, QPixmap
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
        # if fen == "Default":
        for col, piece_type in enumerate([Rook, Knight, Bishop, Queen, King, Bishop, Knight, Rook]):
            piece = piece_type('white')
            piece.setPos(col * 60, 7 * 60)  # Rząd 1 dla białych większych figurek
            self.addItem(piece)

        # Ustawienie białych pionków
        for col in range(8):
            pawn = Pawn('white')
            pawn.setPos(col * 60, 6* 60)  # Rząd 2 dla białych pionków
            self.addItem(pawn)

        # Ustawienie czarnych pionków
        for col in range(8):
            pawn = Pawn('black')
            pawn.setPos(col * 60, 60)  # Rząd 7 dla czarnych pionków
            self.addItem(pawn)

        # Ustawienie czarnych figur
        for col, piece_type in enumerate([Rook, Knight, Bishop, Queen, King, Bishop, Knight, Rook]):
            piece = piece_type('black')
            piece.setPos(col * 60, 0)  # Rząd 8 dla czarnych większych figurek
            self.addItem(piece)

