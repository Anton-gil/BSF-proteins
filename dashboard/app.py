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
</style>
""", unsafe_allow_html=True)


# ── Session-state init ──────────────────────────────────────────────────────

def _init():
    defaults = {
        'batch_started': False,
        'batch_info': None,
        'history': [],
        'policy': HeuristicPolicy(),
        'waste_translator': WasteTranslator(),
        'weather_client': WeatherClient(),
        'state_estimator': StateEstimator(),
        'rec_generator': RecommendationGenerator(),
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


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
        st.session_state.history = []
        st.session_state.weather_client.set_location(lat, lon)
        st.success("✅ Batch started! Head to **Daily Check-in** to get recommendations.")
        st.rerun()


def page_daily_checkin():
    st.title("📋 Daily Check-in")

    batch: BatchInfo = st.session_state.batch_info
    if batch is None:
        st.warning("No active batch. Please start a batch first.")
        return

    age_days = (datetime.now() - batch.start_date).days

    # ── Status bar ──
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Day",        f"{age_days}")
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

        obs = st.session_state.state_estimator.estimate_state(
            batch_info=batch,
            farmer_obs=farmer_obs,
            weather=weather
        )
        action = st.session_state.policy.predict(obs)
        rec = st.session_state.rec_generator.generate(
            action=action,
            available_wastes=selected,
            larvae_count=batch.estimated_count,
            age_days=float(age_days)
        )

        # ── Display ──
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

        if st.button("✅ I followed this recommendation"):
            total_feed = sum(rec.feed_amounts.values())
            batch.total_feed_kg += total_feed
            batch.last_feed_time = datetime.now()
            st.session_state.history.append({
                'date': datetime.now().isoformat(),
                'day': age_days,
                'feed_kg': total_feed,
                'recommendation': rec.feed_instruction,
                'action': action.tolist()
            })
            st.success("Recorded! Check back tomorrow.")


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

    total_feed = sum(h.get('feed_kg', 0) for h in history)
    c1, c2, c3 = st.columns(3)
    c1.metric("Days Tracked", len(history))
    c2.metric("Total Feed",   f"{total_feed:.2f} kg")
    c3.metric("Population",   f"{batch.estimated_count:,}")

    st.markdown("---")
    st.subheader("Daily Log")

    for entry in reversed(history):
        with st.expander(f"Day {entry['day']} — {entry['date'][:10]}"):
            st.markdown(f"**Recommendation:** {entry['recommendation']}")
            st.markdown(f"**Feed given:** {entry['feed_kg']:.2f} kg")


def page_settings():
    st.title("⚙️ Settings")

    st.subheader("Optimization Policy")
    choice = st.selectbox(
        "Policy",
        ["Heuristic (Rule-based)", "Trained RL Model"],
        index=0
    )

    if choice == "Trained RL Model":
        model_path = st.text_input("Model path", "outputs/models/best_model")
        if st.button("Load Model"):
            try:
                from src.agents.ppo_agent import BSFPPOAgent
                agent = BSFPPOAgent.load(model_path)

                class _RLWrapper:
                    name = "PPO-RL"
                    def predict(self, obs, deterministic=True):
                        return agent.predict(obs, deterministic)

                st.session_state.policy = _RLWrapper()
                st.success("✅ RL model loaded successfully!")
            except Exception as exc:
                st.error(f"Could not load model: {exc}")
    else:
        st.session_state.policy = HeuristicPolicy()
        st.info("Using rule-based heuristic policy.")

    st.markdown("---")
    st.subheader("End Current Batch")
    if st.button("🗑️ End Batch", type="secondary"):
        st.session_state.batch_started = False
        st.session_state.batch_info    = None
        st.session_state.history       = []
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
        pages = ["Daily Check-in", "History", "Settings"]
    else:
        pages = ["Start Batch", "Settings"]

    page = st.sidebar.radio("Navigate", pages, index=0)

    # Active batch summary in sidebar
    if st.session_state.batch_info:
        st.sidebar.markdown("---")
        b = st.session_state.batch_info
        age = (datetime.now() - b.start_date).days
        st.sidebar.markdown(f"**Active Batch — Day {age}**")
        st.sidebar.markdown(f"Population: {b.estimated_count:,}")
        st.sidebar.markdown(f"Feed used:  {b.total_feed_kg:.2f} kg")

    # Route
    if page == "Start Batch":
        page_start_batch()
    elif page == "Daily Check-in":
        page_daily_checkin()
    elif page == "History":
        page_history()
    elif page == "Settings":
        page_settings()


if __name__ == "__main__":
    main()
