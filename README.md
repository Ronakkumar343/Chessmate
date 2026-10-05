# ♟️ Chessmate

A chess project built in stages by **Ronak Kumar**: first a correct Python
engine core, then a playable game and interface on top of it.

> **Status: 🚧 in development.** The Python engine core (step 1 below) is in
> the repo and tested. The web app, Stockfish integration and the rest of
> the feature list are still the build plan, not shipped software yet.

## ✅ What's built: Python engine core

`chessmate/board.py` — pure standard-library Python, no dependencies:

- **Board representation** — 64-square board with full FEN import/export
- **Legal move generation** for every piece, including:
  - castling (with the through-check / out-of-check / blocked rules)
  - en passant (including the rare pinned en-passant case)
  - pawn promotion to queen, rook, bishop or knight
  - pins and king safety — a move that leaves your king in check is
    never generated
- **Move application** with castling rights, en-passant targets and the
  halfmove/fullmove clocks kept up to date

Correctness is checked with `perft` node counts, the standard reference
test for move generators. The engine reproduces the published counts
exactly, including the dense "Kiwipete" test position
(perft(3) = 97,862) and the Chess Programming Wiki en-passant position
(perft(4) = 43,238).

### Run the tests

```bash
python -m unittest discover -s tests -v
```

23 unit tests cover FEN round-trips, perft counts, castling rules,
en passant (capture, pin legality), promotion and pinned pieces.

### Use it

```python
from chessmate import Board

board = Board()                       # standard starting position
print(len(board.legal_moves()))       # 20
board.make_move(board.find_move("e2e4"))
print(board.fen())
# rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1
```

## 🛣️ Build plan (next steps)

1. ✅ Engine core: board + legal move generation
2. ⬜ Check, checkmate and stalemate detection
3. ⬜ Simple evaluation + minimax opponent, playable in the terminal
4. ⬜ Web app: local multiplayer, Stockfish-powered AI opponents across
   five difficulty tiers, live move evaluation, ELO tracking and
   Bot Council commentary

## 👤 Author

Built by **Ronak Kumar** — student developer from Mithi, Pakistan, working
toward Computer Science at MIT.
