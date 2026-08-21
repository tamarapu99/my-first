import streamlit as st
import plotly.graph_objects as go

from utils import (
    inject_base_css, kpi_card, status_pill, note, load_driver_scores,
    load_vehicle_health, load_drivers, load_vehicles, load_trips,
    fleet_plot_layout, COLORS,
)

st.set_page_config(
    page_title="VexarDrive Fleet Analytics",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_base_css()

drivers_scores = load_driver_scores()
vehicle_health = load_vehicle_health()
drivers = load_drivers()
vehicles = load_vehicles()
trips = load_trips()

n_drivers = len(drivers)
n_vehicles = len(vehicles)
n_trips = len(trips)
scores = drivers_scores["driver_safety_score"]
avg_score = scores.mean()
q1 = scores.quantile(0.25)
low_scoring = drivers_scores[drivers_scores["driver_safety_score"] <= q1].sort_values("driver_safety_score")
n_low_scoring = len(low_scoring)
status_counts = vehicle_health["vehicle_health_status"].value_counts()
n_investigate = int(status_counts.get("Investigate", 0))
n_watch = int(status_counts.get("Watch", 0))
n_normal = int(status_counts.get("Normal", 0))
avg_confidence = drivers_scores["data_confidence_pct"].mean()
low_conf_drivers = drivers_scores[drivers_scores["data_confidence_pct"] < 30]
worst_driver = drivers_scores.sort_values("driver_safety_score").iloc[0]

st.markdown("# VexarDrive Fleet Analytics")
st.markdown(
    '<div class="subtitle">Understanding driver behaviour and vehicle health from one week of trip, GPS and mobile-sensor data.</div>',
    unsafe_allow_html=True,
)

st.markdown(
    "This dashboard is the final analysis layer of the VexarDrive assignment. "
    "The driver scores and vehicle statuses were calculated and validated before this dashboard was built; "
    "this app reads those outputs rather than recalculating them."
)

with st.sidebar:
    st.markdown("### Start here")
    st.markdown(
        "**Overview** gives the fleet picture. **Driver Behaviour** and **Vehicle Health** are the investigation pages. "
        "**Trip & Sensor Explorer** lets you trace a finding back to individual trips. "
        "**Data Quality** shows where the data needs caution, and **Methodology** explains the decisions behind the numbers."
    )
    st.markdown("---")
    st.markdown("### Fleet snapshot")
    st.markdown(
        f"{n_drivers} drivers  ·  {n_vehicles} vehicles  ·  {n_trips} trips  ·  1 week of data"
    )

st.markdown("## The fleet at a glance")
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    kpi_card("Drivers", f"{n_drivers}", "all have a Step 5 score")
with c2:
    kpi_card("Vehicles", f"{n_vehicles}", "assessed by Step 6")
with c3:
    kpi_card("Trips", f"{n_trips}", "one-week window")
with c4:
    kpi_card("Average safety score", f"{avg_score:.1f}", "0–100 · higher is safer")
with c5:
    kpi_card("Average data confidence", f"{avg_confidence:.0f}%", "clean share of usable trips")

st.markdown("## What stands out")
findings = [
    f"**{worst_driver['Driver_ID']} has the lowest safety score** at {worst_driver['driver_safety_score']:.1f}/100. "
    "That makes this driver the most useful place to start a trip-level review.",
    f"**{n_investigate} of {n_vehicles} vehicles are marked Investigate**, while {n_watch} are on Watch. "
    "These labels mean unusual sensor signatures, not confirmed mechanical failures.",
    f"**{len(low_conf_drivers)} drivers have data confidence below 30%.** Their scores are still valid outputs of the same method, "
    "but the supporting trips contain more quality-flagged data.",
    f"**Driver scores run from {scores.min():.1f} to {scores.max():.1f}.** There is enough separation to identify drivers that deserve a closer look rather than treating the fleet as one group.",
]
for finding in findings:
    st.markdown(f"- {finding}")

note(
    "The safest way to use these results is as a screening tool: find something unusual here, then open the driver, vehicle or trip detail before deciding what action to take."
)

st.markdown("## Where should I look first?")
col_a, col_b = st.columns(2)
with col_a:
    st.markdown("### Driver behaviour")
    st.markdown(
        f"The bottom quartile contains **{n_low_scoring} drivers** (score ≤ {q1:.1f}). "
        f"The first driver I would investigate is **{worst_driver['Driver_ID']}**, then compare the component breakdown rather than assuming one behaviour explains every low score."
    )
    show_low = low_scoring[["Driver_ID", "driver_safety_score", "data_confidence_pct"]].head(8).copy()
    show_low.columns = ["Driver", "Safety score", "Data confidence %"]
    st.dataframe(show_low, hide_index=True, width="stretch")

with col_b:
    st.markdown("### Vehicle health")
    st.markdown(
        f"**{n_investigate} vehicles** are marked Investigate and **{n_watch}** are on Watch. "
        "Open Vehicle Health to see the exact sensor pattern behind each status."
    )
    show_inv = vehicle_health[vehicle_health["vehicle_health_status"] != "Normal"][[
        "Vehicle_ID", "vehicle_health_status", "status_trigger_reasons"
    ]].copy()
    show_inv["vehicle_health_status"] = show_inv["vehicle_health_status"].apply(status_pill)
    show_inv.columns = ["Vehicle", "Status", "Why"]
    st.write(show_inv.head(8).to_html(escape=False, index=False), unsafe_allow_html=True)

st.markdown("## How the results are distributed")
col_c, col_d = st.columns([3, 2])
with col_c:
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=scores, nbinsx=12, marker_color=COLORS["accent"], marker_line_color="white", marker_line_width=1, opacity=0.9))
    fig.add_vline(x=avg_score, line_dash="dash", line_color=COLORS["text_muted"], annotation_text=f"fleet average {avg_score:.1f}", annotation_font_size=11)
    fig.update_layout(title="Where do the driver scores sit?", xaxis_title="Driver safety score (0–100)", yaxis_title="Drivers", bargap=0.08)
    fleet_plot_layout(fig, height=320)
    st.plotly_chart(fig, width="stretch")

with col_d:
    order = ["Normal", "Watch", "Investigate"]
    counts = [int(status_counts.get(s, 0)) for s in order]
    colors = [COLORS["normal"], COLORS["watch"], COLORS["investigate"]]
    fig2 = go.Figure(go.Bar(x=order, y=counts, marker_color=colors, text=counts, textposition="outside"))
    fig2.update_layout(title="Vehicle health status", yaxis_title="Vehicles", showlegend=False)
    fleet_plot_layout(fig2, height=320)
    st.plotly_chart(fig2, width="stretch")

st.markdown("## How I would use this analysis")
st.markdown(
    "1. **Start with the drivers at the bottom of the ranking.** Open their component breakdown to see what is actually pulling the score down.\n"
    "2. **Check data confidence before drawing a strong conclusion.** A low score with limited clean data deserves a closer trip-level review.\n"
    "3. **Open vehicles marked Investigate.** Look for the repeated sensor pattern behind the flag rather than calling it a mechanical fault immediately.\n"
    "4. **Trace interesting results back to trips and telemetry.** This is where a dashboard finding becomes an analysis rather than just a chart.\n"
    "5. **Use more historical data before making operational policy.** This dataset covers one week, so it is useful for screening and comparison, not long-term prediction."
)

st.markdown("## One important limitation")
note(
    "A safety score summarizes observed behaviour in this week's data; it is not an accident prediction. A vehicle marked Investigate has an unusual sensor signature; that is not proof of a mechanical problem. Keeping those distinctions visible is part of the analysis."
)

st.markdown("---")
st.markdown(
    f'<div style="font-size:0.78rem; color:{COLORS["text_muted"]};">'
    "Step 5 and Step 6 outputs are read-only source-of-truth files. This dashboard does not recalculate scores or statuses."
    "</div>",
    unsafe_allow_html=True,
)
