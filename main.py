from PyQt5.QtWidgets import QApplication
from chess_game import ChessGame
import sys
import xml_move_history

def main():
    fen_xml_db = xml_move_history.FenXMLDatabase()
    fen_xml_db.clear_file()
    app = QApplication(sys.argv)
    game = ChessGame()
    game.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
