"""Test EOD download with real provider"""

import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from market_downloader import MarketDownloader
from health_check import HealthChecker


def test_eod_download():
    """Test real EOD download"""
    print("=" * 60)
    print("FlipFlop HQ - EOD Download Test")
    print("=" * 60)

    # Check credentials
    api_key = os.environ.get("ALPACA_API_KEY")
    api_secret = os.environ.get("ALPACA_API_SECRET")

    if not api_key or not api_secret:
        print("⚠ WARNING: Alpaca credentials not set")
        print("  Set ALPACA_API_KEY and ALPACA_API_SECRET environment variables")
        print("  Using synthetic fallback for this test")
    else:
        print("✓ Alpaca credentials found")

    # Create downloader
    print("\n[1/5] Initializing downloader...")
    db_dir = "databases"
    downloader = MarketDownloader(db_dir)
    print(f"✓ Database directory: {db_dir}")

    # Test with yesterday's date (ensure data is available)
    test_date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
    print(f"✓ Test date: {test_date}")

    # Download data
    print(f"\n[2/5] Downloading EOD data for {test_date}...")
    instruments = ["NQ", "ES"]
    results = downloader.download_daily_data(instruments, test_date)

    for instrument, result in results.items():
        status = result.get("status", "UNKNOWN")
        print(f"  {instrument}: {status}")
        if result.get("bars_count"):
            print(f"    - Bars: {result['bars_count']}")
            print(f"    - Quality: {result.get('quality_score', 0):.2f}")
        if result.get("error"):
            print(f"    - Error: {result['error']}")

    # Check database
    print("\n[3/5] Verifying database...")
    db_path = downloader.get_db_path(test_date)
    if db_path.exists():
        print(f"✓ Database exists: {db_path}")
    else:
        print(f"✗ Database not found: {db_path}")
        return False

    # Run health check
    print("\n[4/5] Running health checks...")
    hc = HealthChecker(db_dir)
    health = hc.check_all()

    print(f"Overall Status: {health['status']}")
    for check_name, check_result in health['checks'].items():
        ok = check_result.get('ok', False)
        icon = "✓" if ok else "✗"
        msg = check_result.get('message', 'No message')
        print(f"  {icon} {check_name}: {msg}")

    # Summary
    print("\n[5/5] Summary...")
    print(f"Authority: {health.get('authority', 'UNKNOWN')}")
    print(f"Live: {health.get('live', 'UNKNOWN')}")

    if results and any(r.get('status') == 'COMPLETE' for r in results.values()):
        print("\n✅ EOD Download Test PASSED")
        return True
    else:
        print("\n⚠ EOD Download Test INCOMPLETE (check credentials)")
        return False

    print("\n" + "=" * 60)


if __name__ == "__main__":
    success = test_eod_download()
    sys.exit(0 if success else 1)
