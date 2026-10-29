# Bursa Malaysia IPO Performance Analytics

Interactive web application and data pipeline designed to analyze and compare post-listing return trajectories across Bursa Malaysia Initial Public Offerings (IPOs). 

Built with **Python**, **Streamlit**, **Plotly**, and **yfinance**, this project normalizes disparate listing dates along a synchronized relative trading timeline to provide true like-for-like debut performance comparisons.

---

## 📌 Problem & Motivation

Evaluating IPO performance across multiple companies is challenging because each firm lists at different dates, quarters, and market cycles. Comparing them on standard calendar dates results in misaligned timelines, while raw calendar timeframes fail to account for weekends and public holidays.

This tool solves this by:
1. **Anchoring all IPOs to a common starting point ($T=0$ or $H=0$)** regardless of their actual listing year.
2. **Normalizing by trading sessions** rather than calendar days to prevent distorted comparison gaps.
3. **Providing dual-baseline evaluations** to measure both primary subscriber allotment returns and secondary market trading performance.

---

## 🚀 Key Features

* **Dual Timeframe Granularity**:
  * **Daily Resolution**: Evaluates post-IPO trajectories for up to 6 months (~125 trading days), aligned on a continuous $T+0, T+1, \dots, T+n$ axis.
  * **Hourly Resolution**: High-frequency intraday view covering up to the first 5 trading days from debut ($H+0, H+1, \dots, H+n$).
* **Dual Anchoring Baselines**:
  * **IPO Issue Price**: Measures total return for IPO allotment subscribers, capturing the opening debut pop or discount on Day 0.
  * **Debut Market Close**: Anchors Day 0 / Hour 0 to 0.0%, measuring secondary market performance from the end of the first trading session.
* **Resilient Data Engineering Pipeline**:
  * **Two-Tier Caching**: Persists raw OHLCV market data locally in Apache Parquet format (`cache/`) to eliminate repetitive API calls, combined with Streamlit's in-memory `@st.cache_data` for instant UI responsiveness.
  * **Asymmetric Time-Series Handling**: Automatically handles newer listings with shorter histories alongside mature IPOs without distorting axes.
* **Performance Scorecard & Export**:
  * Automated summary metrics including Day 1 Debut Pop, 1-Month ($T+21$), 3-Month ($T+63$), Window Return, Peak Gain, and Max Drawdown.
  * One-click CSV export of the normalized comparison dataset.

---

## 🏗️ Architecture

```
┌─────────────────────────────────┐
│     Yahoo Finance API (.KL)     │
└────────────────┬────────────────┘
                 │ (Live Ingestion)
                 ▼
┌─────────────────────────────────┐
│    pipeline/data_loader.py      │ <─── metadata.py (Bursa IPO Directory)
│   • Parquet Local Caching       │
│   • Time-Series Alignment       │
│   • Return Normalization        │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│             app.py              │
│   • Streamlit Dashboard         │
│   • Plotly Interactive Chart    │
│   • Performance Scorecard       │
└─────────────────────────────────┘
```

---

## 📂 Project Structure

```text
bursa-ipo-analytics/
├── cache/                  # Auto-generated directory for cached Parquet files
├── pipeline/
│   ├── __init__.py         # Package identifier
│   └── data_loader.py      # ETL pipeline (extraction, caching, transformations)
├── app.py                  # Streamlit application & interactive Plotly visualization
├── metadata.py             # IPO seed directory (Bursa codes, issue prices, listing dates)
├── requirements.txt        # Python dependencies
├── .gitignore              # Git ignore rules for Python, cache, and virtual environments
└── README.md               # Project documentation
```

---

## 🛠️ Tech Stack

* **Language**: Python 3.10+
* **Dashboard Framework**: [Streamlit](https://streamlit.io/)
* **Visualization**: [Plotly Graph Objects](https://plotly.com/python/)
* **Data Manipulation**: [Pandas](https://pandas.pydata.org/)
* **Financial Data**: [yfinance](https://pypi.org/project/yfinance/)
* **Storage / Cache**: Apache Parquet (`pyarrow` / `fastparquet`)

---

## ⚡ Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/<your-username>/bursa-ipo-analytics.git
cd bursa-ipo-analytics
```

### 2. Set Up a Virtual Environment (Recommended)
```bash
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Application
```bash
streamlit run app.py
```
Open your browser and navigate to `http://localhost:8501`.

---

## 📊 Default Tracked Companies

| Company | Bursa Code | Yahoo Ticker | Listing Date | IPO Issue Price | Sector |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **MR D.I.Y. Group (M) Bhd** | `5296` | `5296.KL` | 2020-10-26 | RM 1.60 | Consumer Products & Services |
| **CTOS Digital Berhad** | `5301` | `5301.KL` | 2021-07-19 | RM 1.10 | Technology / Financial Data |
| **99 Speed Mart Retail Holdings** | `5326` | `5326.KL` | 2024-09-09 | RM 1.65 | Consumer Products & Services |
| **ECO-SHOP Marketing Berhad** | `5337` | `5337.KL` | 2025-05-23 | RM 1.13 | Consumer Products & Services |
| **Sunway Healthcare Holdings (SUNMED)** | `5555` | `5555.KL` | 2026-06-30 | RM 1.45 | Healthcare |

You can add additional IPOs directly through the app interface or by updating `metadata.py`.

---

## 📝 License

Distributed under the MIT License. See `LICENSE` for more information.
