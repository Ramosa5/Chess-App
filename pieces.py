from PyQt5.QtWidgets import QGraphicsPixmapItem, QGraphicsItem, QGraphicsRectItem, QMessageBox
from PyQt5.QtGui import QPixmap, QColor
from PyQt5.QtCore import QRectF, QPointF, pyqtSignal, QThread, QTimer
from PyQt5.QtCore import QObject, pyqtSignal
import turn


class DraggablePiece(QGraphicsPixmapItem):
    def __init__(self, image_path, parent=None):
        super().__init__(QPixmap(image_path), parent)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.original_position = self.pos()
        self.setOpacity(1.0)

    def mousePressEvent(self, event):
        if (self.color == 'white' and turn.is_white_move) or (self.color == 'black' and not turn.is_white_move):
            super().mousePressEvent(event)
            self.original_position = self.pos()
            self.setOpacity(0.5)

            self.highlight_moves()
        else:
            event.ignore()

    def mouseReleaseEvent(self, event):
        self.clear_highlights()
        super().mouseReleaseEvent(event)
        self.setOpacity(1.0)
        pos = self.pos()
        x = round(pos.x() / 60) * 60
        y = round(pos.y() / 60) * 60

        board_size = 8 * 60
        x = min(max(x, 0), board_size - 60)
        y = min(max(y, 0), board_size - 60)

        self.make_a_move(x, y)

    def setup_board_from_fen(self, fen):
        piece_map = {
            'P': ('Pawn', 'white'), 'R': ('Rook', 'white'), 'N': ('Knight', 'white'),
            'B': ('Bishop', 'white'), 'Q': ('Queen', 'white'), 'K': ('King', 'white'),
            'p': ('Pawn', 'black'), 'r': ('Rook', 'black'), 'n': ('Knight', 'black'),
            'b': ('Bishop', 'black'), 'q': ('Queen', 'black'), 'k': ('King', 'black')
        }

        # Clear the board or move all pieces to an 'off-board' position
        self.clear_board()

        ranks = fen.split(' ')[0].split('/')

        for y, rank in enumerate(ranks):
            x = 0
            for char in rank:
                if char.isdigit():
                    x += int(char)  # Skip empty squares
                else:
                    piece_type, color = piece_map[char]
                    self.move_piece_to(piece_type, color, x, 7 - y)
                    x += 1

    def move_piece_to(self, piece_type, color, x, y):
        # Find a piece of the specified type and color that's not already placed
        for item in self.stored_pieces:
            if isinstance(item, globals()[piece_type]) and item.color == color:
                item.setPos(x * 60, y * 60)
                return

    def position_to_tile(self, position):
        """
        Converts a QPointF position to a chessboard tile notation (e.g., 'e4').
        """
        file_number = int(position.x() // 60)  # Convert x position to file number (0-7)
        rank_number = 8 - int(position.y() // 60)  # Convert y position to rank number (1-8), inverted because y starts from the top

        # Convert file number to a letter ('a'-'h'), ASCII code for 'a' is 97
        file_letter = chr(file_number + 97)

        # Combine file letter and rank number to get the tile notation
        tile = f"{file_letter}{rank_number}"
        return tile

    def get_piece_at(self, x, y):
        # Convert x, y to scene coordinates if needed
        for item in self.scene().items(QRectF(x * 60, y * 60, 60, 60)):
            if isinstance(item, DraggablePiece):
                return item
        return None

    def get_castling_availability(self):
        # Initial positions for kings and rooks in standard chess setup
        kings = {'white': (4, 7), 'black': (4, 0)}
        rooks = {'white': [(0, 7), (7, 7)], 'black': [(0, 0), (7, 0)]}

        castling_rights = {'white': '', 'black': ''}

        for color in ['white', 'black']:
            king = self.get_piece_at(*kings[color])
            if isinstance(king, King) and king.first_move:
                for rook_pos in rooks[color]:
                    rook = self.get_piece_at(*rook_pos)
                    if isinstance(rook, Rook) and rook.first_move:
                        if rook_pos[0] == 0:  # Queenside
                            castling_rights[color] += 'Q' if color == 'white' else 'q'
                        else:  # Kingside
                            castling_rights[color] += 'K' if color == 'white' else 'k'

        castling = castling_rights['white'] + castling_rights['black']
        return castling if castling else '-'

    def export_to_fen(self):
        fen = ""
        for y in range(7, -1, -1):  # Start from the 8th rank to the 1st
            empty_squares = 0
            for x in range(8):  # Iterate over files from 'a' to 'h'
                item = self.get_piece_at(x, 7-y)
                if item is None:
                    empty_squares += 1
                else:
                    if empty_squares > 0:
                        fen += str(empty_squares)
                        empty_squares = 0
                    fen += self.piece_to_fen(item)
            if empty_squares > 0:
                fen += str(empty_squares)
            if y > 0:
                fen += "/"

        # Assuming you have a way to determine the active color
        active_color = 'w' if turn.is_white_move else 'b'
        castling = self.get_castling_availability()
        if turn.en_passant_notation is not None:
            en_pas = turn.en_passant_notation
        else:
            en_pas = '-'
        fen += f" {active_color} {castling} {en_pas} {turn.halfmoves} {turn.total_moves}"  # Default values for castling, en passant, etc.
        return fen

    def piece_to_fen(self, item):
        if isinstance(item, Pawn):
            return 'p' if item.color == 'black' else 'P'
        elif isinstance(item, Rook):
            return 'r' if item.color == 'black' else 'R'
        elif isinstance(item, Knight):
            return 'n' if item.color == 'black' else 'N'
        elif isinstance(item, Bishop):
            return 'b' if item.color == 'black' else 'B'
        elif isinstance(item, Queen):
            return 'q' if item.color == 'black' else 'Q'
        elif isinstance(item, King):
            return 'k' if item.color == 'black' else 'K'
        return ''

    def make_a_move(self, x, y):
        target_rect = QRectF(x, y, 60, 60)
        items_in_target = self.scene().items(target_rect)
        pieces_in_target = [item for item in items_in_target if isinstance(item, DraggablePiece) and item != self]

        if not self.is_king_in_check(self.color, self.original_position, QPointF(x, y)):
            if self.is_move_allowed(self.original_position, QPointF(x, y)):
                if isinstance(self, Pawn):
                    if self.color == 'black':
                        if y == 7*60:
                            self.promote_pawn(QPointF(x, y))
                    else:
                        if y == 0:
                            self.promote_pawn(QPointF(x, y))
                    if self.color == 'black':
                        if QPointF(x, y - 60) == turn.en_passant:
                            target_rect = QRectF(x, y - 60, 60, 60)
                            items_target = self.scene().items(target_rect)
                            pieces_target = [item for item in items_target if
                                                isinstance(item, DraggablePiece) and item != self]
                            self.scene().removeItem(pieces_target[0])
                    elif self.color == 'white':
                        if QPointF(x, y + 60) == turn.en_passant:
                            target_rect = QRectF(x, y + 60, 60, 60)
                            items_target = self.scene().items(target_rect)
                            pieces_target = [item for item in items_target if
                                             isinstance(item, DraggablePiece) and item != self]
                            self.scene().removeItem(pieces_target[0])

                if isinstance(self, King):
                    if abs(self.original_position.x() - x) == 2 * 60:  # Ruch o dwa pola w poziomie oznacza roszadę
                        rook_pos_x = 0 if x < self.original_position.x() else 7 * 60
                        rook_items = self.scene().items(QRectF(rook_pos_x, y, 60, 60))
                        rook = next((item for item in rook_items if isinstance(item, Rook)), None)
                        if rook:
                            self.perform_castling(rook)

                if pieces_in_target:  # There is a piece on the target square
                    target_piece = pieces_in_target[0]  # Assume there's only one piece on the target square
                    if self.color != target_piece.color:  # Check if the target piece is of the opposite color
                        self.scene().removeItem(target_piece)  # Capture the piece
                        turn.take = True
                        self.setPos(x, y)
                    else:
                        self.setPos(self.original_position)  # Move is not allowed if the piece is of the same color
                else:
                    self.setPos(x, y)
                turn.en_passant = None
                turn.en_passant_notation = None
                if not isinstance(self, Pawn) and not turn.take:
                    turn.halfmoves += 1
                else:
                    turn.halfmoves = 0
                if isinstance(self, Pawn) and abs(self.original_position.y() - y) == 2 * 60:
                    turn.en_passant = QPointF(x, y)
                    if self.color == 'white':
                        turn.en_passant_notation = self.position_to_tile(QPointF(x, y+60))
                    elif self.color == 'black':
                        turn.en_passant_notation = self.position_to_tile(QPointF(x, y-60))
                self.first_move = False
                turn.take = False
                turn.is_white_move = not turn.is_white_move
                if turn.is_white_move:
                    turn.total_moves+=1
                turn.last_moves.append(self.export_to_fen())
                print(self.export_to_fen())
                print(self.position_to_tile(self.pos()))

            else:
                self.setPos(self.original_position)

        if self.color == 'black':
            if self.is_checkmate('black') == 0:
                pass
            elif self.is_checkmate('black') == 1:
                turn.game_over = True
                self.show_winner_popup("Mat! Wygrywają czarne!")
            elif self.is_checkmate('black') == 2:
                turn.game_over = True
                self.show_winner_popup("Pat!")
        elif self.color == 'white':
            if self.is_checkmate('white') == 0:
                pass
            elif self.is_checkmate('white') == 1:
                turn.game_over = True
                self.show_winner_popup("Mat! Wygrywają Białe!")
            elif self.is_checkmate('white') == 2:
                turn.game_over = True
                self.show_winner_popup("Pat!")
        return True

    def check_a_move(self, x, y):
        target_rect = QRectF(x, y, 60, 60)
        items_in_target = self.scene().items(target_rect)
        pieces_in_target = [item for item in items_in_target if isinstance(item, DraggablePiece) and item != self]

        if not self.is_king_in_check(self.color, self.original_position, QPointF(x, y)):
            if self.is_move_allowed(self.original_position, QPointF(x, y)):
                if isinstance(self, King):
                    if abs(self.original_position.x() - x) == 2 * 60:  # Ruch o dwa pola w poziomie oznacza roszadę
                        rook_pos_x = 0 if x < self.original_position.x() else 7 * 60
                        rook_items = self.scene().items(QRectF(rook_pos_x, y, 60, 60))
                        rook = next((item for item in rook_items if isinstance(item, Rook)), None)
                        if rook:
                            return True

                if pieces_in_target:  # There is a piece on the target square
                    target_piece = pieces_in_target[0]  # Assume there's only one piece on the target square
                    if self.color != target_piece.color:  # Check if the target piece is of the opposite color
                        return True
                    else:
                        return False  # Move is not allowed if the piece is of the same color
                else:
                    return True
            else:
                return False
        return False

    def is_king_in_check(self, king_color, original_pos, target_pos):
        king = None
        attacking_pieces = []
        self.setPos(target_pos)
        target_rect = QRectF(target_pos.x(), target_pos.y(), 60, 60)
        items_in_target = self.scene().items(target_rect)
        pieces_in_target = [item for item in items_in_target if
                            isinstance(item, DraggablePiece) and item != self]
        if pieces_in_target:
            target_piece = pieces_in_target[0]  # Assume there's only one piece on the target square
            if self.color != target_piece.color:  # Check if the target piece is of the opposite color
                self.scene().removeItem(target_piece)
        # Find the king of the given color
        for item in self.scene().items():
            if isinstance(item, King) and item.color == king_color:
                king = item
                break

        king_pos = king.pos()

        # Analyze positions of all opposing pieces
        for item in self.scene().items():
            if isinstance(item, DraggablePiece) and item.color != king_color:
                if item.is_move_allowed(item.pos(), king_pos):
                    attacking_pieces.append(item)

        # Revert the piece to its original position if it was moved
        if original_pos is not None:
            self.setPos(original_pos)
        if pieces_in_target:
            self.scene().addItem(pieces_in_target[0])
        return len(attacking_pieces) > 0

    def is_checkmate(self, color):
        board_size = 8
        square_size = 60
        for item in self.scene().items():  # Przechodzenie przez wszystkie elementy na scenie
            if isinstance(item, DraggablePiece) and item.color != color:  # Sprawdzenie, czy element jest figurą
                for dx in range(-board_size + 1, board_size):
                    for dy in range(-board_size + 1, board_size):
                        pos = item.pos()
                        x = round(pos.x() / 60) * 60
                        y = round(pos.y() / 60) * 60
                        x = min(max(x, 0), board_size * 60 - 60)
                        y = min(max(y, 0), board_size * 60 - 60)
                        end_pos = QPointF(x + dx * square_size, y + dy * square_size)
                        if 0 <= end_pos.x() < board_size * square_size and 0 <= end_pos.y() < board_size * square_size:
                            # if end_pos == pos:
                            #     pass
                            item.original_position = item.pos()
                            if item.check_a_move(end_pos.x(), end_pos.y()):
                                return 0
                        else:
                            pass

        for item in self.scene().items():
            if isinstance(item, King) and item.color != color:
                king = item
                break

        king_pos = king.pos()

        for item in self.scene().items():
            if isinstance(item, DraggablePiece) and item.color == color:
                if item.is_move_allowed(item.pos(), king_pos):
                    return 1
        return 2

    def highlight_moves(self):
        self.clear_highlights()

        start_pos = self.pos()
        board_size = 8
        square_size = 60

        for dx in range(-board_size + 1, board_size):
            for dy in range(-board_size + 1, board_size):
                end_pos = QPointF(start_pos.x() + dx * square_size, start_pos.y() + dy * square_size)

                # Check if the move is within the board bounds
                if 0 <= end_pos.x() < board_size * square_size and 0 <= end_pos.y() < board_size * square_size:
                    # Check if the move is allowed for this piece
                    if self.check_a_move(end_pos.x(), end_pos.y()):
                        highlight = QGraphicsRectItem(end_pos.x(), end_pos.y(), square_size, square_size)
                        highlight.setBrush(QColor(0, 255, 0, 100))  # Use a green color with some transparency
                        self.scene().addItem(highlight)

    def clear_highlights(self):
        for item in self.scene().items():
            if isinstance(item, QGraphicsRectItem) and item.brush().color() == QColor(0, 255, 0, 100):
                self.scene().removeItem(item)

    def show_winner_popup(self, message):
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setText(message)
        msgBox.setWindowTitle("Game Over")
        msgBox.setStandardButtons(QMessageBox.Ok)
        msgBox.exec_()

class Pawn(DraggablePiece):
    def __init__(self, color, parent=None):
        image_path = f':/images/{color}_pawn.png'
        self.color = color
        self.first_move = True
        super().__init__(image_path, parent)

    def promote_pawn(self, target_pos):
        msgBox = QMessageBox()
        msgBox.setWindowTitle("Promotion")
        msgBox.setText("Choose piece for promotion:")
        queenButton = msgBox.addButton("Queen", QMessageBox.AcceptRole)
        rookButton = msgBox.addButton("Rook", QMessageBox.AcceptRole)
        bishopButton = msgBox.addButton("Bishop", QMessageBox.AcceptRole)
        knightButton = msgBox.addButton("Knight", QMessageBox.AcceptRole)
        msgBox.exec_()

        if msgBox.clickedButton() == queenButton:
            self.change_to_new_piece(Queen, target_pos)
        elif msgBox.clickedButton() == rookButton:
            self.change_to_new_piece(Rook, target_pos)
        elif msgBox.clickedButton() == bishopButton:
            self.change_to_new_piece(Bishop, target_pos)
        elif msgBox.clickedButton() == knightButton:
            self.change_to_new_piece(Knight, target_pos)

    def change_to_new_piece(self, new_piece_class, target_pos):
        new_piece = new_piece_class(self.color, self.parentItem())
        new_piece.setPos(target_pos)
        self.scene().addItem(new_piece)
        QTimer.singleShot(0, self.remove_self_from_scene)

    def remove_self_from_scene(self):
        if self.scene():
            self.scene().removeItem(self)

    def is_move_allowed(self, start_pos, end_pos):
        dx = start_pos.x() - end_pos.x()
        dy = start_pos.y() - end_pos.y()
        if dx == 0:
            target_rect = QRectF(end_pos.x(), end_pos.y(), 60, 60)
            items_in_target = self.scene().items(target_rect)
            pieces_in_target = [item for item in items_in_target if
                                isinstance(item, DraggablePiece) and item != self]
            if pieces_in_target:
                return False
        if self.color == 'black':
            sign = -1
        else:
            sign = 1
        if self.first_move:
            if (dy == 120 * sign or dy == 60 * sign) and (dx == 0):
                target_rect = QRectF(end_pos.x(), end_pos.y() + 60 * sign, 60, 60)
                items_in_target = self.scene().items(target_rect)
                pieces_in_target = [item for item in items_in_target if
                                    isinstance(item, DraggablePiece) and item != self]
                if pieces_in_target:
                    return False
                else:
                    return True
            if dy == 60 * sign and abs(dx) == 60:
                target_rect = QRectF(end_pos.x(), end_pos.y(), 60, 60)
                items_in_target = self.scene().items(target_rect)
                pieces_in_target = [item for item in items_in_target if
                                    isinstance(item, DraggablePiece) and item != self]
                if pieces_in_target or QPointF(end_pos.x(), end_pos.y() + sign*60) == turn.en_passant:
                    return True
        else:
            if dy == 60 * sign and abs(dx) == 60:
                target_rect = QRectF(end_pos.x(), end_pos.y(), 60, 60)
                items_in_target = self.scene().items(target_rect)
                pieces_in_target = [item for item in items_in_target if
                                    isinstance(item, DraggablePiece) and item != self]
                if pieces_in_target or QPointF(end_pos.x(), end_pos.y() + sign*60) == turn.en_passant:
                    return True
            elif dy == 60 * sign and dx == 0:
                target_rect = QRectF(end_pos.x(), end_pos.y(), 60, 60)
                items_in_target = self.scene().items(target_rect)
                pieces_in_target = [item for item in items_in_target if
                                    isinstance(item, DraggablePiece) and item != self]
                if pieces_in_target:
                    return False
                else:
                    return True


class Rook(DraggablePiece):
    def __init__(self, color, parent=None):
        image_path = f':/images/{color}_rook.png'
        self.color = color
        self.first_move = True
        super().__init__(image_path, parent)

    def is_move_allowed(self, start_pos, end_pos):
        if start_pos.x() != end_pos.x() and start_pos.y() != end_pos.y():
            return False
        target_rect = QRectF(end_pos.x(), end_pos.y(), 60, 60)
        items_in_target = self.scene().items(target_rect)
        pieces_in_target = [item for item in items_in_target if
                            isinstance(item, DraggablePiece) and item != self]
        if pieces_in_target and pieces_in_target[0].color == self.color:
            return False
        dx = int((end_pos.x() - start_pos.x()) / 60)
        dy = int((end_pos.y() - start_pos.y()) / 60)
        if dx == 0 and dy == 0:
            return False
        step_x = 0 if dx == 0 else (dx // abs(dx))
        step_y = 0 if dy == 0 else (dy // abs(dy))
        steps = max(abs(dx), abs(dy))

        for step in range(1, steps):
            next_x = start_pos.x() + step * step_x * 60
            next_y = start_pos.y() + step * step_y * 60
            target_rect = QRectF(next_x, next_y, 60, 60)
            items_in_target = self.scene().items(target_rect)

            pieces_in_target = [item for item in items_in_target if isinstance(item, DraggablePiece) and item != self]
            if pieces_in_target:
                return False
        return True


class Knight(DraggablePiece):
    def __init__(self, color, parent=None):
        image_path = f':/images/{color}_knight.png'
        self.color = color
        super().__init__(image_path, parent)

    def is_move_allowed(self, start_pos, end_pos):
        dx = abs(start_pos.x() - end_pos.x())
        dy = abs(start_pos.y() - end_pos.y())
        target_rect = QRectF(end_pos.x(), end_pos.y(), 60, 60)
        items_in_target = self.scene().items(target_rect)
        pieces_in_target = [item for item in items_in_target if
                            isinstance(item, DraggablePiece) and item != self]
        if pieces_in_target and pieces_in_target[0].color == self.color:
            return False
        return ((dx == 2 * dy) or (dy == 2 * dx)) and (dx + dy == 180)


class Bishop(DraggablePiece):
    def __init__(self, color, parent=None):
        image_path = f':/images/{color}_bishop.png'
        self.color = color
        super().__init__(image_path, parent)

    def is_move_allowed(self, start_pos, end_pos):
        dx = int((end_pos.x() - start_pos.x()) / 60)
        dy = int((end_pos.y() - start_pos.y()) / 60)
        if abs(dx) != abs(dy) or dx == 0:
            return False
        target_rect = QRectF(end_pos.x(), end_pos.y(), 60, 60)
        items_in_target = self.scene().items(target_rect)
        pieces_in_target = [item for item in items_in_target if
                            isinstance(item, DraggablePiece) and item != self]
        if pieces_in_target and pieces_in_target[0].color == self.color:
            return False

        step_x = dx // abs(dx)  # Ustala kierunek ruchu na osi X
        step_y = dy // abs(dy)  # Ustala kierunek ruchu na osi Y

        steps = abs(dx)  # Liczba kroków jest taka sama dla dx i dy, ponieważ ruch jest po przekątnej

        for step in range(1, steps):
            next_x = start_pos.x() + step * step_x * 60
            next_y = start_pos.y() + step * step_y * 60
            target_rect = QRectF(next_x, next_y, 60, 60)
            items_in_target = self.scene().items(target_rect)

            pieces_in_target = [item for item in items_in_target if isinstance(item, DraggablePiece) and item != self]
            if pieces_in_target:
                return False

        return True


class Queen(DraggablePiece):
    def __init__(self, color, parent=None):
        image_path = f':/images/{color}_queen.png'
        self.color = color
        super().__init__(image_path, parent)

    def is_move_allowed(self, start_pos, end_pos):
        dx = int((end_pos.x() - start_pos.x()) / 60)
        dy = int((end_pos.y() - start_pos.y()) / 60)
        target_rect = QRectF(end_pos.x(), end_pos.y(), 60, 60)
        items_in_target = self.scene().items(target_rect)
        pieces_in_target = [item for item in items_in_target if
                            isinstance(item, DraggablePiece) and item != self]
        if pieces_in_target and pieces_in_target[0].color == self.color:
            return False
        if dx == 0 and dy == 0:
            return False
        if dx == 0 or dy == 0:
            step_x = 0 if dx == 0 else (dx // abs(dx))
            step_y = 0 if dy == 0 else (dy // abs(dy))
            steps = max(abs(dx), abs(dy))

        elif abs(dx) == abs(dy):
            step_x = dx // abs(dx)
            step_y = dy // abs(dy)
            steps = abs(dx)

        else:
            return False

        for step in range(1, steps):
            next_x = start_pos.x() + step * step_x * 60
            next_y = start_pos.y() + step * step_y * 60

            target_rect = QRectF(next_x, next_y, 60, 60)
            items_in_target = self.scene().items(target_rect)

            pieces_in_target = [item for item in items_in_target if isinstance(item, DraggablePiece) and item != self]
            if pieces_in_target:
                return False

        return True


class King(DraggablePiece):
    def __init__(self, color, parent=None):
        image_path = f':/images/{color}_king.png'
        self.color = color
        self.first_move = True
        super().__init__(image_path, parent)

    def is_move_allowed(self, start_pos, end_pos):
        dx = abs(start_pos.x() - end_pos.x())
        dy = abs(start_pos.y() - end_pos.y())
        if dx == 0 and dy == 0:
            return False
        target_rect = QRectF(end_pos.x(), end_pos.y(), 60, 60)
        items_in_target = self.scene().items(target_rect)
        pieces_in_target = [item for item in items_in_target if
                            isinstance(item, DraggablePiece) and item != self]
        if pieces_in_target and pieces_in_target[0].color == self.color:
            return False
        if self.first_move and dx == 2 * 60 and dy == 0:
            return self.can_castle(start_pos, end_pos)
        if dx < 61 and dy < 61:
            return True
        return False

    def can_castle(self, start_pos, end_pos):
        if not self.first_move:
            return False
        direction = 1 if end_pos.x() > start_pos.x() else - 1
        for x in range(60, abs(int(end_pos.x() - start_pos.x())), 60):
            next_x = start_pos.x() + direction * x
            target_rect = QRectF(next_x, start_pos.y(), 60, 60)
            items_in_target = self.scene().items(target_rect)
            if any(isinstance(item, DraggablePiece) for item in items_in_target):
                return False  # Nie można roszować przez inne figury
            if self.is_king_in_check(self.color, start_pos, QPointF(next_x, start_pos.y())):
                return False
        rook_pos_x = 0 if direction == -1 else 7 * 60
        rook_items = self.scene().items(QRectF(rook_pos_x, start_pos.y(), 60, 60))
        rook = next((item for item in rook_items if isinstance(item, Rook) and item.first_move), None)

        return rook is not None

    def perform_castling(self, rook):
        if rook.pos().x() > self.pos().x():  # Roszada krótka
            self.setPos(self.pos().x() + 2 * 60, self.pos().y())
            rook.setPos(rook.pos().x() - 2 * 60, rook.pos().y())
        else:  # Roszada długa
            self.setPos(self.pos().x() - 2 * 60, self.pos().y())
            rook.setPos(rook.pos().x() + 3 * 60, rook.pos().y())
        self.first_move = False
        rook.first_move = False

    def is_square_attacked(self, position, attacker_color):
        for item in self.scene().items():
            if isinstance(item, DraggablePiece) and item.color == attacker_color:
                if item.is_move_allowed(item.pos(), position):
                    return True
        return False
