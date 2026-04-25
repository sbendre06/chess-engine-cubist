"""Hidden FEN fixtures for the antichess correctness suite.

Two tiers:
  Tier 1 -- rule compliance, evaluated by calling the Core 3 engine primitives
            directly on a curated position. No search.
  Tier 2 -- strategic decision quality, evaluated by running the engine through
            the harness's iterative_deepening at fixed depth and inspecting the
            chosen root move.

Every fixture carries a `note` documenting the rule under test and (for Tier 2)
the source of the expected move(s). All FENs use chess.variant.AntichessBoard
(Giveaway rules, matching the engines under test).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


Tier1Rule = Literal[
    "move_gen_superset",      # engine output (filtered) must equal board.legal_moves
    "legal_moves_exact",      # engine output (filtered) must equal an explicit set
    "contains_moves",         # engine pseudo-legal output must include certain UCIs
    "excludes_moves",         # engine pseudo-legal output must not include certain UCIs
    "eval_winning",           # evaluate_board(board) >= expected.min_score
    "eval_losing",            # evaluate_board(board) <= expected.max_score
    "terminal_winner",        # board.outcome().winner == expected.winner_color
    "not_terminal",           # board.is_game_over() must be False
]


@dataclass(frozen=True)
class Tier1Fixture:
    test_id: str
    fen: str
    rule: Tier1Rule
    expected: dict
    note: str


@dataclass(frozen=True)
class Tier2Fixture:
    test_id: str
    fen: str
    expected_moves: frozenset
    depth: int
    source: str
    note: str


TIER1_FIXTURES: list[Tier1Fixture] = [
    # --- move generation ---
    Tier1Fixture(
        test_id="move_gen_completeness_startpos",
        fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        rule="move_gen_superset",
        expected={},
        note="Engine's pseudo-legal output, when filtered through board.legal_moves, must equal the legal set. No legal moves dropped.",
    ),
    Tier1Fixture(
        test_id="forced_capture_exact_set",
        fen="4k3/8/8/3p4/4P3/8/8/4K3 w - - 0 1",
        rule="legal_moves_exact",
        expected={"legal_uci": ["e4d5"]},
        note="One capture (exd5) among many quiet moves. Forced-capture rule eliminates all quiet moves. Engine's filtered pseudo-legal set must equal {e4d5} -- no quiet move pollution.",
    ),
    Tier1Fixture(
        test_id="multi_capture_exact_set",
        fen="4k3/8/8/8/p3Q2p/8/8/4K3 w - - 0 1",
        rule="legal_moves_exact",
        expected={"legal_uci": ["e4a4", "e4h4", "e4e8"]},
        note="Queen has three captures (Qxa4, Qxh4, Qxe8). Forced-capture rule removes all quiet moves. Engine's filtered set must equal exactly these three.",
    ),
    Tier1Fixture(
        test_id="king_capturable_exact_set",
        fen="8/8/8/4k3/3Q4/8/8/4K3 w - - 0 1",
        rule="legal_moves_exact",
        expected={"legal_uci": ["d4e5"]},
        note="No-check rule: opponent king is en prise. Forced-capture rule means Qxe5 is the only legal move. Engine must not 'protect' the position from king-capture nor offer quiet moves.",
    ),
    Tier1Fixture(
        test_id="promotion_to_king_offered",
        fen="4k3/P7/8/8/8/8/8/4K3 w - - 0 1",
        rule="contains_moves",
        expected={"required_uci": ["a7a8k", "a7a8q"]},
        note="Antichess allows promotion to king. Engine must offer promotion-to-king alongside other promotions.",
    ),
    Tier1Fixture(
        test_id="no_castling_white",
        fen="r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1",
        rule="excludes_moves",
        expected={"forbidden_uci": ["e1g1", "e1c1"]},
        note="Castling is illegal in antichess even with full castling rights. White to move: engine must not offer e1g1 or e1c1.",
    ),
    Tier1Fixture(
        test_id="no_castling_black",
        fen="r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1",
        rule="excludes_moves",
        expected={"forbidden_uci": ["e8g8", "e8c8"]},
        note="Same as no_castling_white but black to move. Engine must not offer e8g8 or e8c8.",
    ),

    # --- terminal-state recognition ---
    Tier1Fixture(
        test_id="terminal_no_pieces_is_win",
        fen="8/8/8/8/8/8/8/4K3 b - - 0 1",
        rule="terminal_winner",
        expected={"winner_color": "black"},
        note="Black has 0 pieces and it is black's turn. Antichess: side with 0 pieces wins. board.outcome().winner must be BLACK.",
    ),
    Tier1Fixture(
        test_id="stalemate_is_win_for_stalemated",
        fen="8/8/8/8/8/p7/P7/8 b - - 0 1",
        rule="terminal_winner",
        expected={"winner_color": "black"},
        note="Black pawn a3 is blocked, no captures available. Black is stalemated. Giveaway rules: stalemated side wins.",
    ),
    Tier1Fixture(
        test_id="checkmate_not_terminal",
        fen="rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3",
        rule="not_terminal",
        expected={},
        note="Fool's mate position: standard chess scores this as black wins by checkmate. Antichess has no check -> game continues. is_game_over() must be False.",
    ),

    # --- adversarial: prior conflicts where antichess rules invert std-chess intuition ---
    Tier1Fixture(
        test_id="king_attacked_quiet_moves_remain_legal",
        fen="4q3/8/8/8/8/8/4K2P/8 w - - 0 1",
        rule="contains_moves",
        expected={"required_uci": ["h2h3", "h2h4"]},
        note="White king on e1 is attacked by black queen on e8 (std-chess 'check'). No captures available. Antichess has no check rule -> pawn pushes are legal even though king remains 'in check'. Tests that engine doesn't filter quiet moves to 'save' the king.",
    ),
    Tier1Fixture(
        test_id="must_capture_even_if_self_destructive",
        fen="4q3/8/8/8/8/8/8/4Q3 w - - 0 1",
        rule="legal_moves_exact",
        expected={"legal_uci": ["e1e8"]},
        note="White's only legal move (Qxe8) leaves white with one piece and black with zero -> black wins on the next ply. Std-chess intuition says 'don't make a capture that loses the game' but antichess's forced-capture rule overrides that. Engine must offer Qxe8 with no quiet alternatives.",
    ),

    # --- inverted material evaluation ---
    Tier1Fixture(
        test_id="inverted_material_white_winning",
        fen="3qk3/8/8/8/8/8/8/4K3 w - - 0 1",
        rule="eval_winning",
        expected={"min_score": 1},
        note="White (1 piece) vs Black (2 pieces); fewer pieces = winning in antichess. evaluate_board must return positive score for white. Note: harness's negamax assumes evaluate_board is side-to-move-positive (engine.py:151), so this is testing the project's frozen eval contract, not an arbitrary convention.",
    ),
    Tier1Fixture(
        test_id="inverted_material_white_losing",
        fen="4k3/8/8/8/8/8/8/3QK3 w - - 0 1",
        rule="eval_losing",
        expected={"max_score": -1},
        note="White (2 pieces) vs Black (1 piece); more pieces = losing. evaluate_board must return negative score for white.",
    ),
]


TIER2_FIXTURES: list[Tier2Fixture] = [
    Tier2Fixture(
        test_id="forced_single_move",
        fen="4k3/8/8/3p4/4P3/8/8/4K3 w - - 0 1",
        expected_moves=frozenset({"e4d5"}),
        depth=2,
        source="constructed",
        note="Sanity: forced capture is the only legal move. Search must return it at any depth.",
    ),
    Tier2Fixture(
        test_id="opening_e3_or_central_pawn",
        fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        expected_moves=frozenset({"e2e3", "e2e4", "d2d3", "d2d4"}),
        depth=3,
        source="Watkins (1.e3 is proven winner; central pawn pushes accepted as Watkins-class openings)",
        note="Watkins: 1.e3 weakly solves antichess for white. Score lenient: any central pawn opening passes.",
    ),
    Tier2Fixture(
        test_id="liardet_a4_or_pawn_response",
        fen="rnbqkbnr/p1pppppp/1p6/8/8/4P3/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
        expected_moves=frozenset({"a2a4", "a2a3", "b2b3", "c2c4", "c2c3"}),
        depth=3,
        source="Watkins (Liardet defense; 2.a4 was the May 2015 breakthrough switch from 2.Ba6)",
        note="After 1.e3 b6, Watkins's proof tree uses queen-side pawn moves to break the Liardet defense. Accept any.",
    ),
    Tier2Fixture(
        test_id="kp_endgame_push_pawn",
        fen="4k3/8/8/8/8/8/P7/4K3 w - - 0 1",
        expected_moves=frozenset({"a2a3", "a2a4"}),
        depth=4,
        source="Watkins (pawn advancement is the canonical endgame-stalemate breaker)",
        note="KP vs K endgame. Watkins: pushing pawns toward promotion is the most reliable heuristic for breaking endgame stalemates. Pawn push should beat king shuffle.",
    ),
    Tier2Fixture(
        test_id="promotion_at_seventh",
        fen="4k3/P7/8/8/8/8/8/4K3 w - - 0 1",
        expected_moves=frozenset({"a7a8q", "a7a8r", "a7a8b", "a7a8n", "a7a8k"}),
        depth=3,
        source="constructed",
        note="Pawn on 7th, no immediate captures. Engine should promote (any promotion piece is accepted, including king per antichess rules).",
    ),
    Tier2Fixture(
        test_id="capture_only_legal_under_forced_rule",
        fen="4k3/8/3p1p2/4P3/8/8/8/4K3 w - - 0 1",
        expected_moves=frozenset({"e5d6", "e5f6"}),
        depth=2,
        source="constructed",
        note="Two pawn captures available; forced-capture rule eliminates all quiet moves. Engine must pick a capture.",
    ),
    Tier2Fixture(
        test_id="find_pawn_sacrifice_to_force_win",
        fen="8/8/8/8/q7/8/P6P/8 w - - 0 1",
        expected_moves=frozenset({"a2a3"}),
        depth=4,
        source="constructed",
        note=(
            "White has three legal quiet moves: a2a3, h2h3, h2h4. Only a2a3 forces black's queen "
            "to immediately capture (Qxa3, the only legal black move thereafter), starting a "
            "two-step sequence that empties white's pieces and wins the game (white reaches 0 "
            "pieces -> variant_win for white). The h2-pawn pushes are not in queen-capture range "
            "of a4. At depth 4 the engine must see the variant_win and pick a2a3."
        ),
    ),
]


def all_fixtures() -> tuple[list[Tier1Fixture], list[Tier2Fixture]]:
    return TIER1_FIXTURES, TIER2_FIXTURES
