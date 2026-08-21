import streamlit as st

from utils import inject_base_css, load_json

st.set_page_config(page_title="Methodology - VexarDrive", layout="wide")
inject_base_css()

safety = load_json("safety_score_summary.json")
health = load_json("vehicle_health_summary.json")
cleaning = load_json("cleaning_summary.json")

drivers_n = cleaning["records_retained"]["drivers"]
vehicles_n = cleaning["records_retained"]["vehicles"]
trips_n = cleaning["records_retained"]["trips"]
telemetry_n = cleaning["records_retained"]["telemetry"]

st.markdown("# How I got these numbers")
st.markdown(
    '<div class="subtitle">A plain-language walkthrough of where the dashboard metrics come from, '
    'what I chose to do with imperfect data, and where I would be careful when interpreting the results.</div>',
    unsafe_allow_html=True,
)

st.markdown("## Dataset")
st.write(
    f"This analysis uses one week of fleet data: **{drivers_n} drivers, {vehicles_n} vehicles, "
    f"{trips_n} trips, and {telemetry_n:,} minute-level telemetry readings**. "
    "The cleaning step did not remove rows. Instead, quality issues were kept visible as flags so they "
    "could be handled explicitly in the later analysis."
)

st.markdown("## How the data connects")
st.write(
    "I used the same cleaned trip and telemetry layer for the two final analysis questions. "
    "Trips connect the minute-level sensor readings to both the driver and the vehicle."
)

st.markdown(
    '<div class="flow-row">'
    '<div class="flow-step">Telemetry<br><small>minute-level readings</small></div>'
    '<div class="flow-arrow">→</div>'
    '<div class="flow-step">Trips<br><small>journey-level data</small></div>'
    '<div class="flow-arrow">→</div>'
    '<div class="flow-step">Drivers<br><small>Step 5 safety score</small></div>'
    '</div>'
    '<div class="flow-row">'
    '<div class="flow-step">Telemetry<br><small>minute-level readings</small></div>'
    '<div class="flow-arrow">→</div>'
    '<div class="flow-step">Trips<br><small>journey-level data</small></div>'
    '<div class="flow-arrow">→</div>'
    '<div class="flow-step">Vehicles<br><small>Step 6 health status</small></div>'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown("## Driver safety score")
st.write(
    "The Step 5 score uses four behavioural components: harsh acceleration, harsh braking, combined "
    "harsh-event rate, and mean speed delta. Higher values indicate more risk, so they lower the score. "
    "Each component contributes **25%**."
)

st.markdown(
    f'<div class="formula-box"><strong>Driver score</strong><br>'
    f'Each component → fixed 0–100 sub-score → average the 4 sub-scores equally.<br><br>'
    f'Risk ceilings: accel {safety["score_format"]["risk_ceilings"]["accel_rate_per10min"]}, '
    f'brake {safety["score_format"]["risk_ceilings"]["brake_rate_per10min"]}, '
    f'combined event rate {safety["score_format"]["risk_ceilings"]["harsh_event_rate_per_10min"]}, '
    f'speed delta {safety["score_format"]["risk_ceilings"]["speed_delta_mean_kmph"]}.</div>',
    unsafe_allow_html=True,
)

st.write(
    "I used exposure-weighted aggregation rather than treating every trip as equally important. "
    "In practice, that means a longer usable trip contributes more because it represents more driving time."
)

with st.expander("See the exact aggregation formulas"):
    st.markdown(
        f'<div class="formula-box">'
        f'Accel rate / 10 min:<br>{safety["aggregation_method"]["accel_rate_per10min_formula"]}'
        f'<br><br>Brake rate / 10 min:<br>{safety["aggregation_method"]["brake_rate_per10min_formula"]}'
        f'<br><br>Combined event rate:<br>{safety["aggregation_method"]["harsh_event_rate_per_10min_weighted_formula"]}'
        f'<br><br>Speed delta:<br>{safety["aggregation_method"]["speed_delta_mean_kmph_weighted_formula"]}'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f"**Trip weights:** {safety['aggregation_method']['trip_weight_definition']}  "
        f"**Usable trips:** {safety['aggregation_method']['usable_trips_definition']}"
    )
    st.write(
        f"Ceiling derivation: {safety['score_format']['risk_ceiling_derivation']}"
    )

st.markdown("## Data quality")
st.write(
    f"Not every trip is equally reliable. **{safety['overlap_flagged_trip_handling']['total_overlap_trips_excluded_fleet_wide']} "
    "overlap-flagged trips were excluded from Step 5 scoring because the same driver cannot genuinely be on two "
    "overlapping trips. Quality-flagged usable trips were not thrown away; they were given a weight of "
    f"**{safety['quality_flag_handling']['quality_flag_weight']}**."
)
st.write(
    "The data-confidence percentage is shown separately from the safety score. It tells me what share of a "
    "driver's usable trips were clean, so I can see when a result is supported by thinner clean data."
)

st.markdown("## Vehicle health")
st.write(
    "Step 6 is intentionally rule-based rather than a made-up composite score. A vehicle is classified from "
    "four core sensor/data-quality metrics, with each status traceable to the metric that triggered it."
)

st.markdown(
    f'<div class="formula-box"><strong>Status rule</strong><br>'
    f'{health["methodology"]["rule"]}<br><br>'
    f'<strong>Why no composite score?</strong><br>{health["methodology"]["why_no_composite_score"]}'
    f'</div>',
    unsafe_allow_html=True,
)

with st.expander("See the four vehicle-health metrics"):
    for metric, info in health["core_metrics_used_for_status"].items():
        st.markdown(f"### `{metric}`")
        st.markdown(f"**Formula:** `{info['formula']}`")
        st.markdown(f"**Source:** {info['source']}")
        if "watch_threshold" in info:
            st.markdown(
                f"**Watch:** ≥ {info['watch_threshold']} &nbsp;&nbsp; "
                f"**Investigate:** ≥ {info['investigate_threshold']}"
            )
        elif "rule" in info:
            st.markdown(f"**Rule:** {info['rule']}")

st.markdown("## Assumptions & limitations")
st.markdown(
    """
- The telemetry export is treated as the source for the recorded GPS and sensor readings. When another
  distance calculation disagrees with GPS, the disagreement is flagged rather than silently choosing one.
- The driver-score ceilings are fixed constants derived from the current cohort and then frozen for
  reproducibility.
- The four driver components use equal weighting because no alternative weighting scheme was specified.
- Vehicle health does not use maintenance-schedule fields to create a status because no maintenance
  interval standard was provided.
- Vehicle health is a sensor-pattern screen, **not a mechanical diagnosis**.
- The safety score summarizes observed behaviour for this week; it is **not an accident prediction**.
- This is one week of data, so longer-term patterns cannot be established from this dataset alone.
"""
)

st.markdown("## How I would use this analysis")
st.markdown(
    '<div class="interview-box">'
    '<strong>1. Start with the drivers requiring the most attention.</strong> '
    'Open the component breakdown instead of assuming one behaviour explains the score.<br><br>'
    '<strong>2. Check data confidence.</strong> '
    'A result supported by fewer clean trips deserves a closer trip-level review.<br><br>'
    '<strong>3. Investigate unusual vehicles.</strong> '
    'Look for the sensor pattern behind the status before calling it a mechanical problem.<br><br>'
    '<strong>4. Trace findings back to trips and telemetry.</strong> '
    'That is where a dashboard result becomes something I can actually investigate.<br><br>'
    '<strong>5. Use more historical data before making policy.</strong> '
    'This dataset is useful for screening and comparison, not for claiming a long-term trend.'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown("## If I had more data")
st.write(
    "I would test whether the same driver patterns repeat over multiple weeks, compare vehicle flags with "
    "actual maintenance records, and use incident outcomes if they became available. Those would be new "
    "analyses; they are not assumed by this dashboard."
)

st.markdown("---")
st.markdown(
    '<div class="subtitle" style="font-size:0.78rem;">'
    "The Step 5 and Step 6 JSON files remain the authoritative record of the formulas, thresholds and assumptions. "
    "This page only explains those existing outputs; it does not recalculate them."
    '</div>',
    unsafe_allow_html=True,
)
