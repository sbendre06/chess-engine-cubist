"""
Search tactics and alpha-beta invariants (Person 2).

Cases to cover:
- Known forced win line found within depth budget
- TT move ordering changes node count but not best move score (regression)
- Killer/history smoke: no crash on tactical positions
- Quiescence: does not terminate eval inside mandatory capture sequence incorrectly
"""

from __future__ import annotations


def test_search_placeholder():
    ...