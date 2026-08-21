import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from utils import (
    inject_base_css, kpi_card, note, warn,
    load_driver_scores, load_drivers, load_driver_trip_features,
    load_json, fleet_plot_layout, COLORS,
)

st.set_page_config(page_title="Driver Behaviour - VexarDrive", layout="wide")
inject_base_css()

scores_df = load_driver_scores()
drivers_df = load_drivers()
summary = load_json("safety_score_summary.json")

merged = scores_df.merge(drivers_df[["Driver_ID", "Driver_Name", "Primary_Vehicle_ID", "Home_Hub"]], on="Driver_ID")

st.markdown("# Driver Behaviour")
st.markdown(
    '<div class="subtitle">Which driving patterns deserve attention?</div>',
    unsafe_allow_html=True,
)

q1 = scores_df["driver_safety_score"].quantile(0.25)
q3 = scores_df["driver_safety_score"].quantile(0.75)
fleet_avg = scores_df["driver_safety_score"].mean()


def relative_tier(score):
    if score >= q3:
        return "Higher than most of the fleet"
    if score <= q1:
        return "Lower than most of the fleet"
    return "Middle of the fleet"


# ---------------------------------------------------------------------------
# Ranking table
# ---------------------------------------------------------------------------
st.markdown("### Start with the fleet ranking")
ranked = merged.sort_values("driver_safety_score", ascending=False).reset_index(drop=True)
ranked.insert(0, "Rank", ranked.index + 1)
display_cols = [
    "Rank", "Driver_ID", "Driver_Name", "driver_safety_score",
    "data_confidence_pct", "usable_trips", "excluded_overlap_trips",
]
show = ranked[display_cols].copy()
show.columns = ["Rank", "Driver", "Name", "Safety score", "Confidence %", "Usable trips", "Excluded (overlap)"]
st.dataframe(show, hide_index=True, width="stretch", height=320)

st.markdown("---")

# ---------------------------------------------------------------------------
# Driver selector
# ---------------------------------------------------------------------------
st.markdown("### Investigate one driver")
driver_ids = ranked["Driver_ID"].tolist()
selected = st.selectbox("Driver_ID", driver_ids, index=0)

row = merged[merged["Driver_ID"] == selected].iloc[0]
rank_of = int(ranked[ranked["Driver_ID"] == selected]["Rank"].iloc[0])

c1, c2, c3, c4 = st.columns(4)
with c1:
    kpi_card("Safety score", f"{row['driver_safety_score']:.1f}", f"rank {rank_of} of {len(ranked)}")
with c2:
    kpi_card("Vs. fleet average", f"{row['driver_safety_score'] - fleet_avg:+.1f}", relative_tier(row["driver_safety_score"]))
with c3:
    kpi_card("Data confidence", f"{row['data_confidence_pct']:.0f}%", "share of usable trips that were clean")
with c4:
    kpi_card("Trips this week", f"{int(row['total_trips'])}", f"{int(row['usable_trips'])} usable, {int(row['excluded_overlap_trips'])} excluded")

if row["data_confidence_pct"] < 30:
    warn(
        f"Interpret with caution — {selected} has relatively low usable-data coverage "
        f"({row['data_confidence_pct']:.0f}% of usable trips were clean, well below the fleet average of "
        f"{scores_df['data_confidence_pct'].mean():.0f}%). The score is still calculated the same way as "
        "every other driver, but it rests on fewer clean observations."
    )

# ---------------------------------------------------------------------------
# Component breakdown
# ---------------------------------------------------------------------------
st.markdown("### What is driving the score?")

components = [
    ("component_score_accel", "Harsh acceleration", "accel_rate_per10min", "events / 10 min"),
    ("component_score_brake", "Harsh braking", "brake_rate_per10min", "events / 10 min"),
    ("component_score_event_rate", "Combined harsh-event rate", "harsh_event_rate_per_10min_weighted", "events / 10 min"),
    ("component_score_speed_delta", "Speed variability", "speed_delta_mean_kmph_weighted", "km/h"),
]

fleet_component_avg = {c[0]: scores_df[c[0]].mean() for c in components}

fig = go.Figure()
labels = [c[1] for c in components]
driver_vals = [row[c[0]] for c in components]
fleet_vals = [fleet_component_avg[c[0]] for c in components]

fig.add_trace(go.Bar(name=selected, x=labels, y=driver_vals, marker_color=COLORS["accent"]))
fig.add_trace(go.Bar(name="Fleet average", x=labels, y=fleet_vals, marker_color=COLORS["border"]))
fig.update_layout(
    title=f"{selected}'s component scores vs. the fleet average (0-100, higher = safer)",
    barmode="group",
    yaxis_title="Component score (0-100)",
)
fleet_plot_layout(fig, height=360)
st.plotly_chart(fig, width="stretch")

raw_table = pd.DataFrame(
    {
        "Component": labels,
        f"{selected} raw rate": [row[c[2]] for c in components],
        "Unit": [c[3] for c in components],
        f"{selected} component score": [round(row[c[0]], 1) for c in components],
        "Fleet avg component score": [round(fleet_component_avg[c[0]], 1) for c in components],
    }
)
st.dataframe(raw_table, hide_index=True, width="stretch")

# ---------------------------------------------------------------------------
# Why is this driver's score what it is
# ---------------------------------------------------------------------------
st.markdown("### Why is this driver's score what it is?")
st.write(
    "Each driver's score is built from four behavioural components measured across their usable trips "
    "this week: harsh acceleration rate, harsh braking rate, a combined harsh-event rate, and how much "
    "their speed swings within a trip. Each component is weighted equally (25% each) and scored on a "
    "fixed 0-100 scale, so a driver's score doesn't shift just because other drivers in the fleet had a "
    "better or worse week."
)
st.write(
    "Trips are combined using exposure-weighted aggregation — a 40-minute trip counts for more than a "
    "5-minute trip — rather than a simple average across trips. Trips flagged as overlapping with another "
    "trip on the same driver are excluded entirely, and trips with a data-quality flag are counted at half "
    "weight rather than being dropped."
)

with st.expander("Technical details — exact formulas and constants"):
    st.markdown(f"**Weighting:** {summary['weighting']['scheme']}, {summary['weighting']['component_weight_each']} each.")
    st.markdown(f"**Aggregation:** {summary['aggregation_method']['type']}")
    st.markdown(f"- Trip weight: {summary['aggregation_method']['trip_weight_definition']}")
    st.markdown(f"- Usable trips: {summary['aggregation_method']['usable_trips_definition']}")
    st.markdown("**Risk ceilings (value at which a component score hits 0):**")
    for k, v in summary["score_format"]["risk_ceilings"].items():
        st.markdown(f"- `{k}`: {v}")
    st.markdown(f"**Ceiling derivation:** {summary['score_format']['risk_ceiling_derivation']}")
    st.markdown(f"**Directionality:** {summary['directionality']}")
    st.markdown(
        f"**Overlap exclusion, fleet-wide:** {summary['overlap_flagged_trip_handling']['total_overlap_trips_excluded_fleet_wide']} "
        f"trips ({summary['overlap_flagged_trip_handling']['total_overlap_exposure_minutes_excluded_fleet_wide']} minutes) "
        "excluded entirely from scoring."
    )

# ---------------------------------------------------------------------------
# What I found - per driver, generated from actual values
# ---------------------------------------------------------------------------
st.markdown("### My read of this driver")

comp_scores = {c[1]: row[c[0]] for c in components}
weakest = min(comp_scores, key=comp_scores.get)
strongest = max(comp_scores, key=comp_scores.get)
gap_to_avg = row["driver_safety_score"] - fleet_avg

if gap_to_avg <= -8:
    lead = f"{selected}'s score is meaningfully below the fleet average"
elif gap_to_avg >= 8:
    lead = f"{selected}'s score is meaningfully above the fleet average"
else:
    lead = f"{selected}'s score is close to the fleet average"

found = (
    f"{lead} ({row['driver_safety_score']:.1f} vs. {fleet_avg:.1f}). "
    f"Of the four components, **{weakest.lower()}** is the weakest of the four components "
    f"(component score {comp_scores[weakest]:.0f}/100), while **{strongest.lower()}** is the strongest "
    f"of the four (component score {comp_scores[strongest]:.0f}/100)."
)
st.write(found)

if row["excluded_overlap_trips"] > 0:
    st.write(
        f"{int(row['excluded_overlap_trips'])} of {selected}'s trips this week overlapped in time with "
        "another trip on record and were excluded from scoring entirely, rather than counted at a "
        "reduced weight."
    )

st.markdown("---")
st.markdown(
    f'<div style="font-size:0.78rem; color:{COLORS["text_muted"]};">'
    "Source: processed/analytical/driver_safety_scores.csv (Step 5, read-only). "
    "Scores and component values shown exactly as calculated in Step 5 — nothing on this page recomputes them."
    "</div>",
    unsafe_allow_html=True,
)
