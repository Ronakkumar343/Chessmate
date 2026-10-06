"""Unit tests for the Chessmate engine brain and terminal play loop.

Run from the repository root with the standard library only:

    python -m unittest discover -s tests -v

Search tests use depth 2 (or mate-in-1 positions) so the suite stays
fast while still proving the engine can mate and can grab free material.
"""

import unittest

from chessmate import Board, best_move, evaluate
from chessmate.play import play_game, render

# White to move mates in one with Ra1-a8: the black king on g8 is
# fenced in by its own pawns on f7, g7 and h7.
MATE_IN_ONE = "6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1"
# Black queen on d4 is attacked by the knight on f3 and defended by
# nobody — the engine must simply take it.
HANGING_QUEEN = "4k3/8/8/8/3q4/5N2/8/4K3 w - - 0 1"
# Fool's mate, final position: White to move is checkmated.
FOOLS_MATE_FINAL = "rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3"
# Classic queen-and-king stalemate: Black to move has no legal move
# and is not in check.
STALEMATE = "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"


def play(board, uci):
    board.make_move(board.find_move(uci))
    return board


class EvaluationTests(unittest.TestCase):
    def test_start_position_scores_zero(self):
        # Symmetric material on mirrored squares must cancel exactly.
        self.assertEqual(evaluate(Board()), 0)

    def test_symmetric_position_after_e4_e5_scores_zero(self):
        board = play(play(Board(), "e2e4"), "e7e5")
        self.assertEqual(evaluate(board), 0)

    def test_up_a_queen_is_clearly_positive_for_white(self):
        # Start position with Black's queen removed.
        board = Board("rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
        self.assertGreaterEqual(evaluate(board), 800)

    def test_down_a_queen_is_clearly_negative_for_white(self):
        # Start position with White's queen removed.
        board = Board("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNB1KBNR w KQkq - 0 1")
        self.assertLessEqual(evaluate(board), -800)


class SearchTests(unittest.TestCase):
    def test_finds_mate_in_one(self):
        board = Board(MATE_IN_ONE)
        move = best_move(board, depth=2)
        self.assertIsNotNone(move)
        self.assertEqual(move.uci(), "a1a8")
        play(board, move.uci())
        self.assertTrue(board.is_checkmate())

    def test_captures_hanging_queen(self):
        board = Board(HANGING_QUEEN)
        move = best_move(board, depth=2)
        self.assertIsNotNone(move)
        self.assertEqual(move.uci(), "f3d4")

    def test_returns_a_legal_move_from_start(self):
        board = Board()
        move = best_move(board, depth=2)
        self.assertIsNotNone(move)
        self.assertIn(move.uci(), {m.uci() for m in board.legal_moves()})

    def test_no_move_when_checkmated(self):
        self.assertIsNone(best_move(Board(FOOLS_MATE_FINAL), depth=2))

    def test_no_move_when_stalemated(self):
        self.assertIsNone(best_move(Board(STALEMATE), depth=2))

    def test_engine_replies_as_black(self):
        board = play(Board(), "e2e4")
        move = best_move(board, depth=2)
        self.assertIsNotNone(move)
        self.assertIn(move.uci(), {m.uci() for m in board.legal_moves()})


def scripted_game(inputs, **kwargs):
    """Run play_game with scripted input; return (final board, output lines)."""
    remaining = iter(inputs)
    output = []
    board = play_game(
        input_fn=lambda prompt: next(remaining),
        print_fn=output.append,
        depth=2,
        **kwargs,
    )
    return board, output


class PlayLoopTests(unittest.TestCase):
    def test_render_shows_both_kings(self):
        drawing = render(Board())
        self.assertIn("K", drawing)
        self.assertIn("k", drawing)
        self.assertEqual(len(drawing.splitlines()), 10)

    def test_human_move_gets_an_engine_reply(self):
        board, output = scripted_game(["e2e4", "quit"])
        # After 1. e4 and the engine's reply it is White to move again,
        # in move 2 — then the scripted 'quit' ends the game.
        self.assertEqual(board.turn, "w")
        self.assertEqual(board.fullmove_number, 2)
        self.assertTrue(any(line.startswith("Engine plays") for line in output))

    def test_illegal_input_is_rejected_not_played(self):
        board, output = scripted_game(["zzzz", "e2e4", "quit"])
        self.assertTrue(any("not a legal move" in line for line in output))
        self.assertEqual(board.fullmove_number, 2)  # e4 + engine reply still happened

    def test_moves_command_lists_legal_moves(self):
        board, output = scripted_game(["moves", "quit"])
        self.assertTrue(any(line.startswith("Legal moves:") for line in output))
        self.assertEqual(board.fullmove_number, 1)  # nothing was played


if __name__ == "__main__":
    unittest.main()
