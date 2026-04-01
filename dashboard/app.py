#!/usr/bin/env python3
"""
BSF-RL-OPTIMIZER Dashboard

Streamlit-based farmer dashboard.  Start with:
    streamlit run dashboard/app.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

from src.translation.waste_translator import WasteTranslator
from src.translation.weather_client import WeatherClient
from src.translation.state_estimator import StateEstimator, BatchInfo, FarmerObservation
from src.translation.recommendation import RecommendationGenerator
from src.baselines.heuristic_policy import HeuristicPolicy


# ── Page config ────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="BSF Feed Optimizer",
    page_icon="🪲",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS ─────────────────────────────────────────────────────────────

st.markdown("""
<style>
  /* Inter font */
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  /* Sidebar */
  [data-testid="stSidebar"] {
    background: linear-gradient(160deg, #0d1b2a 0%, #1b263b 60%, #415a77 100%);
    color: #e0e1dd;
  }
  [data-testid="stSidebar"] * { color: #e0e1dd !important; }
  [data-testid="stSidebar"] .stRadio label { font-size: 1rem; }
  [data-testid="stSidebar"] hr { border-color: #415a77; }

  /* Metric cards */
  [data-testid="metric-container"] {
    background: #1e2d3d;
    border: 1px solid #415a77;
    border-radius: 12px;
    padding: 12px 16px;
  }

  /* Primary button */
  .stButton>button[kind="primary"] {
    background: linear-gradient(90deg, #4fc3f7, #0288d1);
    border: none;
    border-radius: 8px;
    color: #fff;
    font-weight: 600;
  }
  .stButton>button[kind="primary"]:hover {
    background: linear-gradient(90deg, #0288d1, #4fc3f7);
    transform: translateY(-1px);
    box-shadow: 0 4px 15px rgba(79,195,247,0.4);
  }

  /* Info boxes */
  .stSuccess { border-radius: 10px; }
  .stInfo    { border-radius: 10px; }

  /* Main background */
  .main { background-color: #0d1b2a; color: #e0e1dd; }

  /* Day progression banner */
  .day-banner {
    background: linear-gradient(135deg, #1b4332, #2d6a4f);
    border-radius: 14px;
    padding: 18px 24px;
    margin-bottom: 20px;
    border: 1px solid #40916c;
  }
  .day-banner h2 { margin: 0; color: #b7e4c7; }
  .day-banner p { margin: 4px 0 0; color: #d8f3dc; }

  /* Stage badge */
  .stage-badge {
    display: inline-block;
    background: #52b788;
    color: #081c15;
    padding: 4px 14px;
    border-radius: 20px;
    font-weight: 600;
    font-size: 0.85rem;
  }
</style>
""", unsafe_allow_html=True)


# ── Session-state init ──────────────────────────────────────────────────────

def _init():
    defaults = {
        'batch_started': False,
        'batch_info': None,
        'history': [],
        'current_day': 0,                # Simulated day counter
        'day_completed': False,           # Whether today's recommendation was followed
        'pending_recommendation': None,   # Stored recommendation awaiting confirmation
        'pending_action': None,           # Stored action awaiting confirmation
        'pending_feed_amounts': None,     # Stored feed amounts awaiting confirmation
        'policy': HeuristicPolicy(),
        'waste_translator': WasteTranslator(),
        'weather_client': WeatherClient(),
        'state_estimator': StateEstimator(),
        'rec_generator': RecommendationGenerator(),
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ── Helpers ────────────────────────────────────────────────────────────────

LIFECYCLE_STAGES = [
    (0, 2,  "🥚 Neonate",          "Tiny larvae, minimal feeding"),
    (3, 5,  "🐛 Early Growth",     "Growing fast, increasing appetite"),
    (6, 8,  "🐛 Exponential Phase","Peak growth, heavy feeding"),
    (9, 11, "🐛 Late Growth",      "Continued feeding, preparing to mature"),
    (12, 14,"🦋 Pre-Pupa",         "Appetite drops, darkening colour"),
    (15, 16,"✅ Harvest Ready",     "Time to harvest!"),
]

def _get_stage_info(day: int):
    """Return (stage_name, description, progress_fraction) for the given day."""
    for start, end, name, desc in LIFECYCLE_STAGES:
        if start <= day <= end:
            progress = min(1.0, day / 16.0)
            return name, desc, progress
    # Beyond day 16
    return "✅ Harvest Ready", "Time to harvest!", 1.0


# ── Pages ──────────────────────────────────────────────────────────────────

def page_start_batch():
    st.title("🪲 Start New Batch")
    st.markdown("Initialize a new BSF larvae batch and configure its settings.")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Batch Details")
        initial_count = st.number_input(
            "Number of larvae", min_value=100, max_value=100_000,
            value=1_000, step=100
        )
        container_size = st.selectbox(
            "Container size",
            ["Small (10×20 cm)", "Medium (20×30 cm)", "Large (30×50 cm)", "Custom"],
            index=1
        )
        if container_size == "Custom":
            area_cm2 = st.number_input("Area (cm²)", min_value=100, value=600)
        else:
            area_cm2 = {"Small (10×20 cm)": 200, "Medium (20×30 cm)": 600,
                        "Large (30×50 cm)": 1500}[container_size]

        start_date = st.date_input("Batch start date", value=datetime.now().date())

    with col2:
        st.subheader("Farm Location")
        location = st.selectbox(
            "Location preset",
            ["Chennai, India", "Mumbai, India", "Bangalore, India", "Custom"],
            index=0
        )
        if location == "Custom":
            lat = st.number_input("Latitude",  value=13.08)
            lon = st.number_input("Longitude", value=80.27)
        else:
            coords = {"Chennai, India": (13.08, 80.27),
                      "Mumbai, India":  (19.08, 72.88),
                      "Bangalore, India": (12.97, 77.59)}
            lat, lon = coords[location]
        st.info(f"📍 {lat:.2f}°N, {lon:.2f}°E")

    st.markdown("---")

    if st.button("🚀 Start Batch", type="primary"):
        batch = BatchInfo(
            start_date=datetime.combine(start_date, datetime.min.time()),
            initial_count=initial_count,
            estimated_count=initial_count,
            container_area_cm2=area_cm2,
            last_feed_time=datetime.now() - timedelta(hours=12),
            total_feed_kg=0.0
        )
        st.session_state.batch_info = batch
        st.session_state.batch_started = True
        st.session_state.current_day = 0
        st.session_state.day_completed = False
        st.session_state.pending_recommendation = None
        st.session_state.pending_action = None
        st.session_state.pending_feed_amounts = None
        st.session_state.history = []
        st.session_state.weather_client.set_location(lat, lon)
        st.success("✅ Batch started! Head to **Daily Check-in** to get recommendations.")
        st.rerun()


def _render_day_progression(day: int):
    """Render the prominent day-progression banner and progress bar."""
    stage_name, stage_desc, progress = _get_stage_info(day)

    st.markdown(f"""
    <div class="day-banner">
        <h2>📅 Day {day} of 16</h2>
        <p><span class="stage-badge">{stage_name}</span> &nbsp; {stage_desc}</p>
    </div>
    """, unsafe_allow_html=True)

    st.progress(progress, text=f"Lifecycle progress: Day {day}/16 — {stage_name}")


def page_daily_checkin():
    st.title("📋 Daily Check-in")

    batch: BatchInfo = st.session_state.batch_info
    if batch is None:
        st.warning("No active batch. Please start a batch first.")
        return

    day = st.session_state.current_day

    # ── Day Progression Banner ──
    _render_day_progression(day)

    # Check if the batch is complete
    if day >= 16:
        st.success("🎉 **Congratulations!** Your BSF batch has reached harvest stage. "
                   "Head to **History** to review the full batch log.")
        return

    # ── If today's recommendation was already followed, show a message ──
    if st.session_state.day_completed:
        st.info(f"✅ Day {day} is complete! Click below to proceed to the next day.")
        if st.button("➡️ Proceed to Next Day", type="primary"):
            st.session_state.current_day += 1
            st.session_state.day_completed = False
            st.session_state.pending_recommendation = None
            st.session_state.pending_action = None
            st.session_state.pending_feed_amounts = None
            st.rerun()
        return

    # ── Status bar ──
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Day",        f"{day}")
    c2.metric("Population", f"{batch.estimated_count:,}")
    c3.metric("Total Feed", f"{batch.total_feed_kg:.2f} kg")
    c4.metric("Survival",   f"{batch.estimated_count / batch.initial_count * 100:.0f}%")

    st.markdown("---")

    # ── Weather ──
    st.subheader("🌤️ Current Conditions")
    weather = st.session_state.weather_client.get_current_weather()
    wc1, wc2, wc3 = st.columns(3)
    wc1.metric("Temperature", f"{weather.temperature_c:.1f} °C")
    wc2.metric("Humidity",    f"{weather.humidity_pct:.0f} %")
    wc3.markdown(f"**{weather.description}**\n\n*Source: {weather.source}*")

    st.markdown("---")

    # ── Farmer observations ──
    st.subheader("👀 Your Observations")
    oc1, oc2 = st.columns(2)
    with oc1:
        activity  = st.select_slider("Larval activity",
            options=["sluggish", "normal", "very_active"], value="normal")
        mortality = st.select_slider("Dead larvae visible",
            options=["none", "few", "some", "many"], value="none")
    with oc2:
        substrate = st.select_slider("Substrate condition",
            options=["dry", "good", "wet", "soggy"], value="good")
        smell     = st.select_slider("Smell",
            options=["normal", "ammonia", "sour"], value="normal")

    st.markdown("---")

    # ── Available waste ──
    st.subheader("🗑️ Available Waste Today")
    wt = st.session_state.waste_translator
    all_wastes = wt.list_wastes()

    default_sel = [w for w in ["banana_peels", "rice_bran"] if w in all_wastes]
    selected = st.multiselect(
        "What waste do you have?",
        options=all_wastes,
        default=default_sel,
        format_func=wt.get_display_name
    )
    if selected:
        info_str = "  |  ".join(
            f"**{wt.get_display_name(w)}**: C:N {wt.get_cn_ratio(w):.0f}"
            for w in selected if wt.get_cn_ratio(w)
        )
        st.caption(info_str)

    st.markdown("---")

    # ── Get Recommendation ──
    if st.button("🎯 Get Today's Recommendation", type="primary"):
        farmer_obs = FarmerObservation(
            larvae_activity=activity,
            mortality_estimate=mortality,
            substrate_condition=substrate,
            smell=smell
        )

        # Update estimated population
        mult = {"none": 1.0, "few": 0.99, "some": 0.95, "many": 0.85}[mortality]
        batch.estimated_count = int(batch.estimated_count * mult)

        # Use simulated day instead of real time for age_days
        age_days = float(day)

        obs = st.session_state.state_estimator.estimate_state(
            batch_info=batch,
            farmer_obs=farmer_obs,
            weather=weather
        )
        # Override the age_days in observation with our simulated day
        obs[0] = age_days

        action = st.session_state.policy.predict(obs)
        rec = st.session_state.rec_generator.generate(
            action=action,
            available_wastes=selected,
            larvae_count=batch.estimated_count,
            age_days=age_days
        )

        # Store recommendation in session state so it persists across reruns
        st.session_state.pending_recommendation = rec
        st.session_state.pending_action = action
        st.session_state.pending_feed_amounts = rec.feed_amounts
        st.rerun()

    # ── Display pending recommendation (persisted in session state) ──
    rec = st.session_state.pending_recommendation
    if rec is not None:
        st.success("### ✅ Today's Recommendation")
        rc1, rc2 = st.columns([2, 1])
        with rc1:
            st.markdown(f"### 🥬 {rec.feed_instruction}")
            if rec.feed_amounts:
                st.markdown("**Breakdown:**")
                for waste, kg in rec.feed_amounts.items():
                    st.markdown(f"- {wt.get_display_name(waste)}: **{kg:.2f} kg**")
            st.markdown(f"**Target C:N ratio:** {rec.target_cn:.0f}:1")
        with rc2:
            st.markdown(f"**💧 {rec.moisture_action}**")
            st.markdown(f"**🌀 {rec.aeration_action}**")

        if rec.notes:
            st.info("**Notes:**\n" + "\n".join(f"• {n}" for n in rec.notes))

        st.progress(rec.confidence, text=f"Confidence: {rec.confidence*100:.0f}%")

        st.markdown("---")

        # ── Confirm Button (separate from Get Recommendation) ──
        if st.button("✅ I followed this recommendation", type="primary"):
            feed_amounts = st.session_state.pending_feed_amounts or {}
            total_feed = sum(feed_amounts.values()) if feed_amounts else 0.0
            action = st.session_state.pending_action

            batch.total_feed_kg += total_feed
            batch.last_feed_time = datetime.now()

            st.session_state.history.append({
                'date': datetime.now().isoformat(),
                'day': day,
                'feed_kg': total_feed,
                'recommendation': rec.feed_instruction,
                'action': action.tolist() if action is not None else [],
            })

            # Mark today as complete — user can proceed to next day
            st.session_state.day_completed = True
            st.rerun()


def page_history():
    st.title("📊 Batch History")

    batch: BatchInfo = st.session_state.batch_info
    history = st.session_state.history

    if batch is None:
        st.warning("No active batch.")
        return

    if not history:
        st.info("No history yet. Complete some daily check-ins first.")
        return

    day = st.session_state.current_day
    _render_day_progression(day)

    total_feed    = sum(h.get('feed_kg', 0) for h in history)
    total_feed_g  = total_feed * 1000
    survival_rate = batch.estimated_count / max(batch.initial_count, 1)
    mortality_pct = (1 - survival_rate) * 100

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Days Completed", len(history))
    c2.metric("Total Feed",     f"{total_feed:.2f} kg")
    c3.metric("Survival",       f"{survival_rate*100:.0f}%")
    c4.metric("Mortality",      f"{mortality_pct:.0f}%")

    # ── Batch-complete comparison report ──────────────────────────────────
    if day >= 16:
        st.markdown("---")
        st.markdown("## 🏆 Your Batch vs AI — Final Report")
        st.markdown(
            "Your 16-day batch is done! Here's how your day-to-day feeding "
            "compared to the AI optimizer, expert heuristic, and other strategies."
        )

        RESULTS = Path(__file__).parent.parent / "results"
        summary_csv = RESULTS / "summary_comparison.csv"

        if summary_csv.exists():
            bench = pd.read_csv(summary_csv).set_index("strategy")

            # ── Chart 1: Feed used ─────────────────────────────────────
            st.markdown("### 🥬 Total Feed Used (g)")
            st.caption("Lower feed for similar output = better resource efficiency")

            feed_data = {s: bench.loc[s, 'avg_feed_g']
                         for s in ["PPO Agent", "Rule-Based", "Random"] if s in bench.index}
            feed_data["⭐ Your Batch"] = total_feed_g
            feed_df = pd.DataFrame.from_dict(feed_data, orient='index', columns=['Feed Used (g)'])
            st.bar_chart(feed_df, color="#4fc3f7")

            if "Rule-Based" in bench.index:
                rule_feed = bench.loc["Rule-Based", "avg_feed_g"]
                if total_feed_g < rule_feed:
                    st.success(f"✅ You used **{rule_feed - total_feed_g:.0f}g less feed** than the expert baseline!")
                else:
                    st.warning(f"⚠️ You used **{total_feed_g - rule_feed:.0f}g more feed** than the expert baseline.")

            st.markdown("---")

            # ── Chart 2: Mortality ─────────────────────────────────────
            st.markdown("### 💀 Mortality Rate (%)")
            st.caption("Lower mortality = more larvae survived to harvest")

            mort_data = {s: bench.loc[s, 'avg_mortality']
                         for s in ["PPO Agent", "Rule-Based", "Random"] if s in bench.index}
            mort_data["⭐ Your Batch"] = mortality_pct
            mort_df = pd.DataFrame.from_dict(mort_data, orient='index', columns=['Mortality (%)'])
            st.bar_chart(mort_df, color="#ef5350")

            if "Rule-Based" in bench.index:
                rule_mort = bench.loc["Rule-Based", "avg_mortality"]
                if mortality_pct < rule_mort:
                    st.success(f"✅ Your mortality ({mortality_pct:.0f}%) beats the expert baseline ({rule_mort:.0f}%)!")
                else:
                    st.warning(f"⚠️ Your mortality ({mortality_pct:.0f}%) is above the expert baseline ({rule_mort:.0f}%).")

            st.markdown("---")

            # ── Chart 3: Daily feed trend ──────────────────────────────
            st.markdown("### 📅 Your Daily Feed (g/day)")
            st.caption("How much feed you gave each day — the AI would adapt this to larval growth stage")

            daily_df = pd.DataFrame(
                {'Feed (g)': [h.get('feed_kg', 0) * 1000 for h in history]},
                index=[f"Day {h['day']}" for h in history]
            )
            st.bar_chart(daily_df, color="#66bb6a")

            st.markdown("---")

            # ── Verdict ───────────────────────────────────────────────
            st.markdown("### 🧾 Overall Verdict")
            score = 0
            if "Rule-Based" in bench.index:
                if total_feed_g  < bench.loc["Rule-Based", "avg_feed_g"]:    score += 1
                if mortality_pct < bench.loc["Rule-Based", "avg_mortality"]: score += 1

            st.markdown(f"- **Feed:** {total_feed_g:.0f}g used" +
                        (" ✅" if score >= 1 else " ❌"))
            st.markdown(f"- **Mortality:** {mortality_pct:.0f}%" +
                        (" ✅" if score == 2 else " ❌"))

            if score == 2:
                st.success("🏆 **Outstanding!** You beat the expert baseline on both feed and mortality.")
            elif score == 1:
                st.info("👍 **Good!** You beat the expert on one metric. Try to improve the other.")
            else:
                st.warning("📚 **Keep going.** Follow the AI recommendations more closely next batch.")

        else:
            st.info("No benchmark data found. Run `python results/run_real_evaluation.py` to generate it.")

    # ── Daily log ─────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📋 Daily Log")
    for entry in reversed(history):
        with st.expander(f"Day {entry['day']} — {entry['date'][:10]}"):
            st.markdown(f"**Recommendation:** {entry['recommendation']}")
            st.markdown(f"**Feed given:** {entry['feed_kg']:.2f} kg")




def page_analysis():
    st.title("📊 AI Performance Report")
    st.markdown(
        "How does the AI optimizer compare to traditional rule-based farming? "
        "Below are results from **20 simulated BSF batches** per strategy, "
        "run under realistic stochastic weather conditions."
    )

    RESULTS = Path(__file__).parent.parent / "results"
    GRAPHS = [
        ("01_summary_comparison.png",  "Aggregate Metrics",
         "Side-by-side comparison of average biomass, max biomass, average reward, "
         "feed used, mortality rate, and consistency (std deviation) across all strategies."),
        ("02_boxplot_distributions.png", "Result Distributions",
         "Box plots showing the spread of results per strategy. A tighter box = more "
         "consistent. The AI's box is wider, meaning it has higher variance — some great "
         "episodes and some poor ones."),
        ("03_episode_performance.png",  "Episode-by-Episode Performance",
         "Each line is one of the 20 test batches. Shows how biomass (larvae weight) "
         "and total reward evolved across episodes for each strategy."),
        ("04_radar_comparison.png",     "Multi-Metric Radar",
         "A radar chart where bigger area = better overall performance. The AI scores "
         "highest on feed efficiency (Low Feed axis) — using 66% less feed than the "
         "rule-based heuristic."),
        ("05_ppo_improvement.png",      "Head-to-Head: AI vs Baselines",
         "Direct comparison showing the absolute difference between the AI and each "
         "other strategy across key metrics."),
        ("06_biomass_vs_feed.png",      "Biomass vs Feed Used (Efficiency)",
         "Each dot is one episode. Ideal point = top-left (high biomass, low feed). "
         "The AI clusters towards the left — producing larvae using much less feed."),
    ]

    # ── Key stats from CSV ──────────────────────────────────────────────
    summary_csv = RESULTS / "summary_comparison.csv"
    if summary_csv.exists():
        df = pd.read_csv(summary_csv)
        df = df.set_index("strategy")

        st.markdown("### 🔢 Key Numbers at a Glance")
        cols = st.columns(4)
        strategies = ["PPO Agent", "Rule-Based", "Random", "Do-Nothing"]
        icons      = ["🤖", "📚", "🎲", "😴"]
        for col, strat, icon in zip(cols, strategies, icons):
            if strat in df.index:
                row = df.loc[strat]
                col.metric(
                    f"{icon} {strat}",
                    f"{row['avg_biomass']:.0f} mg",
                    help=f"Avg feed: {row['avg_feed_g']:.0f}g | Mortality: {row['avg_mortality']:.0f}%"
                )

        # Feed efficiency highlight
        if "PPO Agent" in df.index and "Rule-Based" in df.index:
            ppo_feed  = df.loc["PPO Agent", "avg_feed_g"]
            rule_feed = df.loc["Rule-Based", "avg_feed_g"]
            saving_pct = (rule_feed - ppo_feed) / rule_feed * 100
            st.success(
                f"💡 **Key finding:** The AI uses **{saving_pct:.0f}% less feed** than rule-based "
                f"({ppo_feed:.0f}g vs {rule_feed:.0f}g per batch) while producing larvae at "
                f"near-expert levels on its best episodes."
            )
    else:
        st.warning("Run `python results/run_real_evaluation.py` first to generate data.")

    st.markdown("---")

    # ── 6 Graphs ────────────────────────────────────────────────────────
    st.markdown("### 📈 Detailed Graphs")
    for filename, title, caption in GRAPHS:
        img_path = RESULTS / filename
        if img_path.exists():
            st.markdown(f"#### {title}")
            st.image(str(img_path), use_container_width=True)
            st.caption(caption)
            st.markdown("")
        else:
            st.warning(f"Graph not found: {filename} — run `generate_comparison_graphs.py`")

    st.markdown("---")

    # ── Insight summary ─────────────────────────────────────────────────
    st.markdown("### 🧠 What This Means")
    st.markdown("""
    | Insight | Detail |
    |---------|--------|
    | **Feed Efficiency** | AI uses ~66% less feed — direct cost savings for farmers |
    | **Peak Performance** | AI's best episodes (150mg) match expert heuristic (153mg) |
    | **Consistency** | AI is still high-variance — more training needed for reliability |
    | **vs Real Farmers** | Our heuristic is the *ideal* scientist-farmer with sensors; real farmers likely do less |
    | **Mortality** | AI: 83.9% → Rule-Based: 79% → gap closing with more training |
    """)


def _load_ppo_model(model_path: str = "outputs/models/best_model"):
    """
    Load the PPO model with its VecNormalize stats and store a
    policy wrapper in session_state. The wrapper normalises raw
    observations (from the state estimator) before passing them
    to the neural network — fixing the Celsius/Fahrenheit mismatch
    where the model was trained on normalised inputs but the dashboard
    was feeding it raw values.
    """
    import glob as _glob
    from stable_baselines3 import PPO as _PPO
    from stable_baselines3.common.vec_env import DummyVecEnv as _DVE, VecNormalize as _VN
    from stable_baselines3.common.monitor import Monitor as _Mon
    from src.environments.bsf_env import BSFEnv as _BSFEnv

    MODELS = Path("outputs/models")
    vecnorm_files = sorted(_glob.glob(str(MODELS / "*vecnormalize*.pkl")))
    vecnorm_path  = vecnorm_files[-1] if vecnorm_files else None

    try:
        vec_env  = _DVE([lambda: _Mon(_BSFEnv(stochastic_weather=True))])
        if vecnorm_path:
            vec_norm = _VN.load(vecnorm_path, vec_env)
        else:
            vec_norm = _VN(vec_env, norm_obs=True, norm_reward=False, clip_obs=10.0)
        vec_norm.training    = False
        vec_norm.norm_reward = False
        model = _PPO.load(model_path, env=vec_norm)

        class _PPOWrapper:
            name = "PPO RL Model"
            def __init__(self, m, vn):
                self._model = m
                self._vn    = vn
            def predict(self, obs, deterministic=True):
                # Normalise raw observation before passing to the network
                obs_norm = self._vn.normalize_obs(obs.reshape(1, -1))
                action, _ = self._model.predict(obs_norm, deterministic=deterministic)
                return action.flatten()
            def reset(self):
                pass

        st.session_state.policy = _PPOWrapper(model, vec_norm)
        vn_name = Path(vecnorm_path).name if vecnorm_path else "(no stats)"
        st.success(f"✅ PPO model loaded! VecNormalize: `{vn_name}`")
        st.rerun()
    except Exception as exc:
        st.error(f"❌ Could not load RL model: {exc}")


def page_settings():
    st.title("⚙️ Settings")

    current = getattr(st.session_state.get('policy'), 'name', 'Unknown')
    st.info(f"🟢 **Currently active policy:** `{current}`")

    st.markdown("---")
    st.subheader("🤖 Choose Optimization Policy")
    st.markdown(
        "- **Heuristic** — expert rules from BSF biology research. Reliable and consistent.\n"
        "- **RL Model** — neural network trained on 10,000+ batches. More feed-efficient, "
        "still improving on consistency with more training."
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 📚 Rule-Based Heuristic")
        if st.button("✅ Switch to Heuristic"):
            st.session_state.policy = HeuristicPolicy()
            st.session_state.policy.name = "Heuristic (Rule-Based)"
            st.success("Switched to Heuristic.")
            st.rerun()

    with col2:
        st.markdown("#### 🤖 Trained PPO Model")
        if st.button("🤖 Load & Switch to RL Model"):
            _load_ppo_model()

    with st.expander("🔧 Advanced: load a specific checkpoint"):
        custom_path = st.text_input("Model path (without .zip)", "outputs/models/best_model")
        if st.button("Load from path"):
            _load_ppo_model(custom_path)

    st.markdown("---")
    st.subheader("🗑️ End Current Batch")
    if st.button("🗑️ End Batch", type="secondary"):
        st.session_state.batch_started = False
        st.session_state.batch_info    = None
        st.session_state.history       = []
        st.session_state.current_day   = 0
        st.session_state.day_completed = False
        st.session_state.pending_recommendation = None
        st.session_state.pending_action = None
        st.session_state.pending_feed_amounts = None
        st.success("Batch ended. You can start a new one.")
        st.rerun()


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    _init()

    # Sidebar
    st.sidebar.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5f/BSF_larva.jpg/320px-BSF_larva.jpg",
        use_container_width=True,
        caption="Black Soldier Fly Larvae"
    )
    st.sidebar.title("🪲 BSF Optimizer")

    if st.session_state.batch_started:
        pages = ["Daily Check-in", "History", "AI Performance Report", "Settings"]
    else:
        pages = ["Start Batch", "AI Performance Report", "Settings"]

    page = st.sidebar.radio("Navigate", pages, index=0)

    # Active batch summary in sidebar
    if st.session_state.batch_info:
        st.sidebar.markdown("---")
        b = st.session_state.batch_info
        day = st.session_state.current_day
        stage_name, _, _ = _get_stage_info(day)
        st.sidebar.markdown(f"**Active Batch — Day {day}**")
        st.sidebar.markdown(f"Stage: {stage_name}")
        st.sidebar.markdown(f"Population: {b.estimated_count:,}")
        st.sidebar.markdown(f"Feed used:  {b.total_feed_kg:.2f} kg")

    # Route
    if page == "Start Batch":
        page_start_batch()
    elif page == "Daily Check-in":
        page_daily_checkin()
    elif page == "History":
        page_history()
    elif page == "AI Performance Report":
        page_analysis()
    elif page == "Settings":
        page_settings()


if __name__ == "__main__":
    main()
