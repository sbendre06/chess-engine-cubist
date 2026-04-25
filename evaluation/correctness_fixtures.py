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


@dataclass(frozen=True)
class Tier1Fixture:
    test_id: str
    fen: str
    rule: str
    expected: dict  # rule-specific payload (see correctness.py for keys per rule)
    note: str


@dataclass(frozen=True)
class Tier2Fixture:
    test_id: str
    fen: str
    expected_moves: frozenset  # UCI strings; engine's chosen move must be in this set
    depth: int
    source: str
    note: str


TIER1_FIXTURES: list[Tier1Fixture] = [
    Tier1Fixture(
        test_id="move_gen_completeness_startpos",
        fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        rule="move_gen_superset",
        expected={},
        note="Engine's pseudo-legal output, when filtered through board.legal_moves, must equal the legal set. No legal moves dropped.",
    ),
    Tier1Fixture(
        test_id="forced_capture_recognized",
        fen="4k3/8/8/3p4/4P3/8/8/4K3 w - - 0 1",
        rule="contains_moves",
        expected={"required_uci": ["e4d5"]},
        note="Single capture (exd5) available among many quiet moves. Engine's pseudo-legal set must include the capture.",
    ),
    Tier1Fixture(
        test_id="multi_capture_choice",
        fen="4k3/8/8/8/p3Q2p/8/8/4K3 w - - 0 1",
        rule="contains_moves",
        expected={"required_uci": ["e4a4", "e4h4", "e4e8"]},
        note="Queen has three captures (a4, h4, e8). All must appear in engine's pseudo-legal set.",
    ),
    Tier1Fixture(
        test_id="promotion_to_king_offered",
        fen="4k3/P7/8/8/8/8/8/4K3 w - - 0 1",
        rule="contains_moves",
        expected={"required_uci": ["a7a8k", "a7a8q"]},
        note="Antichess allows promotion to king. Engine must offer promotion-to-king alongside other promotions.",
    ),
    Tier1Fixture(
        test_id="king_capturable",
        fen="8/8/8/4k3/3Q4/8/8/4K3 w - - 0 1",
        rule="contains_moves",
        expected={"required_uci": ["d4e5"]},
        note="No-check rule: opponent king is en prise. Engine must yield Qxe5 (only legal move under forced capture).",
    ),
    Tier1Fixture(
        test_id="no_castling_offered",
        fen="r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1",
        rule="excludes_moves",
        expected={"forbidden_uci": ["e1g1", "e1c1", "e8g8", "e8c8"]},
        note="Castling is illegal in antichess even with full castling rights. Engine must not offer castling moves.",
    ),
    Tier1Fixture(
        test_id="inverted_material_white_winning",
        fen="3qk3/8/8/8/8/8/8/4K3 w - - 0 1",
        rule="eval_winning",
        expected={"min_score": 1},
        note="White (1 piece) vs Black (2 pieces); fewer pieces = winning in antichess. evaluate_board must return positive score for white.",
    ),
    Tier1Fixture(
        test_id="inverted_material_white_losing",
        fen="4k3/8/8/8/8/8/8/3QK3 w - - 0 1",
        rule="eval_losing",
        expected={"max_score": -1},
        note="White (2 pieces) vs Black (1 piece); more pieces = losing. evaluate_board must return negative score for white.",
    ),
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
        test_id="recognize_terminal_win_via_search",
        fen="4k3/8/8/8/8/q7/P7/8 b - - 0 1",
        expected_moves=frozenset({"a3a2"}),
        depth=2,
        source="constructed",
        note="Black queen has only one capture (forced Qxa2). After capture, white has 0 pieces -> white wins (variant_win for white). Black's only move is bad, but it's forced. Tests harness terminal scoring path.",
    ),
]


def all_fixtures() -> tuple[list[Tier1Fixture], list[Tier2Fixture]]:
    return TIER1_FIXTURES, TIER2_FIXTURES
