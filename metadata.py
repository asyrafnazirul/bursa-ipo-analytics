# At the top of app.py
try:
    from metadata import get_all_ipos, IPO_METADATA
    def get_metadata():
        return get_all_ipos()
except ImportError:
    try:
        from pipeline.data_loader import load_ipo_metadata
        def get_metadata():
            return load_ipo_metadata()
    except Exception:
        def get_metadata():
            return [
                {"name": "MR D.I.Y. Group (M) Bhd", "code": "5296", "ticker": "5296.KL", "issue_price": 1.60, "listing_date": "2020-10-26", "sector": "Consumer"},
                {"name": "CTOS Digital Berhad", "code": "5301", "ticker": "5301.KL", "issue_price": 1.10, "listing_date": "2021-07-19", "sector": "Technology"},
                {"name": "99 Speed Mart Retail Holdings", "code": "5326", "ticker": "5326.KL", "issue_price": 1.65, "listing_date": "2024-09-09", "sector": "Consumer"},
                {"name": "ECO-SHOP Marketing Berhad", "code": "5337", "ticker": "5337.KL", "issue_price": 1.13, "listing_date": "2025-05-23", "sector": "Consumer"},
                {"name": "Sunway Healthcare Holdings (SUNMED)", "code": "5555", "ticker": "5555.KL", "issue_price": 1.45, "listing_date": "2026-06-30", "sector": "Healthcare"},
            ]