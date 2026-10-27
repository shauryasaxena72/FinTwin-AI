"""Shared contract: results.json schema as Python dataclasses.

Single source of truth for all modules. No number exists without a provenance tag.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Literal

TagType = Literal["UPLOAD", "ENTERED", "DERIVED", "EXTERNAL", "ASSUMPTION"]


@dataclass
class Provenance:
    field: str
    tag: TagType
    source: str


@dataclass
class InflowEntry:
    amount: float
    month: int
    status: str  # "confirmed" | "expected"


@dataclass
class ProfileData:
    cash: float
    reserve: float
    opex_by_month: list[float] = field(default_factory=list)
    loans: list[dict] = field(default_factory=list)
    inflows: list[InflowEntry] = field(default_factory=list)


@dataclass
class SeriesEntry:
    months: list[int] = field(default_factory=list)
    opening: list[float] = field(default_factory=list)
    inflow: list[float] = field(default_factory=list)
    outflow: list[float] = field(default_factory=list)
    closing: list[float] = field(default_factory=list)
    drivers: list[str] = field(default_factory=list)


@dataclass
class RiskData:
    first_breach_month: int | None = None
    max_shortfall: float = 0.0
    kind: str = "NONE"  # "TEMPORARY" | "PERSISTENT" | "NONE"
    causes: list[dict] = field(default_factory=list)  # [{driver, removal_clears_breach}]


@dataclass
class PlanData:
    id: str = ""
    description: str = ""
    feasible: bool = False
    reject_reason: str | None = None
    min_cash_base: float = 0.0
    min_cash_stress: float = 0.0
    breach_prob: float | None = None
    ci: list[float] | None = None
    delay_months: int = 0
    extra_cost: float = 0.0
    label: str | None = None


@dataclass
class MCData:
    enabled: bool = False
    disabled_reason: str | None = None
    N: int = 0
    seed: int = 0
    bands: dict = field(default_factory=lambda: {"p10": [], "p50": [], "p90": []})


@dataclass
class ResultsJSON:
    """Single source of truth shared across all modules."""
    provenance: list[Provenance] = field(default_factory=list)
    profile: ProfileData | None = None
    series: dict[str, dict[str, SeriesEntry]] = field(default_factory=dict)
    risk: RiskData = field(default_factory=RiskData)
    plans: list[PlanData] = field(default_factory=list)
    mc: MCData = field(default_factory=MCData)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        import dataclasses
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ResultsJSON":
        """Create from dictionary."""
        return cls(
            provenance=[Provenance(**p) for p in d.get("provenance", [])],
            profile=ProfileData(**d["profile"]) if d.get("profile") else None,
            series={k: {sk: SeriesEntry(**sv) for sk, sv in v.items()} for k, v in d.get("series", {}).items()},
            risk=RiskData(**d.get("risk", {})),
            plans=[PlanData(**p) for p in d.get("plans", [])],
            mc=MCData(**d.get("mc", {})),
        )
