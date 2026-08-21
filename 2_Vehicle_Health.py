import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from utils import (
    inject_base_css, kpi_card, status_pill, note, warn,
    load_vehicle_health, load_vehicles, load_json,
    fleet_plot_layout, COLORS, STATUS_COLOR,
)

st.set_page_config(page_title="Vehicle Health - VexarDrive", layout="wide")
inject_base_css()

health_df = load_vehicle_health()
vehicles_df = load_vehicles()
summary = load_json("vehicle_health_summary.json")

st.markdown("# Vehicle Health")
st.markdown(
    '<div class="subtitle">Which vehicles show unusual sensor patterns?</div>',
    unsafe_allow_html=True,
)

status_counts = health_df["vehicle_health_status"].value_counts()
n_total = len(health_df)
n_normal = int(status_counts.get("Normal", 0))
n_watch = int(status_counts.get("Watch", 0))
n_investigate = int(status_counts.get("Investigate", 0))

c1, c2, c3, c4 = st.columns(4)
with c1:
    kpi_card("Total vehicles", f"{n_total}", "assessed this week")
with c2:
    kpi_card("Normal", f"{n_normal}", "no core metric elevated")
with c3:
    kpi_card("Watch", f"{n_watch}", "one metric at/above fleet p75")
with c4:
    kpi_card("Investigate", f"{n_investigate}", "one metric at/above fleet p90")

note(
    "This is a rule-based classification, not a blended score. A vehicle lands in 'Investigate' if any one "
    "of four sensor/data-quality metrics is at or above the fleet's 90th percentile for that metric; "
    "'Watch' if any metric is at or above the 75th percentile but none reach the 90th. Every status is "
    "traceable to the exact metric that triggered it."
)

st.markdown("---")

# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------
st.markdown("### Which vehicles would I check first?")

status_order = {"Investigate": 0, "Watch": 1, "Normal": 2}
ranked = health_df.copy()
ranked["_order"] = ranked["vehicle_health_status"].map(status_order)
ranked = ranked.sort_values(["_order", "speed_jump_rate_per_1000min"], ascending=[True, False]).reset_index(drop=True)

show = ranked[[
    "Vehicle_ID", "vehicle_health_status", "status_trigger_reasons",
    "gps_teleport_count", "speed_jump_rate_per_1000min",
    "distance_vs_gps_trip_pct", "distance_vs_speed_integral_trip_pct",
]].copy()
show["vehicle_health_status"] = show["vehicle_health_status"].apply(status_pill)
show.columns = [
    "Vehicle", "Status", "Why", "GPS teleports", "Speed-jump rate /1000min",
    "Distance vs. GPS flag %", "Distance vs. speed-integral flag %",
]
st.write(show.to_html(escape=False, index=False), unsafe_allow_html=True)

st.markdown("---")

# ---------------------------------------------------------------------------
# Vehicle selector
# ---------------------------------------------------------------------------
st.markdown("### Investigate one vehicle")
vehicle_ids = ranked["Vehicle_ID"].tolist()
selected = st.selectbox("Vehicle_ID", vehicle_ids, index=0)

row = health_df[health_df["Vehicle_ID"] == selected].iloc[0]
vinfo = vehicles_df[vehicles_df["Vehicle_ID"] == selected].iloc[0]

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-label">Health status</div>'
        f'<div style="margin-top:4px;">{status_pill(row["vehicle_health_status"])}</div>'
        f'<div class="kpi-sub">{vinfo["Make"]} {vinfo["Model"]}, {int(vinfo["Manufacture_Year"])}</div></div>',
        unsafe_allow_html=True,
    )
with c2:
    kpi_card("Trips this week", f"{int(row['total_trips'])}", f"{int(row['telemetry_row_count'])} telemetry rows")
with c3:
    kpi_card("Speed-jump rate", f"{row['speed_jump_rate_per_1000min']:.2f}", "flagged min. per 1,000 telemetry min.")
with c4:
    kpi_card("GPS teleport events", f"{int(row['gps_teleport_count'])}", "abrupt GPS position jumps")

c5, c6, c7 = st.columns(3)
with c5:
    kpi_card("Distance vs. GPS mismatch", f"{row['distance_vs_gps_trip_pct']:.1f}%", "of this vehicle's trips")
with c6:
    kpi_card("Distance vs. speed-integral mismatch", f"{row['distance_vs_speed_integral_trip_pct']:.1f}%", "of this vehicle's trips")
with c7:
    kpi_card("Days since last service", f"{int(row['days_since_last_service'])}", f"as of {summary['context_only_master_data_fields']['days_since_last_service_reference_date']}")

st.markdown(f"**Status trigger reason(s):** {row['status_trigger_reasons']}")

# ---------------------------------------------------------------------------
# Comparison chart
# ---------------------------------------------------------------------------
st.markdown("### What looks different about this vehicle?")

metrics = [
    ("speed_jump_rate_per_1000min", "Speed-jump rate /1000min"),
    ("distance_vs_gps_trip_pct", "Distance vs. GPS mismatch %"),
    ("distance_vs_speed_integral_trip_pct", "Distance vs. speed-integral mismatch %"),
]
p75 = {m: health_df[m].quantile(0.75) for m, _ in metrics}
p90 = {m: health_df[m].quantile(0.90) for m, _ in metrics}

fig = go.Figure()
labels = [lbl for _, lbl in metrics]
fig.add_trace(go.Bar(name=selected, x=labels, y=[row[m] for m, _ in metrics], marker_color=STATUS_COLOR[row["vehicle_health_status"]]))
fig.add_trace(go.Scatter(name="Fleet p75 (Watch line)", x=labels, y=[p75[m] for m, _ in metrics], mode="markers",
                          marker=dict(symbol="line-ew", size=26, color=COLORS["watch"], line=dict(width=3, color=COLORS["watch"]))))
fig.add_trace(go.Scatter(name="Fleet p90 (Investigate line)", x=labels, y=[p90[m] for m, _ in metrics], mode="markers",
                          marker=dict(symbol="line-ew", size=26, color=COLORS["investigate"], line=dict(width=3, color=COLORS["investigate"]))))
fig.update_layout(
    title=f"{selected}'s core metrics against the fleet's Watch/Investigate cut-points",
    yaxis_title="Metric value",
)
fleet_plot_layout(fig, height=380)
st.plotly_chart(fig, width="stretch")

# ---------------------------------------------------------------------------
# Why flagged
# ---------------------------------------------------------------------------
st.markdown("### Why did this vehicle catch my attention?")

if row["vehicle_health_status"] == "Normal":
    st.write(
        f"{selected} shows no core metric elevated above the fleet's 75th percentile this week. "
        "That doesn't rule out a developing issue — it means nothing in this week's sensor data stood out "
        "relative to the rest of the fleet."
    )
else:
    st.write(
        f"{selected} shows an unusual sensor signature that may warrant inspection. "
        f"Specifically: {row['status_trigger_reasons']} "
        "This reflects the sensor data recorded this week, not a confirmed mechanical diagnosis — "
        "the underlying cause could be a sensor/GPS artifact, a data-logging quirk, or an actual "
        "vehicle issue, and telemetry alone can't distinguish between those."
    )

with st.expander("Technical details — how each core metric is calculated"):
    for metric, info in summary["core_metrics_used_for_status"].items():
        st.markdown(f"**`{metric}`**")
        st.markdown(f"- Formula: `{info['formula']}`")
        st.markdown(f"- Source: {info['source']}")
        if "watch_threshold" in info:
            st.markdown(f"- Watch at ≥ {info['watch_threshold']}, Investigate at ≥ {info['investigate_threshold']}")
        elif "rule" in info:
            st.markdown(f"- Rule: {info['rule']}")
    st.markdown(f"**Overall rule:** {summary['methodology']['rule']}")
    st.markdown(f"**Why not a single composite score:** {summary['methodology']['why_no_composite_score']}")

# ---------------------------------------------------------------------------
# What next
# ---------------------------------------------------------------------------
st.markdown("### What I would do next")
if row["vehicle_health_status"] == "Investigate":
    st.markdown(
        "- Review this vehicle's recent trips for repeated instances of the flagged pattern, not just this week's total.\n"
        "- If the pattern persists across weeks, schedule a physical inspection focused on GPS/telemetry hardware "
        "and the specific signal that triggered the flag.\n"
        "- Cross-check against the driver(s) who used this vehicle — a single erratic trip can look like a vehicle "
        "issue when it's actually a one-off driving event."
    )
elif row["vehicle_health_status"] == "Watch":
    st.markdown(
        "- Keep this vehicle on the watch list and re-check after another week of data before acting.\n"
        "- No inspection is indicated yet on a single week of borderline readings."
    )
else:
    st.markdown("- No action indicated this week. Continue routine monitoring.")

st.markdown("---")
st.markdown(
    f'<div style="font-size:0.78rem; color:{COLORS["text_muted"]};">'
    "Source: processed/analytical/vehicle_health.csv (Step 6, read-only). "
    "Statuses and metrics shown exactly as calculated in Step 6 — nothing on this page recomputes them."
    "</div>",
    unsafe_allow_html=True,
)
