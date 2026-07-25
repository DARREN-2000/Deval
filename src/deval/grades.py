"""Letter-grade boundaries for Deval scores.

This module is deliberately dependency-free. Both :mod:`deval.model` and
:mod:`deval.scoring` need to turn a 0-100 score into a letter grade, and if
either owned the mapping the other would have to import it, creating an import
cycle. Keeping the mapping in a leaf module lets every layer depend on it
without depending on each other.

The boundaries are intentionally close to a university grading curve so the
grade is legible without a legend: an A- means "good, ship it", anything below
a C means the repository needs real work.
"""

from __future__ import annotations

# Ordered high to low; the first threshold a score meets wins.
GRADE_BOUNDARIES: tuple[tuple[int, str], ...] = (
    (97, "A+"),
    (93, "A"),
    (90, "A-"),
    (85, "B+"),
    (80, "B"),
    (75, "C+"),
    (70, "C"),
    (60, "D"),
)

LOWEST_GRADE = "F"


def grade_for(score: int) -> str:
    """Return the letter grade for a 0-100 ``score``.

    The mapping is total: any integer resolves to a grade, and scores below the
    lowest boundary fall through to ``F``.

    >>> grade_for(100)
    'A+'
    >>> grade_for(90)
    'A-'
    >>> grade_for(0)
    'F'
    """
    for threshold, letter in GRADE_BOUNDARIES:
        if score >= threshold:
            return letter
    return LOWEST_GRADE