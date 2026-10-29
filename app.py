"""
Bursa Malaysia IPO Performance Analytics Web App
Author: Data Engineering & Analytics Assistant
Features:
- Dual Timeframe: Daily (up to 6 months / 125 trading days) & Hourly (up to 5 trading days).
- Dual Baseline: IPO Issue Price vs. Debut Market Close.
- Normalized X-Axis: T+0, T+1... for daily; H+0, H+1... for hourly.
- Zero-friction metadata loading (works standalone without external JSON files).
"""

import datetime
from pathlib import Path
import sys

# Ensure project root directory is always on Python's module search path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Built-in default metadata: ensures app works immediately even if metadata.py / JSON is absent
DEFAULT_IPO_METADATA = [
    {
        "name": "MR D.I.Y. Group (M) Bhd",
        "code": "5296",
        "ticker": "5296.KL",
        "issue_price": 1.60,
        "listing_date": "2020-10-26",
        "sector": "Consumer Products & Services",
    },
    {
        "name": "CTOS Digital Berhad",
        "code": "5301",
        "ticker": "5301.KL",
        "issue_price": 1.10,
        "listing_date": "2021-07-19",
        "sector": "Technology / Financial Data",
    },
    {
        "name": "99 Speed Mart Retail Holdings",
        "code": "5326",
        "ticker": "5326.KL",
        "issue_price": 1.65,
        "listing_date": "2024-09-09",
        "sector": "Consumer Products & Services",
    },
    {
        "name": "ECO-SHOP Marketing Berhad",
        "code": "5337",
        "ticker": "5337.KL",
        "issue_price": 1.13,
        "listing_date": "2025-05-23",
        "sector": "Consumer Products & Services",
    },
    {
        "name": "Sunway Healthcare Holdings (SUNMED)",
        "code": "5555",
        "ticker": "5555.KL",
        "issue_price": 1.45,
        "listing_date": "2026-06-30",
        "sector": "Healthcare",
    },
]


def get_metadata():
    """
    Safely load metadata:
    1. Tries to import from metadata.py if user created it.
    2. Otherwise uses the built-in DEFAULT_IPO_METADATA.
    Never calls external JSON files or throws FileNotFoundError.
    """
    try:
        from metadata import get_all_ipos
        return get_all_ipos()
    except Exception:
        return [item.copy() for item in DEFAULT_IPO_METADATA]


try:
    from pipeline.data_loader import process_all_selected_ipos
except ModuleNotFoundError:
    st.error(
        f"**Pipeline Module Not Found!**\n\n"
        f"Make sure you have a `pipeline/` folder with `data_loader.py` and `__init__.py` inside `{PROJECT_ROOT}`."
    )
    st.stop()

# -----------------------------------------------------------------------------
# 1. Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Bursa Malaysia IPO Analytics",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# 2. Cached Pipeline Execution
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def run_pipeline(
    selected_names: list,
    metadata: list,
    timeframe: str,
    max_units: int,
    baseline_choice: str,
    force_refresh: bool = False,
):
    """
    Cached wrapper around the ETL pipeline to guarantee sub-second UI responsiveness.
    """
    return process_all_selected_ipos(
        selected_names=selected_names,
        metadata=metadata,
        timeframe=timeframe,
        max_units=max_units,
        baseline_type=baseline_choice,
        force_refresh=force_refresh,
    )


# -----------------------------------------------------------------------------
# 3. Streamlit Application
# -----------------------------------------------------------------------------
def main():
    st.title("📈 Bursa Malaysia IPO Performance Analytics")
    st.caption("Normalized Post-Listing Comparative Trajectory (Daily & Hourly Timeframes)")

    # Load metadata safely (no JSON file lookup)
    metadata = get_metadata()

    # --- Sidebar: Configuration & Controls ---
    with st.sidebar:
        st.header("⚙️ Timeframe & Anchoring")

        # Timeframe Selector
        timeframe = st.radio(
            "Select Timeframe:",
            options=["Daily", "Hourly"],
            help="Daily covers up to 6 months (125 trading days). Hourly covers up to the first 5 trading days from debut.",
        )

        if timeframe == "Daily":
            max_units = st.slider(
                "Evaluation Window (Trading Days):",
                min_value=20,
                max_value=250,
                value=125,
                step=5,
                help="125 trading days is approximately 6 calendar months on Bursa Malaysia.",
            )
            unit_label = "Trading Days"
            x_prefix = "T"
        else:
            max_units = st.slider(
                "Evaluation Window (Days from Listing):",
                min_value=1,
                max_value=5,
                value=5,
                step=1,
                help="Filters hourly candles up to a maximum of 5 trading days from debut.",
            )
            unit_label = "Trading Hours"
            x_prefix = "H"
            st.info(
                "💡 **Data Engineering Note**: Yahoo Finance free tier provides hourly data for the past 730 days (~2 years). "
                "Recent IPOs (e.g., 99SMART, ECOSHOP, SUNMED) are supported."
            )

        # Baseline Toggle
        baseline_choice = st.radio(
            "Anchoring Baseline (0% Point):",
            options=["IPO Issue Price", "Debut Market Close"],
            help=(
                "• IPO Issue Price: Measures total return from IPO allotment price (includes debut pop).\n"
                "• Debut Market Close: Measures return from secondary market debut session close."
            ),
        )

        st.markdown("---")
        st.subheader("🏢 Company Selection")

        all_company_names = [item["name"] for item in metadata]
        selected_names = st.multiselect(
            "Select IPOs to Compare:",
            options=all_company_names,
            default=all_company_names,
        )

        # Force refresh cache button
        force_refresh = st.button("🔄 Force Refresh Market Data")

        st.markdown("---")
        with st.expander("➕ Add Custom IPO"):
            new_name = st.text_input("Company Name", value="Farm Fresh Berhad")
            new_ticker = st.text_input("Yahoo Ticker (.KL)", value="5306.KL")
            new_price = st.number_input(
                "IPO Price (RM)", value=1.35, min_value=0.01, step=0.05
            )
            new_date = st.date_input("Listing Date", value=datetime.date(2022, 3, 22))
            if st.button("Add to Session"):
                metadata.append({
                    "name": new_name,
                    "code": new_ticker.replace(".KL", ""),
                    "ticker": new_ticker,
                    "issue_price": new_price,
                    "listing_date": str(new_date),
                    "sector": "Custom",
                })
                st.success(f"Added {new_name}! Check the company selection above.")

    if not selected_names:
        st.info("Please select at least one company from the sidebar.")
        return

    # --- Run Pipeline ---
    with st.spinner(f"Executing {timeframe} pipeline (cache check, ETL, and return normalization)..."):
        combined_df, scorecard_df, warnings = run_pipeline(
            selected_names=selected_names,
            metadata=metadata,
            timeframe=timeframe,
            max_units=max_units,
            baseline_choice=baseline_choice,
            force_refresh=force_refresh,
        )

    for warn in warnings:
        st.warning(warn)

    if combined_df.empty:
        st.warning(
            "No market data could be loaded for the selected timeframe and companies."
        )
        return

    # -------------------------------------------------------------------------
    # 4. Interactive Plotly Visualization
    # -------------------------------------------------------------------------
    fig = go.Figure()

    palette = [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
        "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
    ]

    time_col = "Timestamp" if "Timestamp" in combined_df.columns else "Date"
    time_fmt = "%Y-%m-%d %H:%M" if timeframe == "Hourly" else "%Y-%m-%d"

    for i, (name, group) in enumerate(combined_df.groupby("Company")):
        color = palette[i % len(palette)]
        fig.add_trace(
            go.Scatter(
                x=group["X_Index"],
                y=group["Pct_Return"],
                mode="lines",
                name=name,
                line=dict(width=2.5, color=color),
                customdata=group[[time_col, "Close", "Issue_Price"]],
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    f"{unit_label}: {x_prefix}+%{{x}}<br>"
                    f"Timestamp: %{{customdata[0]|{time_fmt}}}<br>"
                    "Close Price: RM %{customdata[1]:.2f}<br>"
                    "Percentage Return: <b>%{y:+.2f}%</b>"
                    "<extra></extra>"
                ),
                text=group["Company"],
            )
        )

    # 0% Reference Anchor Line
    fig.add_hline(
        y=0,
        line_dash="dash",
        line_color="#6c757d",
        annotation_text="Anchor Line (0.0%)",
        annotation_position="bottom right",
    )

    chart_title_timeframe = (
        f"{max_units}-Trading-Day Window (~6 Months)"
        if timeframe == "Daily"
        else f"First {max_units} Days from Listing (Hourly Resolution)"
    )

    fig.update_layout(
        title=dict(
            text=f"<b>Bursa Malaysia IPO Trajectory ({timeframe} Timeframe)</b><br><sup>Anchored to {baseline_choice} | {chart_title_timeframe}</sup>",
            x=0.02,
            font=dict(size=18),
        ),
        xaxis=dict(
            title=f"<b>Normalized {unit_label} Since Listing ({x_prefix}+n)</b>",
            gridcolor="#e9ecef",
            zeroline=True,
        ),
        yaxis=dict(
            title="<b>Percentage Return (%)</b>",
            ticksuffix="%",
            gridcolor="#e9ecef",
            zeroline=True,
            zerolinecolor="#6c757d",
        ),
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            title=None,
        ),
        template="plotly_white",
        height=620,
        margin=dict(l=40, r=40, t=90, b=40),
    )

    st.plotly_chart(fig, use_container_width=True)

    # -------------------------------------------------------------------------
    # 5. Performance Scorecard & Data Export
    # -------------------------------------------------------------------------
    st.subheader(f"📊 Performance Scorecard ({timeframe} Resolution)")
    st.dataframe(scorecard_df, use_container_width=True, hide_index=True)

    # Download Clean Dataset
    export_cols = [
        "Company", "Ticker", "X_Index", "X_Label", time_col, "Close", "Adj Close", "Pct_Return"
    ]
    available_cols = [c for c in export_cols if c in combined_df.columns]
    csv_data = combined_df[available_cols].to_csv(index=False).encode("utf-8")

    st.download_button(
        label=f"📥 Download Normalized {timeframe} Comparison Dataset (CSV)",
        data=csv_data,
        file_name=f"bursa_ipo_{timeframe.lower()}_returns.csv",
        mime="text/csv",
    )


if __name__ == "__main__":
    main()