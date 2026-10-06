"""Play Chessmate in the terminal against the minimax engine.

Run from the repository root:

    python -m chessmate.play [--black] [--depth N]

You are White unless ``--black`` is given. Enter moves in UCI /
coordinate notation — ``e2e4``, ``g1f3``, ``e7e8q`` for a promotion.
At your prompt you can also type:

    moves   list your legal moves
    fen     show the current position as FEN
    quit    resign and leave

The engine (:mod:`chessmate.engine`) answers every move at the chosen
search depth; the default depth of 3 thinks for a few seconds in busy
middlegame positions on ordinary hardware.
"""

from __future__ import annotations

import argparse
from typing import Callable, Optional

from .board import Board
from .engine import best_move

InputFn = Callable[[str], str]
PrintFn = Callable[[str], None]


def render(board: Board) -> str:
    """Return an ASCII drawing of the board, rank 8 at the top."""
    lines = ["  a b c d e f g h"]
    for rank in range(7, -1, -1):
        cells = []
        for file_ in range(8):
            piece = board.squares[rank * 8 + file_]
            cells.append(piece if piece is not None else ".")
        lines.append(f"{rank + 1} {' '.join(cells)} {rank + 1}")
    lines.append("  a b c d e f g h")
    return "\n".join(lines)


def _announce_result(board: Board, print_fn: PrintFn) -> None:
    result = board.outcome()
    if board.is_checkmate():
        winner = "Black" if board.turn == "w" else "White"
        print_fn(f"Checkmate — {winner} wins. Result: {result}")
    else:
        print_fn(f"Stalemate — the game is a draw. Result: {result}")


def play_game(
    board: Optional[Board] = None,
    human_colour: str = "w",
    depth: int = 3,
    input_fn: InputFn = input,
    print_fn: PrintFn = print,
) -> Board:
    """Run one game and return the final board.

    ``input_fn``/``print_fn`` are injectable so tests can script a game
    without a terminal.
    """
    board = board if board is not None else Board()
    print_fn("Chessmate — type 'moves' for your legal moves, 'quit' to stop.")
    while True:
        state = board.status()
        if state in ("checkmate", "stalemate"):
            print_fn(render(board))
            _announce_result(board, print_fn)
            return board
        print_fn(render(board))
        if state == "check":
            side = "White" if board.turn == "w" else "Black"
            print_fn(f"{side} is in check.")
        if board.turn != human_colour:
            move = best_move(board, depth)
            if move is None:  # defensive; status() above already ended it
                return board
            print_fn(f"Engine plays {move.uci()}")
            board.make_move(move)
            continue
        try:
            text = input_fn("Your move: ").strip().lower()
        except EOFError:
            print_fn("")
            return board
        if text in ("quit", "exit", "resign"):
            print_fn("You resigned. The engine takes this one.")
            return board
        if text == "moves":
            legal = " ".join(sorted(m.uci() for m in board.legal_moves()))
            print_fn(f"Legal moves: {legal}")
            continue
        if text == "fen":
            print_fn(board.fen())
            continue
        try:
            board.make_move(board.find_move(text))
        except ValueError:
            print_fn(f"{text!r} is not a legal move here — try again.")
    return board


def main(argv: Optional[list] = None) -> None:
    parser = argparse.ArgumentParser(description="Play chess against Chessmate.")
    parser.add_argument(
        "--black",
        action="store_true",
        help="play as Black (the engine moves first as White)",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=3,
        help="engine search depth in plies (default: 3)",
    )
    parser.add_argument(
        "--fen",
        type=str,
        default=None,
        help="start from this FEN instead of the standard position",
    )
    args = parser.parse_args(argv)
    board = Board(args.fen) if args.fen else Board()
    play_game(
        board=board,
        human_colour="b" if args.black else "w",
        depth=args.depth,
    )


if __name__ == "__main__":
    main()
