"""Chessmate engine brain: static evaluation and alpha-beta search.

Pure standard-library Python, built on :mod:`chessmate.board`.
Evaluation is in centipawns from **White's** point of view: material
values plus piece-square tables that reward good development squares.
Search is negamax with alpha-beta pruning and capture-first move
ordering. Checkmate scores dominate every material score, and faster
mates score higher than slower ones.

Scope is deliberately simple and honest: no quiescence search, no
transposition table, no opening book, and no draw handling beyond
stalemate scoring 0 (fifty-move and repetition draws are not detected).
"""

from __future__ import annotations

from typing import List, Optional

from .board import Board, Move

PIECE_VALUES = {"P": 100, "N": 320, "B": 330, "R": 500, "Q": 900, "K": 0}

# A mate is worth far more than any reachable material swing.
MATE_SCORE = 100_000
_INFINITY = 10 * MATE_SCORE

# Piece-square tables in centipawns, written from White's perspective
# with rank 8 first (the way they are conventionally printed). Values
# follow the classic simplified-evaluation tables: pawns are pushed
# toward promotion, knights belong near the centre, the king is told
# to stay tucked away in a corner.
_PAWN_PST = (
    0, 0, 0, 0, 0, 0, 0, 0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
    5, 5, 10, 25, 25, 10, 5, 5,
    0, 0, 0, 20, 20, 0, 0, 0,
    5, -5, -10, 0, 0, -10, -5, 5,
    5, 10, 10, -20, -20, 10, 10, 5,
    0, 0, 0, 0, 0, 0, 0, 0,
)
_KNIGHT_PST = (
    -50, -40, -30, -30, -30, -30, -40, -50,
    -40, -20, 0, 0, 0, 0, -20, -40,
    -30, 0, 10, 15, 15, 10, 0, -30,
    -30, 5, 15, 20, 20, 15, 5, -30,
    -30, 0, 15, 20, 20, 15, 0, -30,
    -30, 5, 10, 15, 15, 10, 5, -30,
    -40, -20, 0, 5, 5, 0, -20, -40,
    -50, -40, -30, -30, -30, -30, -40, -50,
)
_BISHOP_PST = (
    -20, -10, -10, -10, -10, -10, -10, -20,
    -10, 0, 0, 0, 0, 0, 0, -10,
    -10, 0, 5, 10, 10, 5, 0, -10,
    -10, 5, 5, 10, 10, 5, 5, -10,
    -10, 0, 10, 10, 10, 10, 0, -10,
    -10, 10, 10, 10, 10, 10, 10, -10,
    -10, 5, 0, 0, 0, 0, 5, -10,
    -20, -10, -10, -10, -10, -10, -10, -20,
)
_ROOK_PST = (
    0, 0, 0, 0, 0, 0, 0, 0,
    5, 10, 10, 10, 10, 10, 10, 5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    0, 0, 0, 5, 5, 0, 0, 0,
)
_QUEEN_PST = (
    -20, -10, -10, -5, -5, -10, -10, -20,
    -10, 0, 0, 0, 0, 0, 0, -10,
    -10, 0, 5, 5, 5, 5, 0, -10,
    -5, 0, 5, 5, 5, 5, 0, -5,
    0, 0, 5, 5, 5, 5, 0, -5,
    -10, 5, 5, 5, 5, 5, 0, -10,
    -10, 0, 5, 0, 0, 0, 0, -10,
    -20, -10, -10, -5, -5, -10, -10, -20,
)
_KING_PST = (
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -20, -30, -30, -40, -40, -30, -30, -20,
    -10, -20, -20, -20, -20, -20, -20, -10,
    20, 20, 0, 0, 0, 0, 20, 20,
    20, 30, 10, 0, 0, 10, 30, 20,
)
_PST = {
    "P": _PAWN_PST,
    "N": _KNIGHT_PST,
    "B": _BISHOP_PST,
    "R": _ROOK_PST,
    "Q": _QUEEN_PST,
    "K": _KING_PST,
}


def _pst_value(kind: str, square: int, is_white: bool) -> int:
    """Piece-square bonus for ``kind`` on ``square``.

    The tables are printed from White's side with rank 8 first. A white
    piece on rank ``r`` (0 = rank 1) reads row ``7 - r``; a black piece
    reads row ``r`` — the same table seen from Black's side of the board.
    """
    file_, rank = square % 8, square // 8
    row = 7 - rank if is_white else rank
    return _PST[kind][row * 8 + file_]


def evaluate(board: Board) -> int:
    """Static evaluation of ``board`` in centipawns, White-positive.

    Positive means White is better, negative means Black is better.
    Material plus piece-square bonuses only; checkmate/stalemate are
    the search's concern, not this function's.
    """
    score = 0
    for square, piece in enumerate(board.squares):
        if piece is None:
            continue
        kind = piece.upper()
        value = PIECE_VALUES[kind] + _pst_value(kind, square, piece.isupper())
        score += value if piece.isupper() else -value
    return score


def _side_score(board: Board) -> int:
    """Evaluation from the side-to-move's point of view (for negamax)."""
    score = evaluate(board)
    return score if board.turn == "w" else -score


def _ordered_moves(board: Board, moves: List[Move]) -> List[Move]:
    """Order moves for efficient pruning: best captures first.

    Captures are scored MVV-LVA style (most valuable victim, least
    valuable attacker), promotions get their new piece's value, and
    everything else keeps generation order behind the captures.
    """

    def key(move: Move) -> int:
        if move.is_en_passant:
            victim_value = PIECE_VALUES["P"]
        else:
            victim = board.squares[move.to_square]
            victim_value = PIECE_VALUES[victim.upper()] if victim else 0
        score = 0
        if victim_value:
            attacker = board.squares[move.from_square]
            attacker_value = PIECE_VALUES[attacker.upper()] if attacker else 0
            score = 10 * victim_value - attacker_value // 10
        if move.promotion:
            score += PIECE_VALUES[move.promotion.upper()]
        return score

    return sorted(moves, key=key, reverse=True)


def _negamax(board: Board, depth: int, alpha: int, beta: int, ply: int) -> int:
    """Best score the side to move can force, from its own viewpoint."""
    moves = board.legal_moves()
    if not moves:
        # No legal move: mated (bad, and worse the earlier it happens)
        # or stalemated (a draw).
        return -MATE_SCORE + ply if board.is_in_check(board.turn) else 0
    if depth == 0:
        return _side_score(board)
    best = -_INFINITY
    for move in _ordered_moves(board, moves):
        child = board.copy()
        child.make_move(move)
        score = -_negamax(child, depth - 1, -beta, -alpha, ply + 1)
        if score > best:
            best = score
        if best > alpha:
            alpha = best
        if alpha >= beta:
            break  # beta cutoff: the opponent will never allow this line
    return best


def best_move(board: Board, depth: int = 3) -> Optional[Move]:
    """Return the engine's chosen move for the side to move.

    ``depth`` is in plies (half-moves); the default of 3 looks two of
    its own moves ahead with the replies in between. Returns None when
    the game is already over (checkmate or stalemate).
    """
    moves = board.legal_moves()
    if not moves:
        return None
    best: Optional[Move] = None
    best_score = -_INFINITY
    alpha = -_INFINITY
    for move in _ordered_moves(board, moves):
        child = board.copy()
        child.make_move(move)
        score = -_negamax(child, depth - 1, -_INFINITY, -alpha, 1)
        if score > best_score:
            best_score = score
            best = move
        if score > alpha:
            alpha = score
    return best
