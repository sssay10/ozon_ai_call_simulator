"""Convert Locust HTML report to PDF via headless Chromium (playwright).

Usage:
    python convert_report.py
    python convert_report.py --html path/to/report.html --pdf path/to/report.pdf

First-time setup (installs Chromium, ~150 MB, one time only):
    pip install playwright
    playwright install chromium
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def convert(html_path: Path, pdf_path: Path) -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "playwright is not installed. Run:\n"
            "  pip install playwright\n"
            "  playwright install chromium",
            file=sys.stderr,
        )
        sys.exit(1)

    if not html_path.exists():
        print(f"HTML report not found: {html_path}", file=sys.stderr)
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(f"file://{html_path.absolute()}", wait_until="networkidle")
        page.pdf(path=str(pdf_path), format="A4", print_background=True)
        browser.close()

    print(f"PDF report saved: {pdf_path}")


def main() -> None:
    reports_dir = Path(__file__).parent / "reports"

    parser = argparse.ArgumentParser(description="Convert Locust HTML report to PDF")
    parser.add_argument(
        "--html",
        type=Path,
        default=reports_dir / "report.html",
        help="Path to Locust HTML report (default: reports/report.html)",
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        default=reports_dir / "report.pdf",
        help="Output PDF path (default: reports/report.pdf)",
    )
    args = parser.parse_args()

    args.pdf.parent.mkdir(parents=True, exist_ok=True)
    convert(args.html, args.pdf)


if __name__ == "__main__":
    main()
