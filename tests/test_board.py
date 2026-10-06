"""Unit tests for the Chessmate engine core (board + legal move generation).

Run from the repository root with the standard library only:

    python -m unittest discover -s tests -v

Perft expectations are the long-established reference counts published on
the Chess Programming Wiki ("Perft Results" page).
"""

import unittest

from chessmate import Board, Move, perft

BARE_CASTLING = "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1"
KIWIPETE = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"
EP_PIN_POSITION = "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1"


def uci_set(board):
    return {move.uci() for move in board.legal_moves()}


def play(board, uci):
    board.make_move(board.find_move(uci))
    return board


class FenTests(unittest.TestCase):
    def test_start_position_round_trip(self):
        board = Board()
        self.assertEqual(
            board.fen(),
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        )

    def test_round_trip_various_positions(self):
        for fen in (BARE_CASTLING, KIWIPETE, EP_PIN_POSITION):
            self.assertEqual(Board(fen).fen(), fen)

    def test_invalid_fen_rejected(self):
        with self.assertRaises(ValueError):
            Board("not a fen")
        with self.assertRaises(ValueError):
            Board("8/8/8/8/8/8/8/8 w - - 0")  # missing a field


class MoveGenerationTests(unittest.TestCase):
    def test_start_position_has_20_moves(self):
        self.assertEqual(len(Board().legal_moves()), 20)

    def test_perft_start_position(self):
        board = Board()
        self.assertEqual(perft(board, 1), 20)
        self.assertEqual(perft(board, 2), 400)
        self.assertEqual(perft(board, 3), 8902)

    def test_perft_kiwipete(self):
        # Dense middlegame with castling, pins and captures on both sides.
        board = Board(KIWIPETE)
        self.assertEqual(perft(board, 1), 48)
        self.assertEqual(perft(board, 2), 2039)

    def test_perft_en_passant_pin_position(self):
        board = Board(EP_PIN_POSITION)
        self.assertEqual(perft(board, 1), 14)
        self.assertEqual(perft(board, 2), 191)
        self.assertEqual(perft(board, 3), 2812)

    def test_pinned_piece_cannot_expose_king(self):
        # White rook on e2 shields its king from the rook on e8: it may
        # slide along the e-file (or capture e8) but never sideways.
        board = Board("4r2k/8/8/8/8/8/4R3/4K3 w - - 0 1")
        moves = uci_set(board)
        self.assertNotIn("e2d2", moves)
        self.assertIn("e2e7", moves)
        self.assertIn("e2e8", moves)

    def test_king_cannot_move_into_check(self):
        board = Board("4r2k/8/8/8/8/8/8/4K3 w - - 0 1")
        moves = uci_set(board)
        self.assertNotIn("e1e2", moves)  # still on the rook's file
        self.assertIn("e1d1", moves)
        self.assertIn("e1f1", moves)


class PawnTests(unittest.TestCase):
    def test_double_push_sets_en_passant_square(self):
        board = play(Board(), "e2e4")
        self.assertEqual(board.ep_square, 20)  # e3
        self.assertEqual(board.turn, "b")

    def test_single_push_clears_en_passant_square(self):
        board = play(Board(), "e2e3")
        self.assertIsNone(board.ep_square)

    def test_en_passant_capture_removes_the_passed_pawn(self):
        board = Board("8/8/8/2kPp3/8/8/8/4K3 w - e6 0 1")
        self.assertIn("d5e6", uci_set(board))
        play(board, "d5e6")
        self.assertEqual(board.squares[44], "P")  # pawn landed on e6
        self.assertIsNone(board.squares[36])  # black pawn on e5 is gone

    def test_en_passant_that_exposes_king_is_illegal(self):
        # b5xc6 e.p. would remove both rank-5 pawns and open the h5 rook's
        # line to the white king on a5, so the capture must not be offered.
        board = Board("8/8/8/KPp4r/8/8/8/4k3 w - c6 0 1")
        moves = uci_set(board)
        self.assertNotIn("b5c6", moves)
        self.assertIn("b5b6", moves)  # the plain push stays legal

    def test_promotion_offers_all_four_pieces(self):
        board = Board("1r6/P7/8/8/8/8/k6K/8 w - - 0 1")
        moves = uci_set(board)
        for suffix in ("q", "r", "b", "n"):
            self.assertIn("a7a8" + suffix, moves)  # push promotion
            self.assertIn("a7b8" + suffix, moves)  # capture promotion

    def test_promotion_places_the_chosen_piece(self):
        board = Board("8/P7/8/8/8/8/k6K/8 w - - 0 1")
        play(board, "a7a8n")
        self.assertEqual(board.squares[56], "N")  # a8 holds a white knight


class CastlingTests(unittest.TestCase):
    def test_both_sides_available_in_open_position(self):
        moves = uci_set(Board(BARE_CASTLING))
        self.assertIn("e1g1", moves)
        self.assertIn("e1c1", moves)

    def test_castling_moves_the_rook_and_clears_rights(self):
        board = play(Board(BARE_CASTLING), "e1g1")
        self.assertEqual(board.squares[6], "K")  # king on g1
        self.assertEqual(board.squares[5], "R")  # rook on f1
        self.assertEqual(board.castling, "kq")  # only Black keeps rights

    def test_castling_through_check_is_illegal(self):
        # The black rook on f2 covers f1, so White may not pass through it;
        # queenside castling stays legal.
        board = Board("r3k2r/8/8/8/8/8/5r2/R3K2R w KQkq - 0 1")
        moves = uci_set(board)
        self.assertNotIn("e1g1", moves)
        self.assertIn("e1c1", moves)

    def test_castling_out_of_check_is_illegal(self):
        board = Board("r3k2r/8/8/8/8/4r3/8/R3K2R w KQkq - 0 1")
        moves = uci_set(board)
        self.assertNotIn("e1g1", moves)
        self.assertNotIn("e1c1", moves)

    def test_blocked_castling_is_illegal(self):
        board = Board("r3k2r/8/8/8/8/8/8/RN2K1NR w KQkq - 0 1")
        moves = uci_set(board)
        self.assertNotIn("e1g1", moves)
        self.assertNotIn("e1c1", moves)

    def test_rook_move_drops_only_its_own_right(self):
        board = play(Board(BARE_CASTLING), "a1a2")
        self.assertEqual(board.castling, "Kkq")


class GameStatusTests(unittest.TestCase):
    def test_start_position_is_ongoing(self):
        board = Board()
        self.assertEqual(board.status(), "ongoing")
        self.assertFalse(board.is_checkmate())
        self.assertFalse(board.is_stalemate())
        self.assertIsNone(board.outcome())

    def test_check_is_not_mate_when_king_can_move(self):
        # Black king on e8 is in check from the e2 rook but can step aside.
        board = Board("4k3/8/8/8/8/8/4R3/4K3 b - - 0 1")
        self.assertTrue(board.is_in_check("b"))
        self.assertEqual(board.status(), "check")
        self.assertFalse(board.is_checkmate())
        self.assertIsNone(board.outcome())

    def test_fools_mate_is_checkmate_for_side_to_move(self):
        # 1. f3 e5 2. g4 Qh4# — the fastest checkmate in chess.
        board = Board()
        for uci in ("f2f3", "e7e5", "g2g4", "d8h4"):
            play(board, uci)
        self.assertEqual(board.turn, "w")
        self.assertTrue(board.is_checkmate())
        self.assertFalse(board.is_stalemate())
        self.assertEqual(board.status(), "checkmate")
        self.assertEqual(board.outcome(), "0-1")  # White is mated

    def test_scholars_mate_position_is_checkmate(self):
        # Qxf7# protected by the c4 bishop; Black to move has no legal move.
        board = Board(
            "r1bqkb1r/pppp1Qpp/2n2n2/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4"
        )
        self.assertTrue(board.is_checkmate())
        self.assertEqual(board.outcome(), "1-0")  # Black is mated

    def test_classic_stalemate(self):
        # Black king h8, White Qf7 + Kg6: not in check, nowhere to move.
        board = Board("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
        self.assertFalse(board.is_in_check("b"))
        self.assertTrue(board.is_stalemate())
        self.assertFalse(board.is_checkmate())
        self.assertEqual(board.status(), "stalemate")
        self.assertEqual(board.outcome(), "1/2-1/2")

    def test_stalemate_needs_no_legal_moves_not_just_no_king_moves(self):
        # Same king trap, but Black has a pawn that can still move.
        board = Board("7k/5Q1p/6K1/8/8/8/8/8 b - - 0 1")
        self.assertFalse(board.is_stalemate())
        self.assertEqual(board.status(), "ongoing")


class MoveObjectTests(unittest.TestCase):
    def test_uci_round_trip(self):
        move = Move.from_uci("e7e8q")
        self.assertEqual(move.uci(), "e7e8q")
        self.assertEqual(Move.from_uci("g1f3").uci(), "g1f3")

    def test_illegal_move_lookup_raises(self):
        with self.assertRaises(ValueError):
            Board().find_move("e2e5")


if __name__ == "__main__":
    unittest.main()
