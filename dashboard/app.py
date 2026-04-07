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

# Optional plotly import
try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False


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

  /* Styled expanders */
  .streamlit-expanderHeader {
    background: #1e2d3d;
    border-radius: 8px;
    font-weight: 600;
  }

  /* Better table styling */
  .stDataFrame table {
    border-radius: 8px;
    overflow: hidden;
  }
  .stDataFrame th {
    background: #1b263b !important;
    color: #e0e1dd !important;
  }

  /* Smooth transitions on interactive elements */
  .stButton > button {
    transition: all 0.2s ease;
  }

  /* Lifecycle timeline */
  .lifecycle-row {
    display: flex;
    align-items: center;
    padding: 6px 12px;
    border-radius: 8px;
    margin-bottom: 4px;
    transition: background 0.2s;
  }
  .lifecycle-row:hover { background: #1e2d3d; }
  .lifecycle-day { min-width: 80px; font-weight: 600; color: #4fc3f7; }
  .lifecycle-icon { min-width: 30px; font-size: 1.1rem; }
  .lifecycle-name { min-width: 160px; font-weight: 500; }
  .lifecycle-desc { color: #a0a0a0; }

  /* Action card */
  .action-card {
    background: #1e2d3d;
    border: 1px solid #415a77;
    border-radius: 10px;
    padding: 10px 14px;
    margin-bottom: 6px;
  }
  .action-label { color: #4fc3f7; font-weight: 600; font-size: 0.85rem; }
  .action-value { font-size: 1rem; margin-top: 2px; }
</style>
""", unsafe_allow_html=True)


# ── Session-state init ──────────────────────────────────────────────────────

def _init():
    defaults = {
        'batch_started': False,
        'batch_info': None,
        'history': [],
        'current_day': 0,           # Simulated day counter
        'checkin_phase': 0,         # 0=form  1=show_rec  2=day_done
        'pending_rec': None,        # Stored DailyRecommendation
        'pending_action': None,     # Stored np.ndarray action
        'pending_weather': None,    # Weather snapshot used for this rec
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


def _load_results_csv():
    """Load summary_comparison.csv if available."""
    csv_path = Path(__file__).parent.parent / "results" / "summary_comparison.csv"
    if csv_path.exists():
        return pd.read_csv(csv_path).set_index("strategy")
    return None


def _interpret_action(action_val, action_type):
    """Convert a 0-1 action value to a human-readable description."""
    if action_type == "cn_target":
        if action_val < 0.3:
            return f"{action_val:.2f} → Carbon-heavy (high C:N)"
        elif action_val < 0.7:
            return f"{action_val:.2f} → Balanced mix"
        else:
            return f"{action_val:.2f} → Nitrogen-heavy (low C:N)"
    elif action_type == "feed_amount":
        if action_val < 0.15:
            return f"{action_val:.2f} → No feeding"
        elif action_val < 0.4:
            return f"{action_val:.2f} → Light feeding"
        elif action_val < 0.7:
            return f"{action_val:.2f} → Moderate feeding"
        else:
            return f"{action_val:.2f} → Heavy feeding"
    elif action_type == "moisture":
        if action_val < 0.3:
            return f"{action_val:.2f} → Ventilate (dry out)"
        elif action_val < 0.7:
            return f"{action_val:.2f} → No change"
        else:
            return f"{action_val:.2f} → Add water"
    elif action_type == "aeration":
        if action_val < 0.33:
            return f"{action_val:.2f} → Low aeration"
        elif action_val < 0.66:
            return f"{action_val:.2f} → Medium aeration"
        else:
            return f"{action_val:.2f} → High aeration"
    return f"{action_val:.2f}"


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

    # ── What to Expect ─────────────────────────────────────────────────
    st.markdown("---")
    st.info(
        "📋 **What to Expect:**\n\n"
        "- Your batch will run for **16 days** (the full BSF larval lifecycle)\n"
        "- You'll do a **daily check-in** where you report observations and receive AI-powered feeding recommendations\n"
        "- Each day you'll be asked about: larval activity, mortality, substrate condition, smell, and available waste\n"
        "- The AI will then tell you exactly how much and what to feed"
    )

    # ── BSF Lifecycle Preview ──────────────────────────────────────────
    st.subheader("🔬 BSF Lifecycle Preview")
    st.markdown("Here's what to expect across the 16-day growing period:")

    for start, end, name, desc in LIFECYCLE_STAGES:
        st.markdown(
            f'<div class="lifecycle-row">'
            f'<span class="lifecycle-day">Day {start}–{end}</span>'
            f'<span class="lifecycle-name">{name}</span>'
            f'<span class="lifecycle-desc">{desc}</span>'
            f'</div>',
            unsafe_allow_html=True
        )


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

    day   = st.session_state.current_day
    phase = st.session_state.checkin_phase   # 0=form  1=show_rec  2=day_done
    wt    = st.session_state.waste_translator

    # ── Day Progression Banner ──
    _render_day_progression(day)

    # ── Harvest gate ──
    if day >= 16:
        st.success("🎉 **Congratulations!** Your BSF batch has reached harvest stage. "
                   "Head to **History** to review the full batch log.")
        return

    # ── Status bar (always visible) ──
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Day",        f"{day} / 16")
    c2.metric("Population", f"{batch.estimated_count:,}")
    c3.metric("Total Feed", f"{batch.total_feed_kg:.2f} kg")
    c4.metric("Survival",   f"{batch.estimated_count / batch.initial_count * 100:.0f}%")

    st.markdown("---")

    # ══════════════════════════════════════════════
    # PHASE 2: Day is done — advance to next day
    # ══════════════════════════════════════════════
    if phase == 2:
        rec = st.session_state.pending_rec
        st.success(f"### ✅ Day {day} Complete!")

        # Summarise what was done
        if rec and rec.feed_amounts:
            st.markdown("**You fed:**")
            for waste, kg in rec.feed_amounts.items():
                st.markdown(f"  - {wt.get_display_name(waste)}: **{kg:.2f} kg**")
        if rec:
            total = sum(rec.feed_amounts.values()) if rec.feed_amounts else 0
            st.markdown(f"**Total feed:** {total:.2f} kg")

        st.markdown("")
        st.info("Click the button below to load tomorrow's check-in.")

        if st.button("➡️ Proceed to Day " + str(day + 1), type="primary", key="next_day_btn"):
            st.session_state.current_day  += 1
            st.session_state.checkin_phase = 0
            st.session_state.pending_rec   = None
            st.session_state.pending_action = None
            st.session_state.pending_weather = None
            st.rerun()
        return

    # ══════════════════════════════════════════════
    # PHASE 1: Show recommendation, await confirm
    # ══════════════════════════════════════════════
    if phase == 1:
        rec = st.session_state.pending_rec
        weather = st.session_state.pending_weather

        # Show weather that was captured
        if weather:
            st.subheader("🌤️ Conditions Used")
            wc1, wc2, wc3 = st.columns(3)
            wc1.metric("Temperature", f"{weather.temperature_c:.1f} °C")
            wc2.metric("Humidity",    f"{weather.humidity_pct:.0f} %")
            wc3.markdown(f"**{weather.description}**\n\n*Source: {weather.source}*")
            st.markdown("---")

        st.success("### 🎯 Today's Recommendation")
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

        col_confirm, col_back = st.columns([3, 1])
        with col_confirm:
            if st.button("✅ I followed this recommendation — go to next day",
                         type="primary", key="confirm_btn"):
                # ── Record the day ──
                total_feed = sum(rec.feed_amounts.values()) if rec.feed_amounts else 0.0
                action     = st.session_state.pending_action

                batch.total_feed_kg   += total_feed
                batch.last_feed_time   = datetime.now()
                # Adjust estimated count by severity observed (captured during form)
                st.session_state.history.append({
                    'date':           datetime.now().isoformat(),
                    'day':            day,
                    'feed_kg':        total_feed,
                    'recommendation': rec.feed_instruction,
                    'action':         action.tolist() if action is not None else [],
                })
                st.session_state.checkin_phase = 2   # → day done screen
                st.rerun()

        with col_back:
            if st.button("🔄 Redo", key="redo_btn"):
                st.session_state.checkin_phase = 0
                st.session_state.pending_rec   = None
                st.rerun()
        return

    # ══════════════════════════════════════════════
    # PHASE 0: Input form → generate recommendation
    # ══════════════════════════════════════════════

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
    all_wastes  = wt.list_wastes()
    default_sel = [w for w in ["banana_peels", "rice_bran"] if w in all_wastes]
    selected    = st.multiselect(
        "What waste do you have?",
        options=all_wastes,
        default=default_sel,
        format_func=wt.get_display_name
    )
    if selected:
        st.caption("  |  ".join(
            f"**{wt.get_display_name(w)}**: C:N {wt.get_cn_ratio(w):.0f}"
            for w in selected if wt.get_cn_ratio(w)
        ))

    st.markdown("---")

    if st.button("🎯 Get Today's Recommendation", type="primary", key="get_rec_btn"):
        farmer_obs = FarmerObservation(
            larvae_activity=activity,
            mortality_estimate=mortality,
            substrate_condition=substrate,
            smell=smell
        )

        # Adjust estimated population based on mortality observation
        mult = {"none": 1.0, "few": 0.99, "some": 0.95, "many": 0.85}[mortality]
        batch.estimated_count = int(batch.estimated_count * mult)

        age_days = float(day)
        obs      = st.session_state.state_estimator.estimate_state(
            batch_info=batch,
            farmer_obs=farmer_obs,
            weather=weather
        )
        obs[0]   = age_days   # override with simulated day

        action = st.session_state.policy.predict(obs)
        rec    = st.session_state.rec_generator.generate(
            action=action,
            available_wastes=selected,
            larvae_count=batch.estimated_count,
            age_days=age_days
        )

        # Persist to session state and advance to phase 1
        st.session_state.pending_rec     = rec
        st.session_state.pending_action  = action
        st.session_state.pending_weather = weather
        st.session_state.checkin_phase   = 1
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

    # ── Running Charts (during batch) ─────────────────────────────────────
    if len(history) >= 2:
        st.markdown("---")
        st.subheader("📈 Batch Progress Charts")

        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            # Cumulative feed over days
            cumulative_feed = []
            running_total = 0.0
            for h in history:
                running_total += h.get('feed_kg', 0)
                cumulative_feed.append({'Day': h['day'], 'Cumulative Feed (kg)': round(running_total, 3)})
            feed_chart_df = pd.DataFrame(cumulative_feed).set_index('Day')

            if HAS_PLOTLY:
                fig = px.area(feed_chart_df, y='Cumulative Feed (kg)',
                              title='Cumulative Feed Over Time',
                              template='plotly_dark')
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                  font_color='#e0e1dd')
                fig.update_traces(fillcolor='rgba(79,195,247,0.3)', line_color='#4fc3f7')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.area_chart(feed_chart_df, color='#4fc3f7')

        with chart_col2:
            # Population estimate over days (estimated from mortality observations)
            pop_data = [{'Day': 0, 'Population': batch.initial_count}]
            est_pop = batch.initial_count
            for h in history:
                # Approximate: each day we applied mortality multiplier
                factor = 0.99  # default estimate
                pop_data.append({'Day': h['day'], 'Population': int(est_pop * factor)})
                est_pop = int(est_pop * factor)
            # override last point with actual current estimate
            pop_data[-1]['Population'] = batch.estimated_count
            pop_df = pd.DataFrame(pop_data).set_index('Day')

            if HAS_PLOTLY:
                fig = px.line(pop_df, y='Population',
                              title='Estimated Population Over Time',
                              template='plotly_dark')
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                  font_color='#e0e1dd')
                fig.update_traces(line_color='#66bb6a')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.line_chart(pop_df, color='#66bb6a')

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

            # ── Chart 1: Feed used (Plotly horizontal bar) ─────────────
            st.markdown("### 🥬 Total Feed Used (g)")
            st.caption("Lower feed for similar output = better resource efficiency")

            feed_data = {}
            for s in ["PPO Agent", "Rule-Based", "Random"]:
                if s in bench.index:
                    feed_data[s] = bench.loc[s, 'avg_feed_g']
            feed_data["⭐ Your Batch"] = total_feed_g

            if HAS_PLOTLY:
                feed_df = pd.DataFrame({
                    'Strategy': list(feed_data.keys()),
                    'Feed Used (g)': list(feed_data.values())
                })
                colors = ['#4fc3f7' if s != '⭐ Your Batch' else '#FFD700'
                          for s in feed_df['Strategy']]
                fig = px.bar(feed_df, x='Feed Used (g)', y='Strategy', orientation='h',
                             template='plotly_dark')
                fig.update_traces(marker_color=colors)
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                  font_color='#e0e1dd', showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                feed_df = pd.DataFrame.from_dict(feed_data, orient='index', columns=['Feed Used (g)'])
                st.bar_chart(feed_df, color="#4fc3f7")

            if "Rule-Based" in bench.index:
                rule_feed = bench.loc["Rule-Based", "avg_feed_g"]
                if total_feed_g < rule_feed:
                    st.success(f"✅ You used **{rule_feed - total_feed_g:.0f}g less feed** than the expert baseline!")
                else:
                    st.warning(f"⚠️ You used **{total_feed_g - rule_feed:.0f}g more feed** than the expert baseline.")

            st.markdown("---")

            # ── Chart 2: Mortality (Plotly horizontal bar) ─────────────
            st.markdown("### 💀 Mortality Rate (%)")
            st.caption("Lower mortality = more larvae survived to harvest")

            mort_data = {}
            for s in ["PPO Agent", "Rule-Based", "Random"]:
                if s in bench.index:
                    mort_data[s] = bench.loc[s, 'avg_mortality']
            mort_data["⭐ Your Batch"] = mortality_pct

            if HAS_PLOTLY:
                mort_df = pd.DataFrame({
                    'Strategy': list(mort_data.keys()),
                    'Mortality (%)': list(mort_data.values())
                })
                colors = ['#ef5350' if s != '⭐ Your Batch' else '#FFD700'
                          for s in mort_df['Strategy']]
                fig = px.bar(mort_df, x='Mortality (%)', y='Strategy', orientation='h',
                             template='plotly_dark')
                fig.update_traces(marker_color=colors)
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                  font_color='#e0e1dd', showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
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

            if HAS_PLOTLY:
                daily_df = pd.DataFrame({
                    'Day': [f"Day {h['day']}" for h in history],
                    'Feed (g)': [h.get('feed_kg', 0) * 1000 for h in history]
                })
                fig = px.bar(daily_df, x='Day', y='Feed (g)', template='plotly_dark')
                fig.update_traces(marker_color='#66bb6a')
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                  font_color='#e0e1dd')
                st.plotly_chart(fig, use_container_width=True)
            else:
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

            # ── Download Report ────────────────────────────────────────
            st.markdown("---")
            report_text = (
                f"BSF Batch Report\n"
                f"================\n"
                f"Date: {datetime.now().strftime('%Y-%m-%d')}\n"
                f"Days: {len(history)}\n"
                f"Total Feed: {total_feed_g:.0f}g\n"
                f"Survival Rate: {survival_rate*100:.0f}%\n"
                f"Mortality: {mortality_pct:.0f}%\n\n"
                f"Benchmark Comparison\n"
                f"--------------------\n"
            )
            for s in ["PPO Agent", "Rule-Based", "Random"]:
                if s in bench.index:
                    row = bench.loc[s]
                    report_text += f"{s}: Biomass={row['avg_biomass']:.0f}mg, Feed={row['avg_feed_g']:.0f}g, Mortality={row['avg_mortality']:.0f}%\n"

            st.download_button(
                "📥 Download Batch Report",
                data=report_text,
                file_name=f"bsf_batch_report_{datetime.now().strftime('%Y%m%d')}.txt",
                mime="text/plain"
            )

        else:
            st.info("No benchmark data found. Run `python results/run_real_evaluation.py` to generate it.")

    # ── Daily log ─────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📋 Daily Log")
    for entry in reversed(history):
        with st.expander(f"Day {entry['day']} — {entry['date'][:10]}"):
            st.markdown(f"**Recommendation:** {entry['recommendation']}")
            st.markdown(f"**Feed given:** {entry['feed_kg']:.2f} kg")

            # Show action vector with human-readable interpretation
            action = entry.get('action', [])
            if action and len(action) >= 4:
                st.markdown("**AI Action Vector:**")
                action_labels = [
                    ("🎯 Feed C:N target", action[0], "cn_target"),
                    ("🥬 Feed amount", action[1], "feed_amount"),
                    ("💧 Moisture action", action[2], "moisture"),
                    ("🌀 Aeration level", action[3], "aeration"),
                ]
                for label, val, atype in action_labels:
                    interp = _interpret_action(val, atype)
                    st.markdown(
                        f'<div class="action-card">'
                        f'<span class="action-label">{label}</span><br>'
                        f'<span class="action-value">{interp}</span>'
                        f'</div>',
                        unsafe_allow_html=True
                    )




def page_analysis():
    st.title("📊 AI Performance Report")
    st.markdown(
        "How does the AI optimizer compare to traditional rule-based farming? "
        "Below are results from **20 simulated BSF batches** per strategy, "
        "run under realistic stochastic weather conditions."
    )

    RESULTS = Path(__file__).parent.parent / "results"

    # ── How This Works Explainer ─────────────────────────────────────────
    with st.expander("🔍 How does the AI learn?"):
        st.markdown("""
The AI (PPO Agent) is a neural network that learned to manage BSF larvae
by running **52,000+ simulated 16-day batches**. Each batch involves 96
decisions (every 4 hours). It receives:

**INPUT (what the AI sees):**
→ Temperature, humidity, larval age, biomass estimate, substrate level,
  C:N ratio, moisture %, hours since last feed

**OUTPUT (what the AI decides):**
→ Feed amount, feed type (C:N ratio), moisture action, aeration level

It was trained using **Proximal Policy Optimization (PPO)** to maximise
larval biomass while minimising feed waste and mortality.

The neural network has **128×128 neurons** in both the policy (what to do)
and value (how good is this state) heads, totalling 36,489 trainable parameters.
        """)

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
         "highest on feed efficiency (Low Feed axis) — using significantly less feed than the "
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

        # ── Dynamic computed insights ──────────────────────────────────
        if "PPO Agent" in df.index and "Rule-Based" in df.index:
            ppo = df.loc["PPO Agent"]
            rule = df.loc["Rule-Based"]

            feed_saving = (rule['avg_feed_g'] - ppo['avg_feed_g']) / rule['avg_feed_g'] * 100
            biomass_diff = ppo['avg_biomass'] - rule['avg_biomass']
            mortality_diff = rule['avg_mortality'] - ppo['avg_mortality']

            st.markdown("### 🏆 AI vs Expert Heuristic")

            m1, m2, m3 = st.columns(3)
            m1.metric("Feed Savings", f"{feed_saving:.0f}%",
                      delta=f"{ppo['avg_feed_g']:.0f}g vs {rule['avg_feed_g']:.0f}g",
                      delta_color="inverse")
            m2.metric("Biomass Advantage", f"{biomass_diff:+.1f} mg",
                      delta=f"{ppo['avg_biomass']:.0f} vs {rule['avg_biomass']:.0f} mg",
                      delta_color="normal" if biomass_diff > 0 else "inverse")
            m3.metric("Mortality Improvement", f"{mortality_diff:+.1f}%",
                      delta=f"{ppo['avg_mortality']:.0f}% vs {rule['avg_mortality']:.0f}%",
                      delta_color="inverse")

            if biomass_diff > 0 and feed_saving > 0:
                st.success(
                    f"💡 **The AI outperforms the expert heuristic!** It produces "
                    f"**{biomass_diff:.0f} mg more biomass** while using **{feed_saving:.0f}% less feed** "
                    f"({ppo['avg_feed_g']:.0f}g vs {rule['avg_feed_g']:.0f}g per batch), "
                    f"with **{mortality_diff:.0f}% lower mortality**."
                )
            elif feed_saving > 0:
                st.success(
                    f"💡 **Key finding:** The AI uses **{feed_saving:.0f}% less feed** than rule-based "
                    f"({ppo['avg_feed_g']:.0f}g vs {rule['avg_feed_g']:.0f}g per batch) while producing larvae at "
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

    # ── Per-Episode Data Table ───────────────────────────────────────────
    episode_csv = RESULTS / "episode_comparison.csv"
    if episode_csv.exists():
        with st.expander("📋 Per-Episode Raw Data"):
            ep_df = pd.read_csv(episode_csv)
            st.markdown("Dig into the actual numbers behind the graphs. "
                        "Each row is one simulated 16-day batch.")
            st.dataframe(
                ep_df.style.highlight_max(subset=['final_biomass_mg'], color='#2d6a4f')
                           .highlight_min(subset=['mortality_pct'], color='#2d6a4f'),
                use_container_width=True,
                height=400
            )

    st.markdown("---")

    # ── Dynamic Insight summary ──────────────────────────────────────────
    st.markdown("### 🧠 What This Means")
    if summary_csv.exists():
        df = pd.read_csv(summary_csv).set_index("strategy")
        if "PPO Agent" in df.index and "Rule-Based" in df.index:
            ppo = df.loc["PPO Agent"]
            rule = df.loc["Rule-Based"]
            feed_saving = (rule['avg_feed_g'] - ppo['avg_feed_g']) / rule['avg_feed_g'] * 100
            biomass_ratio = ppo['avg_biomass'] / rule['avg_biomass'] * 100

            st.markdown(f"""
| Insight | Detail |
|---------|--------|
| **Feed Efficiency** | AI uses ~{feed_saving:.0f}% less feed — direct cost savings for farmers |
| **Biomass Output** | AI produces {biomass_ratio:.0f}% of the expert heuristic's average biomass ({ppo['avg_biomass']:.0f} vs {rule['avg_biomass']:.0f} mg) |
| **Peak Performance** | AI's best episodes ({ppo['max_biomass']:.0f}mg) match expert heuristic ({rule['max_biomass']:.0f}mg) |
| **Consistency** | AI std dev: {ppo['std_biomass']:.0f} vs Expert: {rule['std_biomass']:.0f} — {"AI is more consistent" if ppo['std_biomass'] < rule['std_biomass'] else "Expert is more consistent"} |
| **Mortality** | AI: {ppo['avg_mortality']:.0f}% vs Expert: {rule['avg_mortality']:.0f}% — {"AI has lower mortality ✅" if ppo['avg_mortality'] < rule['avg_mortality'] else "gap closing with more training"} |
| **vs Real Farmers** | Our heuristic is the *ideal* scientist-farmer with sensors; real farmers likely do less |
            """)
    else:
        st.markdown("""
| Insight | Detail |
|---------|--------|
| **Feed Efficiency** | AI uses significantly less feed — direct cost savings for farmers |
| **Peak Performance** | AI's best episodes match expert heuristic |
| **Consistency** | More training improves reliability |
| **vs Real Farmers** | Our heuristic is the *ideal* scientist-farmer with sensors; real farmers likely do less |
        """)

    # ── Scientific References ────────────────────────────────────────────
    with st.expander("📚 Scientific References"):
        st.markdown("""
1. **Dortmans, B., Diener, S., Verstappen, B., Zurbrügg, C. (2017).** *Black Soldier Fly Biowaste Processing - A Step-by-Step Guide.* Eawag: Swiss Federal Institute of Aquatic Science and Technology.
   - Source of moisture thresholds (60–80%), temperature ranges, and feeding guidelines used in our heuristic rules.

2. **Tomberlin, J. K., Adler, P. H., & Myers, H. M. (2009).** Development of the black soldier fly (Diptera: Stratiomyidae) in relation to temperature. *Environmental Entomology*, 38(3), 930–934.
   - Source of thermal tolerance curves used in our growth and mortality models.

3. **Oonincx, D. G., van Broekhoven, S., van Huis, A., & van Loon, J. J. (2015).** Feed conversion, survival and development, and composition of four insect species on diets composed of food by-products. *PLoS One*, 10(12), e0144601.
   - Source of age-phase feeding rates (neonates → exponential → pre-pupa) used in our heuristic.

4. **Lalander, C., Diener, S., Magri, M. E., Zurbrügg, C., Lindström, A., & Vinnerås, B. (2019).** Faecal sludge and solid waste mixed for optimization of black soldier fly larvae treatment. *Science of The Total Environment*, 650, 151–157.
   - Source of optimal C:N ratio range (14–18:1) used in feed composition rules.
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
        "- **RL Model** — neural network trained on 52,000+ batches. More feed-efficient, "
        "higher biomass, and lower mortality than the expert baseline."
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

    # ── Model Info Cards ──────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("ℹ️ Active Policy Details")

    if "PPO" in current or "RL" in current:
        st.markdown("""
| Property | Value |
|----------|-------|
| **Training Steps** | ~5,000,000 |
| **Network Architecture** | 128 × 128 MLP (actor-critic) |
| **Training Episodes** | ~52,000 simulated batches |
| **Algorithm** | Proximal Policy Optimization (PPO) |
| **Parameters** | 36,489 trainable weights |
        """)
    else:
        st.markdown("""
**4 expert rules derived from published BSF biology research:**

| Rule | Description |
|------|-------------|
| 🎯 **C:N Targeting** | Adjusts feed composition to maintain optimal 14–18:1 carbon-to-nitrogen ratio |
| 🐛 **Age-Based Feeding** | Scales feed quantity based on larval growth phase (neonate → exponential → pre-pupa) |
| 💧 **Moisture Control** | Maintains 60–80% moisture via water addition or ventilation |
| 🌀 **Aeration** | Manages oxygen flow to prevent anaerobic conditions and overheating |
        """)

    # ── Policy Comparison Table ───────────────────────────────────────────
    bench_df = _load_results_csv()
    if bench_df is not None and "PPO Agent" in bench_df.index and "Rule-Based" in bench_df.index:
        st.markdown("---")
        st.subheader("📊 Policy Comparison")

        ppo = bench_df.loc["PPO Agent"]
        rule = bench_df.loc["Rule-Based"]
        feed_saving = (rule['avg_feed_g'] - ppo['avg_feed_g']) / rule['avg_feed_g'] * 100

        comparison_data = {
            "Metric": ["Avg Biomass", "Feed Used", "Mortality", "Consistency (Std)", "Feed Efficiency"],
            "Heuristic": [
                f"{rule['avg_biomass']:.0f} mg",
                f"{rule['avg_feed_g']:.0f} g",
                f"{rule['avg_mortality']:.0f}%",
                f"{rule['std_biomass']:.0f}",
                "Baseline"
            ],
            "PPO Agent": [
                f"{ppo['avg_biomass']:.0f} mg",
                f"{ppo['avg_feed_g']:.0f} g",
                f"{ppo['avg_mortality']:.0f}%",
                f"{ppo['std_biomass']:.0f}",
                f"{feed_saving:.0f}% less feed"
            ]
        }
        st.table(pd.DataFrame(comparison_data).set_index("Metric"))

    with st.expander("🔧 Advanced: load a specific checkpoint"):
        custom_path = st.text_input("Model path (without .zip)", "outputs/models/best_model")
        if st.button("Load from path"):
            _load_ppo_model(custom_path)

    st.markdown("---")
    st.subheader("🗑️ End Current Batch")
    if st.button("🗑️ End Batch", type="secondary"):
        st.session_state.batch_started  = False
        st.session_state.batch_info      = None
        st.session_state.history         = []
        st.session_state.current_day     = 0
        st.session_state.checkin_phase   = 0
        st.session_state.pending_rec     = None
        st.session_state.pending_action  = None
        st.session_state.pending_weather = None
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

    # Active batch summary + day timeline in sidebar
    if st.session_state.batch_info:
        st.sidebar.markdown("---")
        b   = st.session_state.batch_info
        day = st.session_state.current_day
        stage_name, stage_desc, prog = _get_stage_info(day)

        st.sidebar.markdown(f"### 📅 Day **{day}** / 16")
        st.sidebar.progress(prog)
        st.sidebar.markdown(f"`{stage_name}`")
        st.sidebar.caption(stage_desc)
        st.sidebar.markdown("---")
        st.sidebar.markdown(f"👥 Population: **{b.estimated_count:,}**")
        st.sidebar.markdown(f"🌿 Feed used:  **{b.total_feed_kg:.2f} kg**")

        # Mini day timeline — dots for completed days
        history_days = {h['day'] for h in st.session_state.history}
        dots = ""
        for d in range(16):
            if d < day and d in history_days:
                dots += "🟢"
            elif d == day:
                dots += "🔵"
            else:
                dots += "⚪"
            if (d + 1) % 8 == 0:
                dots += "\n"
        st.sidebar.markdown(f"**Batch Timeline:**\n{dots}")
        st.sidebar.caption("🟢 done  🔵 today  ⚪ upcoming")

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
