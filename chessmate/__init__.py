"""Chessmate — a chess engine built in stages, in pure Python."""

from .board import Board, Move, perft, parse_square, square_name, START_FEN
from .engine import MATE_SCORE, best_move, evaluate

__all__ = [
    "Board",
    "Move",
    "perft",
    "parse_square",
    "square_name",
    "START_FEN",
    "MATE_SCORE",
    "best_move",
    "evaluate",
]
__version__ = "0.2.0"
