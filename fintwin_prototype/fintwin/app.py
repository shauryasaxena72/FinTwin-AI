import streamlit as st, plotly.graph_objects as go, pandas as pd
from fintwin.engine import Profile, Decision, Scenario, BASE, diagnose
from fintwin.planner import rank_plans
from fintwin.copilot import FinTwinAgent

st.set_page_config(page_title="FinTwin AI", layout="wide")
st.title("FinTwin AI - Financial Digital Twin")
st.caption("Amounts in Rs lakh. Engine computes every number; copilot only explains.")

with st.sidebar:
    st.header("Finances")
    cash = st.number_input("Opening cash", 0.0, 500.0, 8.0, 0.5)
    rev = st.number_input("Monthly revenue", 0.0, 500.0, 5.0, 0.5)
    exp = st.number_input("Monthly expenses", 0.0, 500.0, 4.0, 0.5)
    debt = st.number_input("Monthly debt service", 0.0, 100.0, 0.0, 0.1)
    reserve = st.number_input("Minimum reserve", 0.0, 100.0, 3.0, 0.5)
    lag = st.slider("Collection lag (months)", 0, 3, 0)
    st.header("Decision")
    label = st.text_input("Decision", "Buy equipment")
    amount = st.number_input("Amount", 0.0, 500.0, 4.0, 0.5)
    st.header("Adverse scenario")
    shock = st.slider("Revenue shock %", -50, 0, -20) / 100
    one_off = st.number_input("One-off shock", 0.0, 50.0, 1.5, 0.5)
    one_m = st.slider("One-off month", 0, 12, 3)
    st.header("Optimizer weights")
    wc, wg, wr = (st.slider(n, 0.0, 1.0, v, 0.05) for n, v in (("Cost", .3), ("Goal loss", .3), ("Risk", .4)))

profile = Profile(cash, rev, exp, debt, reserve, lag)
decision, sc = Decision(label, amount), Scenario("adverse", shock, 1, one_off, one_m)

@st.cache_data(show_spinner="Simulating...")
def run(p, d, s, w):
    return diagnose(p, d, s), rank_plans(p, d, s, w, 3)
dx, rk = run(profile, decision, sc, {"cost": wc, "goal_loss": wg, "risk": wr})
a = dx["adverse"]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Original plan", "PASSES" if a["passes"] else "FAILS")
c2.metric("Lowest cash (adverse)", f"{a['min_cash']:.1f}", f"month {a['min_month']}")
c3.metric("Shortfall vs reserve", f"{a['shortfall']:.1f}")
c4.metric("Feasible alternatives", f"{rk['n_feasible']}/{rk['n_candidates']}")
if dx["looks_safe_then_fails"]:
    st.warning("Looks safe in the base case, but fails under stress.")
if not a["passes"]:
    st.write("**Drivers by breach month:**", a["causes"], "| Alone-fixes:", a["single_fixes"])

fig = go.Figure()
x = list(range(profile.horizon + 1))
fig.add_scatter(x=x, y=dx["base"]["cash"], name="As-is (base)")
fig.add_scatter(x=x, y=a["cash"], name="As-is (adverse)", line=dict(color="red"))
for r in rk["ranked"]:
    fig.add_scatter(x=x, y=r["cash_path"], name=f"#{r['rank']} {r['name'][:38]}")
fig.add_hline(y=reserve, line_dash="dash", annotation_text="Min reserve")
fig.update_layout(xaxis_title="Month", yaxis_title="Cash (Rs lakh)", height=430)
st.plotly_chart(fig, width="stretch")

st.subheader("Top ranked plans")
if rk["ranked"]:
    st.dataframe(pd.DataFrame(rk["ranked"])[["rank", "name", "cost", "goal_loss", "acquired_month", "breach_prob",
                                           "min_cash", "expense_cut", "score"]], hide_index=True)
else:
    st.error("No feasible alternative - reduce the purchase or raise cash.")

st.subheader("Grounded copilot")
if "agent" not in st.session_state:
    st.session_state.agent, st.session_state.msgs = FinTwinAgent(), []
ag = st.session_state.agent
ag.profile, ag.decision, ag.scenario = profile, decision, sc
for role, txt in st.session_state.msgs:
    st.chat_message(role).write(txt)
if q := st.chat_input("Can I afford this? Why does it fail? What if cash is 10?"):
    st.chat_message("user").write(q)
    ans = ag.chat(q)
    st.chat_message("assistant").write(ans)
    st.session_state.msgs += [("user", q), ("assistant", ans)]
