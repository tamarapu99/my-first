import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from utils import (
    inject_base_css, kpi_card, note,
    load_trips, load_telemetry, load_driver_trip_features, load_drivers, load_vehicles,
    fleet_plot_layout, COLORS,
)

st.set_page_config(page_title="Trip & Sensor Explorer - VexarDrive", layout="wide")
inject_base_css()

trips = load_trips()
features = load_driver_trip_features()
drivers = load_drivers()
vehicles = load_vehicles()

st.markdown("# Trip & Sensor Explorer")
st.markdown(
    '<div class="subtitle">When a dashboard result looks interesting, use this page to trace it back to the trip and sensor readings behind it.</div>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------
f1, f2, f3 = st.columns(3)
with f1:
    driver_choice = st.selectbox("Driver", ["All"] + sorted(trips["Driver_ID"].unique().tolist()))
with f2:
    filtered_for_vehicle = trips if driver_choice == "All" else trips[trips["Driver_ID"] == driver_choice]
    vehicle_choice = st.selectbox("Vehicle", ["All"] + sorted(filtered_for_vehicle["Vehicle_ID"].unique().tolist()))

subset = trips.copy()
if driver_choice != "All":
    subset = subset[subset["Driver_ID"] == driver_choice]
if vehicle_choice != "All":
    subset = subset[subset["Vehicle_ID"] == vehicle_choice]

with f3:
    trip_choice = st.selectbox(
        "Trip",
        subset.sort_values("Trip_Date")["Trip_ID"].tolist(),
        index=0 if len(subset) else None,
    )

if not trip_choice:
    st.info("No trips match this combination of driver and vehicle.")
    st.stop()

trip_row = trips[trips["Trip_ID"] == trip_choice].iloc[0]
feat_row = features[features["Trip_ID"] == trip_choice].iloc[0] if trip_choice in features["Trip_ID"].values else None

st.markdown("---")

# ---------------------------------------------------------------------------
# Trip summary
# ---------------------------------------------------------------------------
st.markdown(f"### Trip {trip_choice} — {trip_row['Driver_ID']} driving {trip_row['Vehicle_ID']}")

c1, c2, c3, c4 = st.columns(4)
with c1:
    kpi_card("Date", str(trip_row["Trip_Date"].date()), f"{trip_row['Start_Time']} - {trip_row['End_Time']}")
with c2:
    kpi_card("Duration", f"{trip_row['Duration_Min']:.0f} min", f"{trip_row['Distance_KM']:.1f} km")
with c3:
    kpi_card("Avg / max speed", f"{trip_row['Avg_Speed_kmph']:.0f} / {trip_row['Max_Speed_kmph']:.0f} km/h", "")
with c4:
    flags = [c for c in [
        "flag_overlap_driver", "flag_overlap_vehicle", "flag_non_primary_vehicle",
        "flag_distance_vs_gps", "flag_distance_vs_speed_integral",
        "flag_has_gps_teleport", "flag_has_speed_jump",
    ] if trip_row[c] == 1]
    kpi_card("Quality flags", f"{len(flags)}", ", ".join(f.replace("flag_", "") for f in flags) if flags else "none")

if feat_row is not None:
    c5, c6, c7 = st.columns(3)
    with c5:
        kpi_card("Harsh accel events", f"{int(feat_row['harsh_accel_events'])}", "this trip")
    with c6:
        kpi_card("Harsh brake events", f"{int(feat_row['harsh_brake_events'])}", "this trip")
    with c7:
        kpi_card("Speed delta (mean)", f"{feat_row['speed_delta_mean_kmph']:.1f} km/h", "minute-to-minute swing")

# ---------------------------------------------------------------------------
# Telemetry time series
# ---------------------------------------------------------------------------
st.markdown("### What happened during this trip?")

telemetry = load_telemetry()
trip_telemetry = telemetry[telemetry["Trip_ID"] == trip_choice].sort_values("Timestamp")

if len(trip_telemetry) == 0:
    st.info("No telemetry rows recorded for this trip.")
else:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=trip_telemetry["Timestamp"], y=trip_telemetry["Speed_kmph"],
        mode="lines+markers", name="Speed (km/h)", line=dict(color=COLORS["accent"], width=2),
        marker=dict(size=4),
    ))
    jump_pts = trip_telemetry[trip_telemetry["flag_speed_jump"] == 1]
    if len(jump_pts):
        fig.add_trace(go.Scatter(
            x=jump_pts["Timestamp"], y=jump_pts["Speed_kmph"], mode="markers",
            name="Flagged speed jump", marker=dict(color=COLORS["investigate"], size=10, symbol="x"),
        ))
    fig.update_layout(
        title="How did speed change minute-to-minute on this trip?",
        yaxis_title="Speed (km/h)", xaxis_title="Time",
    )
    fleet_plot_layout(fig, height=340)
    st.plotly_chart(fig, width="stretch")

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=trip_telemetry["Timestamp"], y=trip_telemetry["speed_delta_kmph"],
        name="Speed change from prior minute", marker_color=COLORS["accent"],
    ))
    fig2.add_hline(y=25.4, line_dash="dash", line_color=COLORS["investigate"],
                    annotation_text="harsh-event threshold (25.4 km/h)", annotation_font_size=11)
    fig2.add_hline(y=-25.4, line_dash="dash", line_color=COLORS["investigate"])
    fig2.update_layout(
        title="Where did acceleration or braking cross the harsh-event threshold?",
        yaxis_title="Speed change (km/h)", xaxis_title="Time",
    )
    fleet_plot_layout(fig2, height=300)
    st.plotly_chart(fig2, width="stretch")

# ---------------------------------------------------------------------------
# Driver-level comparison
# ---------------------------------------------------------------------------
st.markdown("### How does this driver's behaviour compare with the fleet?")

driver_features = features[features["Driver_ID"] == trip_row["Driver_ID"]]
fleet_avg_events = features["harsh_accel_events"].mean() + features["harsh_brake_events"].mean()
driver_avg_events = driver_features["harsh_accel_events"].mean() + driver_features["harsh_brake_events"].mean()

fig3 = go.Figure()
fig3.add_trace(go.Box(y=features["speed_delta_mean_kmph"], name="Fleet (all trips)", marker_color=COLORS["border"]))
fig3.add_trace(go.Box(y=driver_features["speed_delta_mean_kmph"], name=f"{trip_row['Driver_ID']} (all trips)", marker_color=COLORS["accent"]))
fig3.update_layout(
    title=f"How spread out is {trip_row['Driver_ID']}'s speed variability, compared with every trip in the fleet?",
    yaxis_title="Mean speed delta per trip (km/h)",
)
fleet_plot_layout(fig3, height=340)
st.plotly_chart(fig3, width="stretch")

note(
    f"{trip_row['Driver_ID']} has {len(driver_features)} recorded trips this week, averaging "
    f"{driver_avg_events:.1f} combined harsh accel/brake events per trip, versus a fleet average of "
    f"{fleet_avg_events:.1f}."
)

st.markdown("---")
st.markdown(
    f'<div style="font-size:0.78rem; color:{COLORS["text_muted"]};">'
    "Source: processed/analytical/trips.csv, telemetry.csv, and driver_trip_features.csv (Step 3-4, read-only)."
    "</div>",
    unsafe_allow_html=True,
)
