"""Bundled marketplace rule packs.

Each pack is a self-contained plugin that registers extra rules via
:mod:`deval.sdk`. Packs are intentionally inert until their trigger files are
present, so installing a pack never changes an unrelated repository's score.
"""
