
"""Grounded copilot: financial figures come from deterministic engine tools.
Unsupported numeric claims in LLM replies are rejected in favor of the
deterministic offline fallback.
"""

from __future__ import annotations

import json
import math
import os
import re
from dataclasses import asdict, replace

from .engine import Profile, Decision, Scenario, diagnose
from .planner import rank_plans, DEFAULT_WEIGHTS


MODEL = os.getenv("FINTWIN_MODEL", "claude-sonnet-5-5")

SYSTEM = (
    "You are FinTwin AI's copilot. A deterministic engine computes every figure. "
    "Call tools to get numbers; NEVER compute, estimate or invent financial figures yourself. "
    "Quote values exactly as returned (amounts are Rs lakh). If a tool lacks the answer, say so. "
    "Be concise: verdict, why, best alternative, trade-off."
)

TOOLS = [
    {
        "name": "diagnose_decision",
        "description": (
            "Simulate the user's original decision under base and adverse scenarios; "
            "returns breach month, shortfall, runway and root-cause drivers."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "rank_alternatives",
        "description": (
            "Generate alternative plans that preserve the goal, drop infeasible ones, "
            "and rank survivors by cost, goal loss and Monte Carlo breach probability."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "top_n": {"type": "integer"},
                "weights": {
                    "type": "object",
                    "description": "Optional weights for cost, goal_loss and risk",
                },
            },
        },
    },
    {
        "name": "what_if",
        "description": "Re-run diagnosis and ranking with changed inputs.",
        "input_schema": {
            "type": "object",
            "properties": {
                key: {"type": "number"}
                for key in (
                    "opening_cash",
                    "monthly_revenue",
                    "monthly_expenses",
                    "min_reserve",
                    "purchase_amount",
                    "revenue_shock_pct",
                    "one_off_shock",
                )
            },
        },
    },
]


def L(x):
    return f"Rs {x:.1f}L"


class FinTwinAgent:
    def __init__(self, profile=None, decision=None, scenario=None):
        self.profile = profile or Profile()
        self.decision = decision or Decision()
        self.scenario = scenario or Scenario()
        self.history = []
        self.tool_log = []

    # ---------- tools ----------

    def t_diagnose_decision(self, **_):
        return diagnose(self.profile, self.decision, self.scenario)

    def t_rank_alternatives(self, top_n=3, weights=None, **_):
        result = rank_plans(
            self.profile,
            self.decision,
            self.scenario,
            weights,
            int(top_n),
        )
        result.pop("all_feasible", None)
        return result

    def t_what_if(self, **changes):
        profile = replace(self.profile)
        decision = replace(self.decision)
        scenario = replace(self.scenario)

        for key, value in changes.items():
            if key == "purchase_amount":
                decision.amount = value
            elif key in asdict(profile):
                setattr(profile, key, value)
            elif key in asdict(scenario):
                setattr(scenario, key, value)

        ranking = rank_plans(profile, decision, scenario, None, 3)
        ranking.pop("all_feasible", None)

        return {
            "changes": changes,
            "diagnosis": diagnose(profile, decision, scenario),
            "ranking": ranking,
        }

    def call_tool(self, name, args):
        output = getattr(self, "t_" + name)(**(args or {}))
        self.tool_log.append({
            "tool": name,
            "args": args,
            "output": output,
        })
        return output

    # ---------- deterministic narration ----------

    @staticmethod
    def narrate_diagnosis(dx):
        adverse = dx["adverse"]
        base = dx["base"]

        if adverse["passes"]:
            return (
                f"Plan holds: cash never drops below "
                f"{L(adverse['min_cash'])} "
                f"(reserve {L(dx['reserve'])}) even in the adverse case."
            )

        causes = adverse["causes"]

        text = (
            (
                "Looks safe in the base case (lowest cash "
                f"{L(base['min_cash'])}) but "
                if dx["looks_safe_then_fails"]
                else ""
            )
            + f"fails under stress: cash hits {L(adverse['min_cash'])} "
            f"in month {adverse['min_month']}, "
            f"{L(adverse['shortfall'])} below the "
            f"{L(dx['reserve'])} reserve "
            f"(first breach month {adverse['breach_month']}). "
            f"Drivers by then: purchase {L(causes['purchase_paid'])}, "
            f"lost revenue {L(causes['revenue_loss'])}, "
            f"one-off shock {L(causes['one_off_shock'])}."
        )

        fixes = adverse["single_fixes"]

        if len(fixes) == 1:
            text += (
                f" Removing {fixes[0]} alone would avoid the breach "
                "- it is the decisive driver."
            )
        elif fixes:
            text += (
                f" Removing any one of {', '.join(fixes)} alone would "
                "avoid the breach - a compound failure."
            )

        return text

    @staticmethod
    def narrate_ranking(result):
        if not result["ranked"]:
            return (
                "No feasible alternative found under this scenario - "
                "consider a smaller purchase or raising cash."
            )

        lines = [
            f"{result['n_feasible']} of {result['n_candidates']} candidate plans "
            f"survive the stress test. Top {len(result['ranked'])}:"
        ]

        for plan in result["ranked"]:
            lines.append(
                f"{plan['rank']}. {plan['name']} - "
                f"extra cost {L(plan['cost'])}, "
                f"goal acquired month {plan['acquired_month']}, "
                f"lowest cash {L(plan['min_cash'])}, "
                f"reserve-breach probability {plan['breach_prob'] * 100:.1f}%, "
                f"score {plan['score']}."
            )

        return "\n".join(lines)

    # ---------- numeric grounding guard ----------

    @staticmethod
    def _numbers(obj, acc):
        """Collect numeric values actually present in engine outputs."""
        if isinstance(obj, dict):
            for value in obj.values():
                FinTwinAgent._numbers(value, acc)

        elif isinstance(obj, (list, tuple)):
            for value in obj:
                FinTwinAgent._numbers(value, acc)

        elif isinstance(obj, bool) or obj is None:
            return

        elif isinstance(obj, (int, float)):
            if isinstance(obj, float) and not math.isfinite(obj):
                return
            acc.add(float(obj))

    def ungrounded(self, text, outputs):
        """Return numeric tokens not found in the supplied engine outputs."""
        allowed = set()
        self._numbers(outputs, allowed)
        bad = []

        pattern = (
            r"(?<![A-Za-z])[-+]?"
            r"(?:\d{1,3}(?:,\d{3})+|\d+)"
            r"(?:\.\d+)?%?(?![A-Za-z])"
        )

        for token in re.findall(pattern, text):
            normalized = token.replace(",", "").replace("%", "")

            try:
                value = float(normalized)
            except ValueError:
                bad.append(token)
                continue

            if not math.isfinite(value) or value not in allowed:
                bad.append(token)

        return bad

    # ---------- chat ----------

    def chat(self, msg: str) -> str:
        self.tool_log.clear()

        reply = (
            self._llm_chat(msg)
            if os.getenv("ANTHROPIC_API_KEY")
            else None
        )

        if reply:
            outputs = [item["output"] for item in self.tool_log]
            bad = self.ungrounded(reply, outputs)

            if not bad:
                return reply

            note = (
                "\n\n(Guard: LLM draft quoted ungrounded numbers "
                f"{bad}; showing engine-verified answer.)"
            )
        else:
            note = ""

        return self._rule_chat(msg) + note

    def _rule_chat(self, msg):
        message = msg.lower()
        changes = {}

        patterns = (
            ("opening_cash", r"cash\D{0,12}(\d+(?:\.\d+)?)"),
            ("min_reserve", r"reserve\D{0,12}(\d+(?:\.\d+)?)"),
            (
                "purchase_amount",
                r"(?:equipment|purchase|buy)\D{0,12}(\d+(?:\.\d+)?)",
            ),
            (
                "monthly_revenue",
                r"revenue\D{0,12}(\d+(?:\.\d+)?)(?!\s*%)",
            ),
        )

        for key, pattern in patterns:
            match = re.search(pattern, message)
            if match:
                changes[key] = float(match.group(1))

        shock = re.search(
            r"revenue\D{0,12}(-?\d+(?:\.\d+)?)\s*%",
            message,
        )

        if shock:
            changes["revenue_shock_pct"] = (
                -abs(float(shock.group(1))) / 100
            )
            changes.pop("monthly_revenue", None)

        if "what if" in message and changes:
            output = self.call_tool("what_if", changes)
            return (
                f"With {changes}:\n"
                f"{self.narrate_diagnosis(output['diagnosis'])}\n"
                f"{self.narrate_ranking(output['ranking'])}"
            )

        if any(word in message for word in (
            "best", "recommend", "alternative", "instead", "plan", "options"
        )):
            return self.narrate_ranking(
                self.call_tool("rank_alternatives", {"top_n": 3})
            )

        if any(word in message for word in (
            "why", "fail", "risk", "safe", "breach", "afford", "runway"
        )):
            return self.narrate_diagnosis(
                self.call_tool("diagnose_decision", {})
            )

        return (
            "Ask me: 'Can I afford this?', 'Why does it fail?', "
            "'What are the best alternatives?', or "
            "'What if cash is 10 and revenue drops 30%?'"
        )

    def _llm_chat(self, msg):
        try:
            import anthropic

            client = anthropic.Anthropic()
            messages = self.history + [{"role": "user", "content": msg}]

            for _ in range(6):
                response = client.messages.create(
                    model=MODEL,
                    max_tokens=1000,
                    system=SYSTEM,
                    tools=TOOLS,
                    messages=messages,
                )

                if response.stop_reason != "tool_use":
                    text = "".join(
                        block.text
                        for block in response.content
                        if block.type == "text"
                    )
                    self.history = messages + [{
                        "role": "assistant",
                        "content": text,
                    }]
                    return text

                messages.append({
                    "role": "assistant",
                    "content": response.content,
                })

                results = []

                for block in response.content:
                    if block.type == "tool_use":
                        output = self.call_tool(block.name, block.input)
                        results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(output)[:20000],
                        })

                messages.append({"role": "user", "content": results})

        except Exception:
            # Offline / bad key -> deterministic fallback.
            self.tool_log.clear()
            return None

        return None
