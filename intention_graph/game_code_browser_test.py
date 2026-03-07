"""Browser smoke tests for generated game code using Playwright.

Validates that generated HTML/CSS/JS actually works in a real browser:
1. Page loads without JS errors
2. Screen divs exist and one is visible
3. Navigation works (click button, target screen appears)
4. Canvas exists in gameplay screen
5. No console errors after navigation

Gracefully degrades: returns SKIPPED metric if playwright is not installed.
"""

from __future__ import annotations

import os
import tempfile
from typing import Any

from intention_graph.wireframe_quality import QualityMetric

try:
    from playwright.sync_api import sync_playwright

    _HAS_PLAYWRIGHT = True
except ImportError:
    _HAS_PLAYWRIGHT = False


def browser_smoke_test(
    html: str,
    css: str,
    js: str,
    wireframe: dict[str, Any],
    headless: bool = True,
) -> QualityMetric:
    """Run 5 browser smoke checks on generated game code.

    Returns a QualityMetric with score = passed_checks / 5.
    Pass threshold: score >= 0.6 (at least 3/5 checks pass).

    If playwright is not installed, returns a SKIPPED metric (score=0, passed=True).
    """
    if not _HAS_PLAYWRIGHT:
        return QualityMetric(
            name="browser_smoke",
            passed=True,
            score=0.0,
            detail="SKIPPED: playwright not installed",
        )

    # Extract interface IDs and navigation targets from wireframe
    interfaces = wireframe.get("interfaces", [])
    screen_ids = [iface.get("interface_id", "") for iface in interfaces if iface.get("interface_id")]

    # Write files to temp directory
    tmp_dir = tempfile.mkdtemp(prefix="game_smoke_")
    try:
        with open(os.path.join(tmp_dir, "index.html"), "w") as f:
            f.write(html)
        with open(os.path.join(tmp_dir, "style.css"), "w") as f:
            f.write(css)
        with open(os.path.join(tmp_dir, "core.js"), "w") as f:
            f.write(js)

        results = _run_checks(tmp_dir, screen_ids, headless)
    finally:
        # Clean up temp files
        for fname in ("index.html", "style.css", "core.js"):
            try:
                os.remove(os.path.join(tmp_dir, fname))
            except OSError:
                pass
        try:
            os.rmdir(tmp_dir)
        except OSError:
            pass

    passed_checks = sum(1 for v in results.values() if v)
    total_checks = len(results)
    score = passed_checks / total_checks if total_checks > 0 else 0.0
    passed = score >= 0.6

    detail_parts = [f"{k}={'OK' if v else 'FAIL'}" for k, v in results.items()]
    detail = f"{passed_checks}/{total_checks} checks: {', '.join(detail_parts)}"

    return QualityMetric(
        name="browser_smoke",
        passed=passed,
        score=score,
        detail=detail,
    )


def _run_checks(
    tmp_dir: str,
    screen_ids: list[str],
    headless: bool,
) -> dict[str, bool]:
    """Execute the 5 browser smoke checks. Returns dict of check_name → passed."""
    results: dict[str, bool] = {
        "page_loads": False,
        "screens_exist": False,
        "navigation_works": False,
        "canvas_exists": False,
        "no_errors_after_nav": False,
    }

    file_url = f"file://{os.path.join(tmp_dir, 'index.html')}"
    console_errors: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        try:
            page = browser.new_page()

            # Collect console errors
            page.on("console", lambda msg: (
                console_errors.append(msg.text)
                if msg.type == "error"
                else None
            ))

            # Navigate to page
            page.goto(file_url, wait_until="load", timeout=10000)
            page.wait_for_timeout(500)  # Let JS initialize

            # Check 1: Page loads without JS errors
            results["page_loads"] = len(console_errors) == 0

            # Check 2: Screen divs exist, at least one visible
            if screen_ids:
                found_screens = 0
                visible_screens = 0
                for sid in screen_ids:
                    el = page.query_selector(f"#{sid}")
                    if el:
                        found_screens += 1
                        if el.is_visible():
                            visible_screens += 1

                results["screens_exist"] = found_screens > 0 and visible_screens >= 1
            else:
                results["screens_exist"] = True  # No screens to check

            # Check 3: Navigation works — click a button and check if
            # a different screen becomes visible (not just showScreen pattern)
            errors_before_nav = len(console_errors)

            # Snapshot which screens are visible before clicking
            visible_before: set[str] = set()
            for sid in screen_ids:
                el = page.query_selector(f"#{sid}")
                if el and el.is_visible():
                    visible_before.add(sid)

            # Find any clickable button on the currently visible screen
            # Try onclick buttons first, then any visible button
            nav_button = page.query_selector(
                "button[onclick], [onclick]"
            )
            if not nav_button or not nav_button.is_visible():
                nav_button = page.query_selector("button")
            if nav_button and nav_button.is_visible():
                try:
                    nav_button.click(timeout=5000)
                    page.wait_for_timeout(500)

                    # Check if visibility changed — a new screen appeared
                    visible_after: set[str] = set()
                    for sid in screen_ids:
                        el = page.query_selector(f"#{sid}")
                        if el and el.is_visible():
                            visible_after.add(sid)

                    results["navigation_works"] = visible_after != visible_before
                except Exception:
                    results["navigation_works"] = False
            else:
                results["navigation_works"] = False

            # Check 4: Canvas exists in a gameplay-like screen
            canvas = page.query_selector("canvas")
            results["canvas_exists"] = canvas is not None

            # Check 5: No new console errors after navigation
            errors_after_nav = len(console_errors)
            results["no_errors_after_nav"] = errors_after_nav == errors_before_nav

        finally:
            browser.close()

    return results
