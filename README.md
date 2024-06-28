# Chess App in PyQt5
A chess app in python using PyQt5

## Overview
The app allows players to play chess on one computer or by connecting through tcp/ip. Playing on one computer allows players to move on the map check possible moves and use multiple clock variations. Playing through tcp/ip allows players to send FEN chess notation via terminal and updates the board accordingly.

<p align="center">
  <img src="https://github.com/Ramosa5/Chess-App/assets/108287744/a8dff59f-f930-4264-9909-8f44be3c0ab2)](https://github.com/Ramosa5/Chess-App/assets/108287744/54389b1d-0322-44d6-adaa-4852168ed8c1" width="400" alt="App view">
</p>

## Features
- A chess engine allowing playing with another player with multiple clock variations
- Highlighting possible moves
- Saving game history and allowing further replays
- A simple chess bot to play against
- Undoing moves or loading custom board states from FEN notations

<p align="center">
  <img src="https://github.com/Ramosa5/Chess-App/assets/108287744/54389b1d-0322-44d6-adaa-4852168ed8c1" width="400" alt="Move highlight">
</p>

## How it works
Pieces graphics are stored in .rc file. Each piece has its own class with possible movement variations.

```python
class Rook(DraggablePiece):
    def __init__(self, color, parent=None):
        image_path = f':/images/{color}_rook.png'
        self.color = color
        self.first_move = True
        super().__init__(image_path, parent)
```

Game options and current state are stored in turn.py

Chessboard class is responsible for creating the board and initiating new states.

```python
class Chessboard(QGraphicsScene):
    def __init__(self,fen, parent=None):
        super().__init__(parent)
        self.square_items = []  # Add a list to keep track of square items
        self.setBackgroundBrush(QBrush(QColor(210, 180, 140)))  # Set background color
        self.drawBoard()
        self.setupPieces(fen)
```
Game history and tcp/ip options are stored in xml files.
