"""Chessmate engine core: board representation and legal move generation.

Pure standard-library Python. Squares are indexed 0-63 with a1 = 0 and
h8 = 63 (square = rank * 8 + file, where rank 0 is White's back rank).
Pieces are single characters: uppercase for White (``PNBRQK``) and
lowercase for Black (``pnbrqk``); empty squares are ``None``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

KNIGHT_DELTAS = ((1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1), (-2, 1), (-1, 2))
KING_DELTAS = ((1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1))
BISHOP_DIRS = ((1, 1), (1, -1), (-1, 1), (-1, -1))
ROOK_DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))
PROMOTIONS = ("q", "r", "b", "n")


def square_name(square: int) -> str:
    """Return the algebraic name of a square index, e.g. 4 -> 'e1'."""
    return chr(ord("a") + square % 8) + str(square // 8 + 1)


def parse_square(name: str) -> int:
    """Return the index of an algebraic square name, e.g. 'e1' -> 4."""
    if len(name) != 2 or name[0] not in "abcdefgh" or name[1] not in "12345678":
        raise ValueError(f"invalid square name: {name!r}")
    return (int(name[1]) - 1) * 8 + (ord(name[0]) - ord("a"))


def _colour_of(piece: str) -> str:
    return "w" if piece.isupper() else "b"


def _opponent(colour: str) -> str:
    return "b" if colour == "w" else "w"


@dataclass(frozen=True)
class Move:
    """A move from one square to another.

    ``promotion`` is one of 'q', 'r', 'b', 'n' (always lowercase) or None.
    ``is_en_passant`` and ``is_castling`` mark the two special pawn/king
    moves whose side effects :meth:`Board.make_move` must apply.
    """

    from_square: int
    to_square: int
    promotion: Optional[str] = None
    is_en_passant: bool = False
    is_castling: bool = False

    def uci(self) -> str:
        text = square_name(self.from_square) + square_name(self.to_square)
        if self.promotion:
            text += self.promotion
        return text

    @classmethod
    def from_uci(cls, text: str) -> "Move":
        if len(text) not in (4, 5):
            raise ValueError(f"invalid UCI move: {text!r}")
        promotion = text[4].lower() if len(text) == 5 else None
        if promotion is not None and promotion not in PROMOTIONS:
            raise ValueError(f"invalid promotion piece in UCI move: {text!r}")
        return cls(parse_square(text[0:2]), parse_square(text[2:4]), promotion)

    def __str__(self) -> str:
        return self.uci()


class Board:
    """A chess position with FEN I/O and fully legal move generation."""

    def __init__(self, fen: str = START_FEN) -> None:
        self.squares: List[Optional[str]] = [None] * 64
        self.turn: str = "w"
        self.castling: str = ""  # subset of "KQkq", in that order
        self.ep_square: Optional[int] = None
        self.halfmove_clock: int = 0
        self.fullmove_number: int = 1
        self._load_fen(fen)

    # ---------------------------------------------------------------- FEN

    def _load_fen(self, fen: str) -> None:
        parts = fen.split()
        if len(parts) != 6:
            raise ValueError(f"FEN must have 6 fields: {fen!r}")
        placement, turn, castling, ep, halfmove, fullmove = parts
        ranks = placement.split("/")
        if len(ranks) != 8:
            raise ValueError(f"FEN placement must have 8 ranks: {fen!r}")
        self.squares = [None] * 64
        for row, rank_text in enumerate(ranks):
            rank = 7 - row  # FEN lists rank 8 first
            file_ = 0
            for ch in rank_text:
                if ch.isdigit():
                    file_ += int(ch)
                elif ch in "PNBRQKpnbrqk":
                    if file_ > 7:
                        raise ValueError(f"FEN rank overflows: {fen!r}")
                    self.squares[rank * 8 + file_] = ch
                    file_ += 1
                else:
                    raise ValueError(f"invalid FEN piece character: {ch!r}")
            if file_ != 8:
                raise ValueError(f"FEN rank does not cover 8 files: {fen!r}")
        if turn not in ("w", "b"):
            raise ValueError(f"invalid FEN side to move: {turn!r}")
        self.turn = turn
        if castling == "-":
            self.castling = ""
        else:
            if any(c not in "KQkq" for c in castling):
                raise ValueError(f"invalid FEN castling field: {castling!r}")
            self.castling = "".join(c for c in "KQkq" if c in castling)
        self.ep_square = None if ep == "-" else parse_square(ep)
        self.halfmove_clock = int(halfmove)
        self.fullmove_number = int(fullmove)

    def fen(self) -> str:
        rows = []
        for rank in range(7, -1, -1):
            row = ""
            empty = 0
            for file_ in range(8):
                piece = self.squares[rank * 8 + file_]
                if piece is None:
                    empty += 1
                    continue
                if empty:
                    row += str(empty)
                    empty = 0
                row += piece
            if empty:
                row += str(empty)
            rows.append(row)
        castling = self.castling or "-"
        ep = square_name(self.ep_square) if self.ep_square is not None else "-"
        return (
            f"{'/'.join(rows)} {self.turn} {castling} {ep} "
            f"{self.halfmove_clock} {self.fullmove_number}"
        )

    def copy(self) -> "Board":
        clone = Board.__new__(Board)
        clone.squares = list(self.squares)
        clone.turn = self.turn
        clone.castling = self.castling
        clone.ep_square = self.ep_square
        clone.halfmove_clock = self.halfmove_clock
        clone.fullmove_number = self.fullmove_number
        return clone

    # ------------------------------------------------------------ attacks

    def king_square(self, colour: str) -> int:
        target = "K" if colour == "w" else "k"
        return self.squares.index(target)

    def is_square_attacked(self, square: int, by_colour: str) -> bool:
        file_, rank = square % 8, square // 8
        # Pawns: a white pawn attacks from one rank below the target.
        pawn = "P" if by_colour == "w" else "p"
        pawn_rank = rank - 1 if by_colour == "w" else rank + 1
        if 0 <= pawn_rank < 8:
            for df in (-1, 1):
                f = file_ + df
                if 0 <= f < 8 and self.squares[pawn_rank * 8 + f] == pawn:
                    return True
        knight = "N" if by_colour == "w" else "n"
        for df, dr in KNIGHT_DELTAS:
            f, r = file_ + df, rank + dr
            if 0 <= f < 8 and 0 <= r < 8 and self.squares[r * 8 + f] == knight:
                return True
        king = "K" if by_colour == "w" else "k"
        for df, dr in KING_DELTAS:
            f, r = file_ + df, rank + dr
            if 0 <= f < 8 and 0 <= r < 8 and self.squares[r * 8 + f] == king:
                return True
        bishop_like = {"B", "Q"} if by_colour == "w" else {"b", "q"}
        rook_like = {"R", "Q"} if by_colour == "w" else {"r", "q"}
        for directions, targets in ((BISHOP_DIRS, bishop_like), (ROOK_DIRS, rook_like)):
            for df, dr in directions:
                f, r = file_ + df, rank + dr
                while 0 <= f < 8 and 0 <= r < 8:
                    piece = self.squares[r * 8 + f]
                    if piece is not None:
                        if piece in targets:
                            return True
                        break
                    f += df
                    r += dr
        return False

    def is_in_check(self, colour: Optional[str] = None) -> bool:
        colour = colour or self.turn
        return self.is_square_attacked(self.king_square(colour), _opponent(colour))

    # ------------------------------------------------------- move making

    def make_move(self, move: Move) -> None:
        """Apply a move, updating all game state. Assumes it is legal."""
        piece = self.squares[move.from_square]
        if piece is None:
            raise ValueError(f"no piece on {square_name(move.from_square)}")
        captured = self.squares[move.to_square]
        if move.is_en_passant:
            cap_sq = move.to_square - 8 if piece == "P" else move.to_square + 8
            captured = self.squares[cap_sq]
            self.squares[cap_sq] = None
        self.squares[move.from_square] = None
        if move.promotion:
            self.squares[move.to_square] = (
                move.promotion.upper() if piece.isupper() else move.promotion
            )
        else:
            self.squares[move.to_square] = piece
        if move.is_castling:  # move the rook alongside the king
            rank = move.from_square // 8
            if move.to_square % 8 == 6:  # kingside: rook h-file -> f-file
                rook_from, rook_to = rank * 8 + 7, rank * 8 + 5
            else:  # queenside: rook a-file -> d-file
                rook_from, rook_to = rank * 8 + 0, rank * 8 + 3
            self.squares[rook_to] = self.squares[rook_from]
            self.squares[rook_from] = None
        # Castling rights: lost when the king or a home rook moves, or a
        # home rook is captured.
        rights = self.castling
        if piece == "K":
            rights = rights.replace("K", "").replace("Q", "")
        elif piece == "k":
            rights = rights.replace("k", "").replace("q", "")
        for home, flag in ((0, "Q"), (7, "K"), (56, "q"), (63, "k")):
            if move.from_square == home or move.to_square == home:
                rights = rights.replace(flag, "")
        self.castling = rights
        # A new en-passant target exists only after a double pawn push.
        self.ep_square = None
        if piece.upper() == "P" and abs(move.to_square - move.from_square) == 16:
            self.ep_square = (move.from_square + move.to_square) // 2
        if piece.upper() == "P" or captured is not None:
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1
        if self.turn == "b":
            self.fullmove_number += 1
        self.turn = _opponent(self.turn)

    # --------------------------------------------------- move generation

    def _pseudo_legal_moves(self) -> List[Move]:
        moves: List[Move] = []
        us = self.turn
        for square, piece in enumerate(self.squares):
            if piece is None or _colour_of(piece) != us:
                continue
            file_, rank = square % 8, square // 8
            kind = piece.upper()
            if kind == "P":
                self._pawn_moves(square, file_, rank, us, moves)
            elif kind == "N":
                self._step_moves(square, file_, rank, us, KNIGHT_DELTAS, moves)
            elif kind == "K":
                self._step_moves(square, file_, rank, us, KING_DELTAS, moves)
                self._castling_moves(square, us, moves)
            elif kind in ("B", "R", "Q"):
                directions = ()
                if kind in ("B", "Q"):
                    directions += BISHOP_DIRS
                if kind in ("R", "Q"):
                    directions += ROOK_DIRS
                self._slide_moves(square, file_, rank, us, directions, moves)
        return moves

    def _pawn_moves(self, square, file_, rank, us, moves) -> None:
        step = 8 if us == "w" else -8
        start_rank = 1 if us == "w" else 6
        last_rank = 7 if us == "w" else 0
        one = square + step
        if self.squares[one] is None:
            self._add_pawn_move(square, one, last_rank, moves)
            two = square + 2 * step
            if rank == start_rank and self.squares[two] is None:
                moves.append(Move(square, two))
        for df in (-1, 1):
            f = file_ + df
            if not (0 <= f < 8):
                continue
            target = one + df
            victim = self.squares[target]
            if victim is not None and _colour_of(victim) != us:
                self._add_pawn_move(square, target, last_rank, moves)
            elif target == self.ep_square:
                moves.append(Move(square, target, is_en_passant=True))

    @staticmethod
    def _add_pawn_move(from_sq, to_sq, last_rank, moves) -> None:
        if to_sq // 8 == last_rank:
            for promotion in PROMOTIONS:
                moves.append(Move(from_sq, to_sq, promotion=promotion))
        else:
            moves.append(Move(from_sq, to_sq))

    def _step_moves(self, square, file_, rank, us, deltas, moves) -> None:
        for df, dr in deltas:
            f, r = file_ + df, rank + dr
            if 0 <= f < 8 and 0 <= r < 8:
                target = r * 8 + f
                victim = self.squares[target]
                if victim is None or _colour_of(victim) != us:
                    moves.append(Move(square, target))

    def _slide_moves(self, square, file_, rank, us, directions, moves) -> None:
        for df, dr in directions:
            f, r = file_ + df, rank + dr
            while 0 <= f < 8 and 0 <= r < 8:
                target = r * 8 + f
                victim = self.squares[target]
                if victim is None:
                    moves.append(Move(square, target))
                else:
                    if _colour_of(victim) != us:
                        moves.append(Move(square, target))
                    break
                f += df
                r += dr

    def _castling_moves(self, square, us, moves) -> None:
        them = _opponent(us)
        if us == "w" and square == 4:  # e1
            options = (("K", 7, (5, 6), (4, 5, 6), 6), ("Q", 0, (1, 2, 3), (4, 3, 2), 2))
            rook = "R"
        elif us == "b" and square == 60:  # e8
            options = (("k", 63, (61, 62), (60, 61, 62), 62), ("q", 56, (57, 58, 59), (60, 59, 58), 58))
            rook = "r"
        else:
            return
        for flag, rook_sq, empty_sqs, safe_sqs, king_to in options:
            if flag not in self.castling or self.squares[rook_sq] != rook:
                continue
            if any(self.squares[s] is not None for s in empty_sqs):
                continue
            if any(self.is_square_attacked(s, them) for s in safe_sqs):
                continue
            moves.append(Move(square, king_to, is_castling=True))

    def legal_moves(self) -> List[Move]:
        """All fully legal moves for the side to move.

        Pseudo-legal moves are filtered by making each one and checking
        the mover's own king is not left under attack (this also covers
        pins and the en-passant discovered-check edge case). Castling
        transit squares are verified during generation.
        """
        legal = []
        us = self.turn
        for move in self._pseudo_legal_moves():
            clone = self.copy()
            clone.make_move(move)
            if not clone.is_square_attacked(clone.king_square(us), _opponent(us)):
                legal.append(move)
        return legal

    def find_move(self, uci: str) -> Move:
        """Return the legal move matching a UCI string, or raise ValueError."""
        wanted = Move.from_uci(uci)
        for move in self.legal_moves():
            if (
                move.from_square == wanted.from_square
                and move.to_square == wanted.to_square
                and move.promotion == wanted.promotion
            ):
                return move
        raise ValueError(f"illegal move {uci!r} in position {self.fen()}")


def perft(board: Board, depth: int) -> int:
    """Count leaf nodes of the legal move tree — a correctness check."""
    if depth == 0:
        return 1
    total = 0
    for move in board.legal_moves():
        clone = board.copy()
        clone.make_move(move)
        total += perft(clone, depth - 1)
    return total
