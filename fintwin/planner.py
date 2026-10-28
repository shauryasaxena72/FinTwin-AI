"""Backward-compatible shim. Re-exports from generate.py and rank.py."""
from __future__ import annotations
from generate import generate_candidates, hard_filter, filter_candidates, CUT_PAIN, LOAN_RATE, _curve, _structures
from generate import REJECT_BASE_BREACH, REJECT_GOAL_MISSED, REJECT_LOAN_UNPAID
from rank import rank_plans, DEFAULT_WEIGHTS, LABEL_FASTEST, LABEL_SAFEST, LABEL_CHEAPEST
