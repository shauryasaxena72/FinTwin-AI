"""CLI demo / demo-day fallback: python demo.py"""
from fintwin.copilot import FinTwinAgent
a = FinTwinAgent()
for q in ("Can I afford this equipment?", "What are the best alternatives?", "What if cash 10 and revenue drops 30%?"):
    print(f"\n> {q}\n{a.chat(q)}")
