"""Grounded copilot: the LLM (or the offline fallback) may only call tools and explain their output.
A grounding guard rejects any reply containing a number that no tool produced."""
from __future__ import annotations
import json, os, re
from dataclasses import replace, asdict
from .engine import Profile, Decision, Scenario, diagnose
from .planner import rank_plans, DEFAULT_WEIGHTS

MODEL = os.getenv("FINTWIN_MODEL", "claude-sonnet-5-5")
SYSTEM = ("You are FinTwin AI's copilot. A deterministic engine computes every figure. "
          "Call tools to get numbers; NEVER compute, estimate or invent financial figures yourself. "
          "Quote values exactly as returned (amounts are Rs lakh). If a tool lacks the answer, say so. "
          "Be concise: verdict, why, best alternative, trade-off.")

TOOLS = [
    {"name": "diagnose_decision", "description": "Simulate the user's original decision under base and adverse scenarios; returns breach month, shortfall, runway and root-cause drivers.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "rank_alternatives", "description": "Generate alternative plans that preserve the goal, drop infeasible ones, rank survivors by cost, goal loss and Monte Carlo breach probability.",
     "input_schema": {"type": "object", "properties": {"top_n": {"type": "integer"},
                      "weights": {"type": "object", "description": "optional weights for cost, goal_loss, risk"}}}},
    {"name": "what_if", "description": "Re-run diagnosis and ranking with changed inputs (non-destructive).",
     "input_schema": {"type": "object", "properties": {k: {"type": "number"} for k in
                      ("opening_cash", "monthly_revenue", "monthly_expenses", "min_reserve", "purchase_amount",
                       "revenue_shock_pct", "one_off_shock")}}},
]


def L(x): return f"Rs {x:.1f}L"


class FinTwinAgent:
    def __init__(self, profile=None, decision=None, scenario=None):
        self.profile, self.decision, self.scenario = profile or Profile(), decision or Decision(), scenario or Scenario()
        self.history, self.tool_log = [], []

    # ---------- tools (JSON-serialisable) ----------
    def t_diagnose_decision(self, **_):
        return diagnose(self.profile, self.decision, self.scenario)

    def t_rank_alternatives(self, top_n=3, weights=None, **_):
        r = rank_plans(self.profile, self.decision, self.scenario, weights, int(top_n))
        r.pop("all_feasible"); return r

    def t_what_if(self, **ch):
        p, d, s = replace(self.profile), replace(self.decision), replace(self.scenario)
        for k, v in ch.items():
            if k == "purchase_amount": d.amount = v
            elif k in asdict(p): setattr(p, k, v)
            elif k in asdict(s): setattr(s, k, v)
        r = rank_plans(p, d, s, None, 3); r.pop("all_feasible")
        return {"changes": ch, "diagnosis": diagnose(p, d, s), "ranking": r}

    def call_tool(self, name, args):
        out = getattr(self, "t_" + name)(**(args or {}))
        self.tool_log.append({"tool": name, "args": args, "output": out}); return out

    # ---------- narration of engine output (deterministic) ----------
    @staticmethod
    def narrate_diagnosis(dx):
        a, b = dx["adverse"], dx["base"]
        if a["passes"]:
            return f"Plan holds: cash never drops below {L(a['min_cash'])} (reserve {L(dx['reserve'])}) even in the adverse case."
        c = a["causes"]
        s = (f"{'Looks safe in the base case (lowest cash ' + L(b['min_cash']) + ') but ' if dx['looks_safe_then_fails'] else ''}"
             f"fails under stress: cash hits {L(a['min_cash'])} in month {a['min_month']}, {L(a['shortfall'])} below the {L(dx['reserve'])} reserve "
             f"(first breach month {a['breach_month']}). Drivers by then: purchase {L(c['purchase_paid'])}, lost revenue {L(c['revenue_loss'])}, one-off shock {L(c['one_off_shock'])}.")
        sf = a["single_fixes"]
        if len(sf) == 1:
            s += f" Removing {sf[0]} alone would avoid the breach - it is the decisive driver."
        elif sf:
            s += f" Removing any one of {', '.join(sf)} alone would avoid the breach - a compound failure."
        return s

    @staticmethod
    def narrate_ranking(r):
        if not r["ranked"]:
            return "No feasible alternative found under this scenario - consider a smaller purchase or raising cash."
        lines = [f"{r['n_feasible']} of {r['n_candidates']} candidate plans survive the stress test. Top {len(r['ranked'])}:"]
        for x in r["ranked"]:
            lines.append(f"{x['rank']}. {x['name']} - extra cost {L(x['cost'])}, goal acquired month {x['acquired_month']}, "
                         f"lowest cash {L(x['min_cash'])}, reserve-breach probability {x['breach_prob']*100:.1f}%, score {x['score']}.")
        return "\n".join(lines)

    # ---------- grounding guard ----------
    @staticmethod
    def _numbers(obj, acc):
        if isinstance(obj, dict): [FinTwinAgent._numbers(v, acc) for v in obj.values()]
        elif isinstance(obj, list): [FinTwinAgent._numbers(v, acc) for v in obj]
        elif isinstance(obj, bool): pass
        elif isinstance(obj, (int, float)):
            for v in (obj, obj * 100): acc.update({round(v, 0), round(v, 1), round(v, 2)})
    def ungrounded(self, text, outputs):
        allowed = set(); self._numbers(outputs, allowed)
        bad = []
        for tok in re.findall(r"\d+(?:\.\d+)?", text):
            v = float(tok)
            if v in allowed or round(v, 1) in allowed or (v == int(v) and v <= 12): continue   # small ints = month/list indices
            bad.append(tok)
        return bad

    # ---------- chat ----------
    def chat(self, msg: str) -> str:
        self.tool_log.clear()
        reply = self._llm_chat(msg) if os.getenv("ANTHROPIC_API_KEY") else None
        if reply:
            bad = self.ungrounded(reply, [t["output"] for t in self.tool_log])
            if not bad: return reply
            note = f"\n\n(Guard: LLM draft quoted ungrounded numbers {bad}; showing engine-verified answer.)"
        else: note = ""
        return self._rule_chat(msg) + note

    def _rule_chat(self, msg):
        m = msg.lower()
        ch = {}
        for key, pat in (("opening_cash", r"cash\D{0,12}(\d+(?:\.\d+)?)"), ("min_reserve", r"reserve\D{0,12}(\d+(?:\.\d+)?)"),
                         ("purchase_amount", r"(?:equipment|purchase|buy)\D{0,12}(\d+(?:\.\d+)?)"),
                         ("monthly_revenue", r"revenue\D{0,12}(\d+(?:\.\d+)?)(?!\s*%)")):
            mm = re.search(pat, m)
            if mm: ch[key] = float(mm.group(1))
        sh = re.search(r"revenue\D{0,12}(-?\d+(?:\.\d+)?)\s*%", m)
        if sh: ch["revenue_shock_pct"] = -abs(float(sh.group(1))) / 100; ch.pop("monthly_revenue", None)
        if "what if" in m and ch:
            o = self.call_tool("what_if", ch)
            return f"With {ch}:\n{self.narrate_diagnosis(o['diagnosis'])}\n{self.narrate_ranking(o['ranking'])}"
        if any(w in m for w in ("best", "recommend", "alternative", "instead", "plan", "options")):
            return self.narrate_ranking(self.call_tool("rank_alternatives", {"top_n": 3}))
        if any(w in m for w in ("why", "fail", "risk", "safe", "breach", "afford", "runway")):
            return self.narrate_diagnosis(self.call_tool("diagnose_decision", {}))
        return ("Ask me: 'Can I afford this?', 'Why does it fail?', 'What are the best alternatives?', "
                "or 'What if cash is 10 and revenue drops 30%?'")

    def _llm_chat(self, msg):
        try:
            import anthropic
            client = anthropic.Anthropic()
            msgs = self.history + [{"role": "user", "content": msg}]
            for _ in range(6):
                r = client.messages.create(model=MODEL, max_tokens=1000, system=SYSTEM, tools=TOOLS, messages=msgs)
                if r.stop_reason != "tool_use":
                    text = "".join(b.text for b in r.content if b.type == "text")
                    self.history = msgs + [{"role": "assistant", "content": text}]; return text
                msgs.append({"role": "assistant", "content": r.content})
                res = []
                for b in r.content:
                    if b.type == "tool_use":
                        out = self.call_tool(b.name, b.input)
                        res.append({"type": "tool_result", "tool_use_id": b.id, "content": json.dumps(out)[:20000]})
                msgs.append({"role": "user", "content": res})
        except Exception as e:      # offline / bad key -> deterministic fallback
            self.tool_log.clear(); return None
