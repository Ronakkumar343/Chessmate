# ♟️ Chessmate

A chess project built in stages by **Ronak Kumar**: first a correct Python
engine core, then a playable game and interface on top of it.

> **Status: 🚧 in development.** The Python engine core and a playable
> terminal game (steps 1–3 below) are in the repo and tested. The web
> app, Stockfish integration and the rest of the feature list are still
> the build plan, not shipped software yet.

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
- **Game status** — `is_checkmate()`, `is_stalemate()`, `status()`
  ('checkmate' / 'stalemate' / 'check' / 'ongoing') and `outcome()`
  ('1-0' / '0-1' / '1/2-1/2' / None) for the side to move. Draw claims
  from the fifty-move rule or repetition are not covered yet.

Correctness is checked with `perft` node counts, the standard reference
test for move generators. The engine reproduces the published counts
exactly, including the dense "Kiwipete" test position
(perft(3) = 97,862) and the Chess Programming Wiki en-passant position
(perft(4) = 43,238).

## ✅ What's built: evaluation + minimax opponent

`chessmate/engine.py` gives the core a brain, still pure standard library:

- **Evaluation** — `evaluate(board)` scores a position in centipawns
  from White's point of view: material values plus piece-square tables
  that reward central knights, developed bishops and a safely tucked
  king. Symmetric positions score exactly 0.
- **Search** — `best_move(board, depth)` runs negamax with alpha-beta
  pruning and capture-first move ordering (MVV-LVA). Checkmate scores
  beat any material gain, and faster mates beat slower ones. Deliberately
  not included yet: quiescence search, transposition tables, opening
  books, and fifty-move / repetition draw detection.

### Play against it in the terminal

```bash
python -m chessmate.play            # you are White
python -m chessmate.play --black    # engine moves first
python -m chessmate.play --depth 2  # weaker/faster engine (default 3)
```

Enter moves in UCI notation — `e2e4`, `g1f3`, `e7e8q` to promote.
Type `moves` at your turn to list legal moves, `fen` to see the
position as FEN, `quit` to resign.

### Run the tests

```bash
python -m unittest discover -s tests -v
```

43 unit tests cover FEN round-trips, perft counts, castling rules,
en passant (capture, pin legality), promotion, pinned pieces, game
status (Fool's mate, Scholar's mate, classic stalemate), evaluation
symmetry, search tactics (mate in one, winning a hanging queen) and
scripted terminal games.

### Use it

```python
from chessmate import Board, best_move, evaluate

board = Board()                       # standard starting position
print(len(board.legal_moves()))       # 20
board.make_move(board.find_move("e2e4"))
print(board.fen())
# rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1
print(evaluate(board))                # 40 — White's pawn sits on a better square
print(best_move(board).uci())         # g8f6 — the engine's reply as Black
```

## 🛣️ Build plan (next steps)

1. ✅ Engine core: board + legal move generation
2. ✅ Check, checkmate and stalemate detection
3. ✅ Simple evaluation + minimax opponent, playable in the terminal
4. ⬜ Web app: local multiplayer, Stockfish-powered AI opponents across
   five difficulty tiers, live move evaluation, ELO tracking and
   Bot Council commentary

## 👤 Author

Built by **Ronak Kumar** — student developer from Mithi, Pakistan, working
toward Computer Science at MIT.
