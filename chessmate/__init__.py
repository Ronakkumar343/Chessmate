"""Chessmate — a chess engine built in stages, in pure Python."""

from .board import Board, Move, perft, parse_square, square_name, START_FEN

__all__ = ["Board", "Move", "perft", "parse_square", "square_name", "START_FEN"]
__version__ = "0.1.0"
