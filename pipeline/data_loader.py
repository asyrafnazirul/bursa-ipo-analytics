"""
ETL Pipeline: Data Ingestion, Local Caching, and Return Normalization
Supports both Daily (up to 6 months / 125 trading days) and Hourly (up to 5 trading days).
"""

import json
import os
from pathlib import Path
import sys
from typing import Dict, List, Optional, Tuple

import pandas as pd
import yfinance as yf

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

CACHE_DIR = PROJECT_ROOT / "cache"
DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_JSON_PATH = DATA_DIR / "ipo_metadata.json"


def load_ipo_metadata() -> List[Dict]:
    """
    Load IPO metadata.
    First checks metadata.py in project root; falls back to data/ipo_metadata.json.
    """
    # 1. Try importing directly from metadata.py
    try:
        from metadata import IPO_METADATA
        return [item.copy() for item in IPO_METADATA]
    except ImportError:
        pass

    # 2. Try loading from data/ipo_metadata.json
    if DEFAULT_JSON_PATH.exists():
        with open(DEFAULT_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    # 3. Built-in hardcoded fallback so pipeline never crashes if files are missing
    return [
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


def fetch_and_cache_stock(
    ticker: str,
    start_date: str,
    timeframe: str = "Daily",
    cache_dir: Optional[Path] = None,
    force_refresh: bool = False,
) -> pd.DataFrame:
    """
    Ingestion & Cache Layer:
    - Daily: Fetches daily OHLCV from listing date forward.
    - Hourly: Fetches 1h intraday bars for up to 10 calendar days (~5 trading days).
    Note: Yahoo Finance free tier limits hourly/intraday history to the past 730 days (~2 years).
    """
    target_cache_dir = cache_dir or CACHE_DIR
    target_cache_dir.mkdir(parents=True, exist_ok=True)

    clean_code = ticker.replace(".KL", "").replace("^", "")
    suffix = "daily" if timeframe == "Daily" else "hourly"
    cache_file = target_cache_dir / f"{clean_code}_{suffix}.parquet"

    listing_dt = pd.to_datetime(start_date)

    # 1. Read from cache if available
    if cache_file.exists() and not force_refresh:
        try:
            cached_df = pd.read_parquet(cache_file)
            time_col = "Timestamp" if "Timestamp" in cached_df.columns else "Date"
            cached_df[time_col] = pd.to_datetime(cached_df[time_col])
            filtered = (
                cached_df[cached_df[time_col] >= listing_dt]
                .sort_values(time_col)
                .reset_index(drop=True)
            )
            if not filtered.empty:
                return filtered
        except Exception:
            pass

    # 2. Extract from yfinance
    try:
        if timeframe == "Daily":
            start_dt = listing_dt - pd.Timedelta(days=5)
            df = yf.download(
                ticker,
                start=start_dt.strftime("%Y-%m-%d"),
                progress=False,
                auto_adjust=False,
                interval="1d",
            )
        else:
            start_dt = listing_dt
            end_dt = listing_dt + pd.Timedelta(days=12)
            df = yf.download(
                ticker,
                start=start_dt.strftime("%Y-%m-%d"),
                end=end_dt.strftime("%Y-%m-%d"),
                progress=False,
                auto_adjust=False,
                interval="1h",
            )

        if df.empty:
            return pd.DataFrame()

        # Flatten multi-index columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]

        df = df.reset_index()

        # Normalize timestamp column name
        if "Datetime" in df.columns:
            df = df.rename(columns={"Datetime": "Timestamp"})
        elif "Date" in df.columns:
            df = df.rename(columns={"Date": "Timestamp"})

        df["Timestamp"] = pd.to_datetime(df["Timestamp"]).dt.tz_localize(None)

        # Cache complete fetched raw data
        try:
            df.to_parquet(cache_file, index=False)
        except Exception:
            csv_file = target_cache_dir / f"{clean_code}_{suffix}.csv"
            df.to_csv(csv_file, index=False)

        filtered = (
            df[df["Timestamp"] >= listing_dt].sort_values("Timestamp").reset_index(drop=True)
        )
        return filtered
    except Exception as exc:
        print(f"[ERROR] Failed fetching {timeframe} data for {ticker}: {exc}")
        return pd.DataFrame()


def transform_ipo_series(
    df: pd.DataFrame,
    ipo_info: dict,
    timeframe: str = "Daily",
    max_units: int = 125,
    baseline_type: str = "IPO Issue Price",
) -> Optional[pd.DataFrame]:
    """
    Transformation Layer:
    - Daily: Slices up to max_units (e.g. 125 trading days), indexed as Trading_Day (T+0, T+1, ...).
    - Hourly: Slices up to max_units (1 to 5 trading days), indexed as Trading_Hour (H+0, H+1, ...).
    - Normalizes cumulative percentage returns based on selected baseline.
    """
    if df.empty:
        return None

    time_col = "Timestamp" if "Timestamp" in df.columns else "Date"
    sub_df = df.copy()

    if timeframe == "Daily":
        sub_df = sub_df.head(max_units).copy()
        if len(sub_df) == 0:
            return None
        sub_df["X_Index"] = range(len(sub_df))
        sub_df["X_Label"] = [f"T+{i}" for i in range(len(sub_df))]
    else:
        unique_dates = sub_df[time_col].dt.date.unique()
        allowed_dates = unique_dates[:max_units]
        sub_df = sub_df[sub_df[time_col].dt.date.isin(allowed_dates)].copy()
        if len(sub_df) == 0:
            return None
        sub_df["X_Index"] = range(len(sub_df))
        sub_df["X_Label"] = [f"H+{i}" for i in range(len(sub_df))]

    issue_price = float(ipo_info["issue_price"])
    p0_market = float(sub_df.iloc[0]["Close"])
    adj_p0_market = (
        float(sub_df.iloc[0]["Adj Close"]) if "Adj Close" in sub_df.columns else p0_market
    )
    price_col = "Adj Close" if "Adj Close" in sub_df.columns else "Close"

    if baseline_type == "IPO Issue Price":
        sub_df["Pct_Return"] = ((sub_df[price_col] - issue_price) / issue_price) * 100.0
    else:
        sub_df["Pct_Return"] = (
            (sub_df[price_col] - adj_p0_market) / adj_p0_market
        ) * 100.0

    sub_df["Company"] = ipo_info["name"]
    sub_df["Ticker"] = ipo_info["ticker"]
    sub_df["Issue_Price"] = issue_price
    sub_df["Debut_Market_Price"] = p0_market

    return sub_df


def process_all_selected_ipos(
    selected_names: List[str],
    metadata: List[Dict],
    timeframe: str = "Daily",
    max_units: int = 125,
    baseline_type: str = "IPO Issue Price",
    force_refresh: bool = False,
) -> Tuple[pd.DataFrame, pd.DataFrame, List[str]]:
    """
    Pipeline Orchestrator:
    Extracts, transforms, and normalizes data across all selected companies.
    """
    series_list = []
    summary_records = []
    warnings = []

    target_ipos = [item for item in metadata if item["name"] in selected_names]

    for ipo in target_ipos:
        raw_df = fetch_and_cache_stock(
            ticker=ipo["ticker"],
            start_date=ipo["listing_date"],
            timeframe=timeframe,
            force_refresh=force_refresh,
        )

        if raw_df.empty and timeframe == "Hourly":
            listing_year = pd.to_datetime(ipo["listing_date"]).year
            warnings.append(
                f"{ipo['name']} ({ipo['ticker']}): Hourly data is unavailable from Yahoo Finance "
                f"because it listed in {listing_year} (Yahoo Finance free intraday archive is limited to the past 730 days)."
            )
            continue

        proc_df = transform_ipo_series(
            raw_df,
            ipo,
            timeframe=timeframe,
            max_units=max_units,
            baseline_type=baseline_type,
        )

        if proc_df is not None and not proc_df.empty:
            series_list.append(proc_df)

            day0_ret = proc_df.iloc[0]["Pct_Return"]
            final_ret = proc_df.iloc[-1]["Pct_Return"]
            peak_ret = proc_df["Pct_Return"].max()
            max_dd = proc_df["Pct_Return"].min()

            rec = {
                "Company": ipo["name"],
                "Ticker": ipo["ticker"],
                "Listing Date": ipo["listing_date"],
                "Issue Price (RM)": f"RM {ipo['issue_price']:.2f}",
                "Debut Close (RM)": f"RM {proc_df.iloc[0]['Close']:.2f}",
                "Debut Return": f"{day0_ret:+.2f}%",
                "Final Window Return": f"{final_ret:+.2f}%",
                "Peak Return": f"{peak_ret:+.2f}%",
                "Max Dip": f"{max_dd:+.2f}%",
            }

            if timeframe == "Daily":
                m1_idx = min(21, len(proc_df) - 1)
                m3_idx = min(63, len(proc_df) - 1)
                rec["1-Month Return"] = f"{proc_df.iloc[m1_idx]['Pct_Return']:+.2f}%"
                rec["3-Month Return"] = f"{proc_df.iloc[m3_idx]['Pct_Return']:+.2f}%"
                rec["Days Evaluated"] = len(proc_df)
            else:
                rec["Hours Evaluated"] = len(proc_df)

            summary_records.append(rec)

    combined_df = (
        pd.concat(series_list, ignore_index=True) if series_list else pd.DataFrame()
    )
    scorecard_df = pd.DataFrame(summary_records)
    return combined_df, scorecard_df, warnings


if __name__ == "__main__":
    print("Testing pipeline metadata loading...")
    meta = load_ipo_metadata()
    print(f"Loaded {len(meta)} IPOs successfully.")
    for item in meta:
        print(f"• {item['name']} ({item['code']}) - RM {item['issue_price']:.2f} on {item['listing_date']}")