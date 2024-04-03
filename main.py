from PyQt5.QtWidgets import QApplication
from chess_game import ChessGame
import sys


def main():
    app = QApplication(sys.argv)
    game = ChessGame()
    game.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
