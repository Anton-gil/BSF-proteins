#!/usr/bin/env python3
"""
Generate comparison graphs from real evaluation data.
Reads CSVs produced by run_real_evaluation.py.

Outputs saved to results/ folder as PNG files.
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

# ── Setup ──────────────────────────────────────────────────────────────────
RESULTS_DIR = Path(__file__).parent
SUMMARY_CSV = RESULTS_DIR / "summary_comparison.csv"
EPISODE_CSV = RESULTS_DIR / "episode_comparison.csv"

# Color palette
COLORS = {
    "PPO Agent":  "#00b894",
    "Rule-Based": "#0984e3",
    "Random":     "#fdcb6e",
    "Do-Nothing": "#d63031",
}
STRATEGY_ORDER = ["PPO Agent", "Rule-Based", "Random", "Do-Nothing"]

# Global dark style
plt.rcParams.update({
    "font.family":      "sans-serif",
    "font.sans-serif":  ["Inter", "Segoe UI", "Arial"],
    "font.size":        11,
    "axes.facecolor":   "#0d1b2a",
    "figure.facecolor": "#0d1b2a",
    "text.color":       "#e0e1dd",
    "axes.labelcolor":  "#e0e1dd",
    "xtick.color":      "#778da9",
    "ytick.color":      "#778da9",
    "axes.edgecolor":   "#415a77",
    "grid.color":       "#1b263b",
    "grid.alpha":       0.6,
    "legend.facecolor": "#1b263b",
    "legend.edgecolor": "#415a77",
    "legend.fontsize":  10,
})


def load_data():
    summary = pd.read_csv(SUMMARY_CSV)
    episodes = pd.read_csv(EPISODE_CSV)

    # Filter to only keep strategies in our order (PPO might be missing)
    available = [s for s in STRATEGY_ORDER if s in summary['strategy'].values]
    summary["strategy"] = pd.Categorical(summary["strategy"], categories=available, ordered=True)
    summary = summary.sort_values("strategy").dropna(subset=["strategy"])
    episodes["strategy"] = pd.Categorical(episodes["strategy"], categories=available, ordered=True)
    episodes = episodes.dropna(subset=["strategy"])
    return summary, episodes, available


# ── Graph 1: Summary Bar Chart ────────────────────────────────────────────

def plot_summary_bars(summary, strategies):
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle("Strategy Comparison -- Aggregate Metrics (20 Episodes)",
                 fontsize=18, fontweight="bold", color="#e0e1dd", y=0.98)

    metrics = [
        ("avg_biomass",   "Avg Biomass (mg)",  "Higher is better", True),
        ("max_biomass",   "Max Biomass (mg)",  "Higher is better", True),
        ("avg_reward",    "Avg Reward",        "Higher is better", True),
        ("avg_feed_g",    "Avg Feed Used (g)", "Lower is better",  False),
        ("avg_mortality", "Avg Mortality (%)", "Lower is better",  False),
        ("std_biomass",   "Biomass Std Dev",   "Lower = more consistent", False),
    ]

    for ax, (col, title, subtitle, higher_better) in zip(axes.flat, metrics):
        if col not in summary.columns:
            ax.set_visible(False)
            continue
        values = summary[col].values
        strats = summary["strategy"].values
        colors = [COLORS.get(s, "#636e72") for s in strats]

        bars = ax.bar(strats, values, color=colors, edgecolor="#415a77",
                      linewidth=0.8, width=0.6, zorder=3)

        # Highlight best
        if len(values) > 0:
            best_idx = np.argmax(values) if higher_better else np.argmin(values)
            bars[best_idx].set_edgecolor("#ffeaa7")
            bars[best_idx].set_linewidth(2.5)

        for bar, val in zip(bars, values):
            y_pos = bar.get_height() + (abs(max(values) - min(values)) * 0.03)
            ax.text(bar.get_x() + bar.get_width() / 2, y_pos,
                    f"{val:.1f}", ha="center", va="bottom",
                    fontsize=10, fontweight="600", color="#dfe6e9")

        ax.set_title(title, fontsize=13, fontweight="600", pad=10, color="#e0e1dd")
        ax.tick_params(axis="x", rotation=15)
        ax.grid(axis="y", linestyle="--", alpha=0.3)
        ax.text(0.5, -0.18, subtitle, transform=ax.transAxes,
                ha="center", fontsize=9, color="#636e72", style="italic")

    plt.tight_layout(rect=[0, 0.02, 1, 0.94])
    out = RESULTS_DIR / "01_summary_comparison.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] {out.name}")


# ── Graph 2: Box Plots ────────────────────────────────────────────────────

def plot_boxplots(episodes, strategies):
    fig, axes = plt.subplots(1, 4, figsize=(20, 6))
    fig.suptitle("Per-Episode Distribution -- All Strategies",
                 fontsize=18, fontweight="bold", color="#e0e1dd", y=1.02)

    cols = [
        ("final_biomass_mg", "Final Biomass (mg)"),
        ("total_reward",     "Total Reward"),
        ("total_feed_g",     "Total Feed (g)"),
        ("mortality_pct",    "Mortality (%)"),
    ]

    for ax, (col, title) in zip(axes, cols):
        if col not in episodes.columns:
            ax.set_visible(False)
            continue
        data_groups = [episodes[episodes["strategy"] == s][col].dropna().values
                       for s in strategies]

        bp = ax.boxplot(data_groups, tick_labels=strategies, patch_artist=True,
                        widths=0.55, showmeans=True, meanprops=dict(
                            marker="D", markerfacecolor="#ffeaa7", markersize=6
                        ))

        for patch, strat in zip(bp["boxes"], strategies):
            patch.set_facecolor(COLORS.get(strat, "#636e72"))
            patch.set_alpha(0.75)
            patch.set_edgecolor("#e0e1dd")
        for element in ["whiskers", "caps"]:
            for line in bp[element]:
                line.set_color("#778da9")
        for line in bp["medians"]:
            line.set_color("#ffeaa7")
            line.set_linewidth(2)

        ax.set_title(title, fontsize=13, fontweight="600", color="#e0e1dd")
        ax.tick_params(axis="x", rotation=15)
        ax.grid(axis="y", linestyle="--", alpha=0.3)

    plt.tight_layout()
    out = RESULTS_DIR / "02_boxplot_distributions.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] {out.name}")


# ── Graph 3: Episode-by-Episode Lines ─────────────────────────────────────

def plot_episode_lines(episodes, strategies):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
    fig.suptitle("Episode-by-Episode Performance",
                 fontsize=18, fontweight="bold", color="#e0e1dd", y=0.98)

    for strat in strategies:
        df = episodes[episodes["strategy"] == strat].sort_values("episode")
        ax1.plot(df["episode"], df["final_biomass_mg"], marker="o", markersize=5,
                 color=COLORS.get(strat, "#636e72"), label=strat, linewidth=2, alpha=0.85)
        ax2.plot(df["episode"], df["total_reward"], marker="s", markersize=5,
                 color=COLORS.get(strat, "#636e72"), label=strat, linewidth=2, alpha=0.85)

    ax1.set_ylabel("Final Biomass (mg)", fontsize=12)
    ax1.legend(loc="upper right")
    ax1.grid(linestyle="--", alpha=0.3)

    ax2.set_ylabel("Total Reward", fontsize=12)
    ax2.set_xlabel("Episode", fontsize=12)
    ax2.legend(loc="upper right")
    ax2.grid(linestyle="--", alpha=0.3)
    ax2.axhline(y=0, color="#636e72", linewidth=0.5)

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    out = RESULTS_DIR / "03_episode_performance.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] {out.name}")


# ── Graph 4: Radar Chart ─────────────────────────────────────────────────

def plot_radar(summary, strategies):
    metrics = ["avg_biomass", "max_biomass", "avg_reward"]
    inv_metrics = ["avg_feed_g", "avg_mortality", "std_biomass"]
    labels = ["Avg Biomass", "Max Biomass", "Avg Reward",
              "Low Feed", "Low Mortality", "Consistency"]

    # Only include metrics that exist
    all_cols = metrics + inv_metrics
    available_cols = [c for c in all_cols if c in summary.columns]
    if len(available_cols) < 4:
        print("  [SKIP] Not enough metrics for radar chart")
        return

    norm_data = {}
    for strat in strategies:
        row = summary[summary["strategy"] == strat].iloc[0]
        vals = []
        for col in metrics:
            if col in summary.columns:
                v = row[col]
                lo, hi = summary[col].min(), summary[col].max()
                vals.append((v - lo) / (hi - lo + 1e-9))
        for col in inv_metrics:
            if col in summary.columns:
                v = row[col]
                lo, hi = summary[col].min(), summary[col].max()
                vals.append(1.0 - (v - lo) / (hi - lo + 1e-9))
        norm_data[strat] = vals

    n_labels = len(norm_data[strategies[0]])
    actual_labels = labels[:n_labels]
    angles = np.linspace(0, 2 * np.pi, n_labels, endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(9, 9), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor("#0d1b2a")
    ax.set_facecolor("#0d1b2a")

    for strat in strategies:
        vals = norm_data[strat] + norm_data[strat][:1]
        ax.fill(angles, vals, alpha=0.15, color=COLORS.get(strat, "#636e72"))
        ax.plot(angles, vals, linewidth=2.5, label=strat, color=COLORS.get(strat, "#636e72"))

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(actual_labels, fontsize=11, color="#e0e1dd")
    ax.set_yticklabels([])
    ax.spines["polar"].set_color("#415a77")
    ax.grid(color="#1b263b", linewidth=0.8)
    ax.set_title("Multi-Metric Radar Comparison",
                 fontsize=16, fontweight="bold", color="#e0e1dd", pad=30)
    ax.legend(loc="lower right", bbox_to_anchor=(1.3, -0.05))

    out = RESULTS_DIR / "04_radar_comparison.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] {out.name}")


# ── Graph 5: PPO Improvement Over Baselines ──────────────────────────────

def plot_improvement(summary, strategies):
    """Side-by-side bars: raw metric values for PPO vs Rule-Based vs Random."""
    if "PPO Agent" not in strategies:
        print("  [SKIP] No PPO Agent data for improvement chart")
        return

    # Show PPO vs the active baselines (exclude Do-Nothing — too far off)
    show = [s for s in strategies if s != "Do-Nothing"]

    fig, axes = plt.subplots(1, 4, figsize=(20, 6))
    fig.suptitle("PPO Agent vs Active Baselines -- Head-to-Head",
                 fontsize=18, fontweight="bold", color="#e0e1dd", y=1.02)

    metric_defs = [
        ("avg_biomass",   "Avg Biomass (mg)",  True),
        ("avg_reward",    "Avg Reward",        True),
        ("avg_feed_g",    "Avg Feed Used (g)", False),
        ("avg_mortality", "Avg Mortality (%)", False),
    ]
    metrics = [(c, l, h) for c, l, h in metric_defs if c in summary.columns]

    for ax, (col, title, higher_better) in zip(axes, metrics):
        vals = []
        colors = []
        labels = []
        for s in show:
            row = summary[summary["strategy"] == s]
            if len(row) == 0:
                continue
            vals.append(row.iloc[0][col])
            colors.append(COLORS.get(s, "#636e72"))
            labels.append(s)

        bars = ax.bar(labels, vals, color=colors, edgecolor="#415a77",
                      linewidth=0.8, width=0.55, zorder=3)

        # Highlight best
        if len(vals) > 0:
            best_idx = np.argmax(vals) if higher_better else np.argmin(vals)
            bars[best_idx].set_edgecolor("#ffeaa7")
            bars[best_idx].set_linewidth(2.5)

        for bar, val in zip(bars, vals):
            sign = 1 if val >= 0 else -1
            y_pos = val + sign * (abs(max(vals) - min(vals)) * 0.04 + 0.5)
            ax.text(bar.get_x() + bar.get_width() / 2, y_pos,
                    f"{val:.1f}", ha="center",
                    va="bottom" if val >= 0 else "top",
                    fontsize=10, fontweight="600", color="#dfe6e9")

        ax.set_title(title, fontsize=13, fontweight="600", color="#e0e1dd")
        ax.tick_params(axis="x", rotation=15)
        ax.grid(axis="y", linestyle="--", alpha=0.3)

        subtitle = "Higher is better" if higher_better else "Lower is better"
        ax.text(0.5, -0.18, subtitle, transform=ax.transAxes,
                ha="center", fontsize=9, color="#636e72", style="italic")

    plt.tight_layout()
    out = RESULTS_DIR / "05_ppo_improvement.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] {out.name}")


# ── Graph 6: Scatter -- Biomass vs Feed ───────────────────────────────────

def plot_scatter_tradeoff(episodes, strategies):
    fig, ax = plt.subplots(figsize=(10, 8))
    fig.suptitle("Efficiency Trade-off: Biomass vs Feed Used",
                 fontsize=16, fontweight="bold", color="#e0e1dd", y=0.98)

    for strat in strategies:
        df = episodes[episodes["strategy"] == strat]
        ax.scatter(df["total_feed_g"], df["final_biomass_mg"],
                   color=COLORS.get(strat, "#636e72"), label=strat, s=80,
                   alpha=0.75, edgecolors="#e0e1dd", linewidth=0.5, zorder=3)

    ax.set_xlabel("Total Feed (g)", fontsize=12)
    ax.set_ylabel("Final Biomass (mg)", fontsize=12)
    ax.legend(loc="best")
    ax.grid(linestyle="--", alpha=0.3)

    plt.tight_layout(rect=[0, 0, 1, 0.94])
    out = RESULTS_DIR / "06_biomass_vs_feed.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] {out.name}")


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    print("\n[*] Generating comparison graphs from real data...\n")

    summary, episodes, strategies = load_data()

    print(f"  Strategies found: {strategies}")
    print(f"  Total episodes:   {len(episodes)}\n")

    plot_summary_bars(summary, strategies)
    plot_boxplots(episodes, strategies)
    plot_episode_lines(episodes, strategies)
    plot_radar(summary, strategies)
    plot_improvement(summary, strategies)
    plot_scatter_tradeoff(episodes, strategies)

    print(f"\n[OK] All graphs saved to: {RESULTS_DIR.resolve()}\n")


if __name__ == "__main__":
    main()
