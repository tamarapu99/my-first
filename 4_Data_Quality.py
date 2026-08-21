import streamlit as st
import pandas as pd

from utils import (
    inject_base_css, kpi_card, note,
    load_safety_validation, load_vehicle_validation, load_feature_validation,
    load_json, load_driver_scores, load_overlaps_driver, load_overlaps_vehicle,
    load_trips, COLORS,
)

st.set_page_config(page_title="Data Quality - VexarDrive", layout="wide")
inject_base_css()

st.markdown("# Data Quality")
st.markdown(
    '<div class="subtitle">Why this matters: every number on the other pages is only as trustworthy as the '
    'data quality behind it. This page shows that work instead of hiding it.</div>',
    unsafe_allow_html=True,
)

cleaning = load_json("cleaning_summary.json")
feature_checks = load_feature_validation()
safety_checks = load_safety_validation()
vehicle_checks = load_vehicle_validation()
scores_df = load_driver_scores()
trips = load_trips()

# ---------------------------------------------------------------------------
# Overview KPIs
# ---------------------------------------------------------------------------
all_checks = pd.concat([
    feature_checks.assign(stage="Step 4 — Features"),
    safety_checks.assign(stage="Step 5 — Safety scores"),
    vehicle_checks.assign(stage="Step 6 — Vehicle health"),
])
n_pass = (all_checks["status"] == "Pass").sum()
n_total_checks = len(all_checks)

c1, c2, c3, c4 = st.columns(4)
with c1:
    kpi_card("Validation checks run", f"{n_total_checks}", "across Steps 4-6")
with c2:
    kpi_card("Checks passed", f"{n_pass} / {n_total_checks}", "100% pass rate" if n_pass == n_total_checks else "see failures below")
with c3:
    kpi_card("Records removed", f"{cleaning['records_removed']}", "no rows dropped during cleaning")
with c4:
    kpi_card("Avg. driver data confidence", f"{scores_df['data_confidence_pct'].mean():.0f}%", "share of usable trips that are clean")

if n_pass == n_total_checks:
    note("Every automated validation check across feature engineering, driver scoring, and vehicle health passed.")
else:
    st.warning(f"{n_total_checks - n_pass} check(s) did not pass — see the tables below for exactly which ones.")

st.markdown("---")

# ---------------------------------------------------------------------------
# Validation check tables
# ---------------------------------------------------------------------------
st.markdown("### Validation checks by stage")

tab1, tab2, tab3 = st.tabs(["Step 4 — Feature engineering", "Step 5 — Driver safety scores", "Step 6 — Vehicle health"])

with tab1:
    st.dataframe(feature_checks, hide_index=True, width="stretch")
with tab2:
    st.dataframe(safety_checks, hide_index=True, width="stretch")
with tab3:
    st.dataframe(vehicle_checks, hide_index=True, width="stretch")

st.markdown("---")

# ---------------------------------------------------------------------------
# Quality flags created
# ---------------------------------------------------------------------------
st.markdown("### Quality flags created during cleaning")
st.write(
    "These flags were raised while preparing the raw fleet export — none of them removed a record, "
    "they mark rows that need to be treated carefully downstream (excluded, down-weighted, or simply "
    "noted)."
)

flags = cleaning["quality_flags_created"]
flag_df = pd.DataFrame(
    [{"Flag": k, "Rows flagged": v} for k, v in flags.items()]
).sort_values("Rows flagged", ascending=False)
st.dataframe(flag_df, hide_index=True, width="stretch", height=420)

st.markdown("---")

# ---------------------------------------------------------------------------
# Overlap exclusions
# ---------------------------------------------------------------------------
st.markdown("### Overlapping-trip exclusions")
st.write(
    "Some trips overlap in time with another trip for the same driver, or the same vehicle — logically "
    "impossible if both are genuine, so these were excluded from Step 5 scoring rather than silently kept."
)

overlaps_driver = load_overlaps_driver()
overlaps_vehicle = load_overlaps_vehicle()

c5, c6 = st.columns(2)
with c5:
    kpi_card("Driver-level overlaps", f"{len(overlaps_driver)}", "overlapping trip pairs, same driver")
with c6:
    kpi_card("Vehicle-level overlaps", f"{len(overlaps_vehicle)}", "overlapping trip pairs, same vehicle")

with st.expander("View overlapping-trip pairs (driver-level)"):
    st.dataframe(overlaps_driver, hide_index=True, width="stretch")
with st.expander("View overlapping-trip pairs (vehicle-level)"):
    st.dataframe(overlaps_vehicle, hide_index=True, width="stretch")

st.markdown("---")

# ---------------------------------------------------------------------------
# Driver data confidence distribution
# ---------------------------------------------------------------------------
st.markdown("### Data confidence across drivers")
st.write(
    "Data confidence is the share of a driver's usable trips that were clean (no quality flag), as "
    "opposed to quality-flagged and down-weighted. It's reported alongside the safety score, not folded "
    "into it — a driver can have a high score built on thin data, and that's worth knowing."
)

conf_table = scores_df[[
    "Driver_ID", "total_trips", "usable_trips", "excluded_overlap_trips",
    "clean_usable_trips", "downweighted_usable_trips", "data_confidence_pct",
]].sort_values("data_confidence_pct")
conf_table.columns = [
    "Driver", "Total trips", "Usable trips", "Excluded (overlap)",
    "Clean trips", "Quality-flagged trips", "Data confidence %",
]
st.dataframe(conf_table, hide_index=True, width="stretch", height=380)

low_conf = scores_df[scores_df["data_confidence_pct"] < 30]
if len(low_conf):
    st.warning(
        f"{len(low_conf)} driver(s) — {', '.join(low_conf['Driver_ID'])} — have data confidence below 30%. "
        "Their scores are calculated with the same formula as everyone else, but rest on fewer clean trips."
    )

st.markdown("---")
st.markdown(
    f'<div style="font-size:0.78rem; color:{COLORS["text_muted"]};">'
    "Source: processed/analytical/*_validation_checks.csv and cleaning_summary.json (Steps 2-6, read-only)."
    "</div>",
    unsafe_allow_html=True,
)
