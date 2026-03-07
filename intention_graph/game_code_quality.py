"""Game Code Quality Evaluation: PDCA Check phase for Stage 4.

Evaluates generated game code (HTML/CSS/JS) against wireframe specs using:
1. Layer 1: Code Runnability (file completeness, HTML validity, JS syntax, CSS refs)
2. Layer 2: Wireframe Fidelity (screen coverage, element coverage, style, navigation)
3. Layer 3: LLM-as-judge semantic evaluation (mechanics, state mgmt, interaction)
"""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from typing import Any

import anthropic

from intention_graph.wireframe_quality import QualityMetric, QualityReport


# ── HTML Parser ──────────────────────────────────────────────────────────────


class _HTMLElementExtractor(HTMLParser):
    """Extract tags with id, class, onclick, src, style, text content.

    Also tracks which screen div each element belongs to via `screen_id`.
    """

    def __init__(self) -> None:
        super().__init__()
        self.elements: list[dict[str, Any]] = []
        self._tag_stack: list[tuple[str, dict[str, Any]]] = []
        self._screen_stack: list[str] = []  # track nesting inside screen divs

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_dict = dict(attrs)
        elem_id = attr_dict.get("id", "")
        elem_class = attr_dict.get("class", "")

        # Detect screen divs (divs with class "screen" or similar patterns)
        is_screen = "screen" in elem_class.split() if elem_class else False
        if is_screen and elem_id:
            self._screen_stack.append(elem_id)

        current_screen = self._screen_stack[-1] if self._screen_stack else ""

        elem: dict[str, Any] = {
            "tag": tag,
            "id": elem_id,
            "class": elem_class,
            "onclick": attr_dict.get("onclick", ""),
            "src": attr_dict.get("src", ""),
            "href": attr_dict.get("href", ""),
            "style": attr_dict.get("style", ""),
            "text": "",
            "screen_id": current_screen,
        }
        self._tag_stack.append((tag, elem))
        self.elements.append(elem)

    def handle_endtag(self, tag: str) -> None:
        # Pop from tag stack, matching the tag name
        for i in range(len(self._tag_stack) - 1, -1, -1):
            if self._tag_stack[i][0] == tag:
                _, elem = self._tag_stack.pop(i)
                # If this was a screen div, pop from screen stack
                if elem.get("screen_id") == elem.get("id") and elem.get("id"):
                    if "screen" in elem.get("class", "").split():
                        if self._screen_stack and self._screen_stack[-1] == elem["id"]:
                            self._screen_stack.pop()
                break

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text and self._tag_stack:
            self._tag_stack[-1][1]["text"] += text


def _extract_html_elements(html: str) -> list[dict[str, Any]]:
    """Parse HTML and return list of element dicts."""
    parser = _HTMLElementExtractor()
    try:
        parser.feed(html)
    except Exception:
        pass
    return parser.elements


# ── Layer 1: Code Runnability ────────────────────────────────────────────────


def _check_file_completeness(html: str, css: str, js: str) -> QualityMetric:
    """All 3 files non-empty, HTML references CSS/JS via <link> + <script>.

    Critical metric.
    """
    issues = []
    if not html.strip():
        issues.append("HTML empty")
    if not css.strip():
        issues.append("CSS empty")
    if not js.strip():
        issues.append("JS empty")

    has_css_ref = bool(
        re.search(r'<link[^>]+href=["\'][^"\']*\.css["\']', html, re.IGNORECASE)
        or re.search(r"<style", html, re.IGNORECASE)
    )
    has_js_ref = bool(
        re.search(r'<script[^>]+src=["\'][^"\']*\.js["\']', html, re.IGNORECASE)
        or re.search(r"<script[^>]*>", html, re.IGNORECASE)
    )

    if html.strip() and not has_css_ref:
        issues.append("HTML missing CSS reference")
    if html.strip() and not has_js_ref:
        issues.append("HTML missing JS reference")

    total_checks = 5  # 3 non-empty + 2 references
    passed_checks = total_checks - len(issues)
    score = passed_checks / total_checks

    return QualityMetric(
        name="file_completeness",
        passed=len(issues) == 0,
        score=score,
        detail="; ".join(issues) if issues else "All files present with references",
    )


def _check_html_validity(html: str) -> QualityMetric:
    """Parseable by html.parser, has <html>/<head>/<body>, no major errors."""
    if not html.strip():
        return QualityMetric(
            name="html_validity", passed=False, score=0.0, detail="Empty HTML"
        )

    issues = []

    # Check parseability
    try:
        parser = _HTMLElementExtractor()
        parser.feed(html)
    except Exception as e:
        return QualityMetric(
            name="html_validity",
            passed=False,
            score=0.0,
            detail=f"Parse error: {e}",
        )

    # Check required structure tags
    html_lower = html.lower()
    for tag in ["<html", "<head", "<body"]:
        if tag not in html_lower:
            issues.append(f"Missing {tag}>")

    # Check doctype
    if "<!doctype" not in html_lower:
        issues.append("Missing DOCTYPE")

    total_checks = 4  # parse + html + head + body
    # Parse always passes if we got here
    passed_checks = total_checks - len(issues)
    score = passed_checks / total_checks

    return QualityMetric(
        name="html_validity",
        passed=score >= 0.75,
        score=score,
        detail="; ".join(issues) if issues else "Valid HTML structure",
    )


def _check_js_syntax(js: str) -> QualityMetric:
    """Balanced braces/parens, has function definitions, has event listeners."""
    if not js.strip():
        return QualityMetric(
            name="js_syntax", passed=False, score=0.0, detail="Empty JS"
        )

    checks = 0
    total = 4

    # Balanced braces
    if js.count("{") == js.count("}"):
        checks += 1
    # Balanced parens
    if js.count("(") == js.count(")"):
        checks += 1
    # Has function definitions
    has_func = bool(
        re.search(r"\bfunction\s+\w+", js)
        or re.search(r"(const|let|var)\s+\w+\s*=\s*(async\s+)?\(", js)
        or re.search(r"(const|let|var)\s+\w+\s*=\s*(async\s+)?function", js)
        or re.search(r"\w+\s*\([^)]*\)\s*\{", js)
    )
    if has_func:
        checks += 1
    # Has event listeners or onclick
    has_events = bool(
        re.search(r"addEventListener", js)
        or re.search(r"onclick", js, re.IGNORECASE)
        or re.search(r"on(keydown|keyup|keypress|mousedown|mouseup|touchstart)", js, re.IGNORECASE)
    )
    if has_events:
        checks += 1

    score = checks / total
    issues = []
    if js.count("{") != js.count("}"):
        issues.append(f"Unbalanced braces ({js.count('{')}/{js.count('}')})")
    if js.count("(") != js.count(")"):
        issues.append(f"Unbalanced parens ({js.count('(')}/{js.count(')')})")
    if not has_func:
        issues.append("No function definitions found")
    if not has_events:
        issues.append("No event listeners found")

    return QualityMetric(
        name="js_syntax",
        passed=score >= 0.75,
        score=score,
        detail="; ".join(issues) if issues else "JS structure OK",
    )


def _check_css_reference_integrity(html: str, css: str) -> QualityMetric:
    """Extract classes/IDs from HTML, check fraction have CSS rules."""
    if not html.strip() or not css.strip():
        return QualityMetric(
            name="css_reference_integrity",
            passed=False,
            score=0.0,
            detail="Empty HTML or CSS",
        )

    # Extract classes and IDs from HTML
    html_ids = set(re.findall(r'id=["\']([^"\']+)["\']', html))
    html_classes = set()
    for class_str in re.findall(r'class=["\']([^"\']+)["\']', html):
        html_classes.update(class_str.split())

    if not html_ids and not html_classes:
        return QualityMetric(
            name="css_reference_integrity",
            passed=True,
            score=1.0,
            detail="No classes/IDs in HTML to check",
        )

    # Check which ones have CSS rules
    matched = 0
    total = len(html_ids) + len(html_classes)

    for id_val in html_ids:
        if re.search(r"#" + re.escape(id_val) + r"\b", css):
            matched += 1
    for cls_val in html_classes:
        if re.search(r"\." + re.escape(cls_val) + r"\b", css):
            matched += 1

    score = matched / total if total > 0 else 1.0
    passed = score >= 0.3  # At least 30% of HTML refs have CSS rules

    return QualityMetric(
        name="css_reference_integrity",
        passed=passed,
        score=score,
        detail=f"{matched}/{total} HTML classes/IDs found in CSS",
    )


# ── Canvas Element Counting ──────────────────────────────────────────────────


def _count_canvas_elements(js: str) -> int:
    """Count distinct visual elements drawn on canvas in JS code.

    Heuristic: each fillStyle/strokeStyle assignment or drawImage/fillText call
    represents a visual element. Divides by 2 to account for loop duplication,
    capped at 20 to avoid inflation.
    """
    if not js.strip():
        return 0

    count = 0
    # Each fillStyle/strokeStyle assignment = potential element
    count += len(re.findall(r"(?:fillStyle|strokeStyle)\s*=", js))
    # Each drawImage call = 1 element
    count += len(re.findall(r"drawImage\s*\(", js))
    # Each fillText/strokeText call = 1 element
    count += len(re.findall(r"(?:fillText|strokeText)\s*\(", js))

    # Heuristic: divide by 2 for loop duplication, minimum 1 if any found
    adjusted = max(1, count // 2) if count > 0 else 0
    # Cap at 20 to avoid inflation
    return min(adjusted, 20)


# ── Layer 2: Wireframe Fidelity ─────────────────────────────────────────────


def _check_screen_coverage(html: str, wireframe: dict[str, Any]) -> QualityMetric:
    """Each wireframe interface_id has a <div id="{id}"> in HTML.

    Critical metric.
    """
    interfaces = wireframe.get("interfaces", [])
    if not interfaces:
        return QualityMetric(
            name="screen_coverage",
            passed=True,
            score=1.0,
            detail="No wireframe interfaces to check",
        )

    wf_ids = [iface.get("interface_id", "") for iface in interfaces]

    # Extract all IDs from HTML
    html_ids = set(re.findall(r'id=["\']([^"\']+)["\']', html))
    # Also check for data-screen attributes
    html_ids.update(re.findall(r'data-screen=["\']([^"\']+)["\']', html))

    matched = 0
    matched_ids = []
    for wf_id in wf_ids:
        # Exact match
        if wf_id in html_ids:
            matched += 1
            matched_ids.append(wf_id)
            continue
        # Fuzzy: check if any HTML ID contains the wireframe ID or vice versa
        fuzzy_hit = any(
            wf_id in hid or hid in wf_id
            for hid in html_ids
            if len(hid) > 2
        )
        if fuzzy_hit:
            matched += 1
            matched_ids.append(f"{wf_id}~")

    score = matched / len(wf_ids)
    passed = score >= 0.5

    return QualityMetric(
        name="screen_coverage",
        passed=passed,
        score=score,
        detail=f"{matched}/{len(wf_ids)} screens found [{', '.join(matched_ids)}]",
    )


def _check_element_coverage(
    html: str, wireframe: dict[str, Any], js: str = "",
) -> QualityMetric:
    """Per-screen: wireframe elements → HTML elements.

    Asymmetric penalty: 0.5x for over-generation.
    For screens with <canvas>, adds canvas-drawn element count from JS.
    """
    interfaces = wireframe.get("interfaces", [])
    if not interfaces:
        return QualityMetric(
            name="element_coverage",
            passed=True,
            score=1.0,
            detail="No wireframe interfaces",
        )

    elements = _extract_html_elements(html)

    # Group HTML elements by screen_id
    screen_elements: dict[str, list[dict]] = {}
    for el in elements:
        sid = el.get("screen_id", "")
        if sid:
            screen_elements.setdefault(sid, []).append(el)

    canvas_count = _count_canvas_elements(js) if js else 0

    scores = []
    details = []

    for iface in interfaces:
        iface_id = iface.get("interface_id", "")
        wf_elems = iface.get("elements", [])
        if not wf_elems:
            scores.append(1.0)
            continue

        # Find HTML elements for this screen
        # Try exact match first, then fuzzy
        screen_html = screen_elements.get(iface_id, [])
        if not screen_html:
            for sid, elems in screen_elements.items():
                if iface_id in sid or sid in iface_id:
                    screen_html = elems
                    break

        # Count child elements (exclude the screen div itself)
        screen_html_count = len([
            el for el in screen_html
            if el.get("id") != iface_id  # don't count the screen div itself
        ])

        # If screen has a <canvas>, add canvas-drawn elements from JS
        has_canvas = any(el.get("tag") == "canvas" for el in screen_html)
        if has_canvas and canvas_count > 0:
            screen_html_count += canvas_count

        # If no screen-specific elements found, fall back to total distribution
        gold_count = len(wf_elems)
        if not screen_html and len(elements) > 0:
            screen_html_count = len(elements) // max(len(interfaces), 1)

        if gold_count == 0:
            scores.append(1.0)
        elif screen_html_count <= gold_count:
            ratio = screen_html_count / gold_count
            scores.append(ratio)
        else:
            excess = screen_html_count - gold_count
            ratio = max(0.0, 1.0 - (excess / gold_count) * 0.5)
            scores.append(ratio)

        details.append(f"{iface_id}:{screen_html_count}/{gold_count}")

    avg_score = sum(scores) / len(scores) if scores else 0.0
    passed = avg_score >= 0.3

    return QualityMetric(
        name="element_coverage",
        passed=passed,
        score=avg_score,
        detail=" ".join(details),
    )


def _check_style_fidelity(
    css: str, html: str, wireframe: dict[str, Any],
) -> QualityMetric:
    """Wireframe colors/font-sizes appear in CSS. Normalize hex colors."""
    if not css.strip():
        return QualityMetric(
            name="style_fidelity",
            passed=False,
            score=0.0,
            detail="Empty CSS",
        )

    # Extract style values from wireframe
    wf_colors: set[str] = set()
    wf_font_sizes: set[str] = set()

    for iface in wireframe.get("interfaces", []):
        for elem in iface.get("elements", []):
            style = elem.get("style", {})
            if not isinstance(style, dict):
                continue
            for key, val in style.items():
                if not val:
                    continue
                val_str = str(val).strip().lower()
                # Extract colors
                if "color" in key.lower() or "background" in key.lower():
                    # Normalize hex colors to lowercase
                    color_match = re.findall(r"#[0-9a-fA-F]{3,8}", val_str)
                    wf_colors.update(c.lower() for c in color_match)
                    if not color_match and val_str not in ("", "none", "transparent"):
                        wf_colors.add(val_str)
                # Extract font sizes
                if "font-size" in key.lower() or "font_size" in key.lower():
                    wf_font_sizes.add(val_str)

    if not wf_colors and not wf_font_sizes:
        return QualityMetric(
            name="style_fidelity",
            passed=True,
            score=1.0,
            detail="No wireframe styles to check",
        )

    css_lower = css.lower()
    matched = 0
    total = len(wf_colors) + len(wf_font_sizes)

    for color in wf_colors:
        if color in css_lower:
            matched += 1
    for size in wf_font_sizes:
        # Normalize: "24px" or "24" → look for "24px"
        size_val = re.sub(r"[^0-9]", "", size)
        if size_val and re.search(r"\b" + re.escape(size_val) + r"px", css_lower):
            matched += 1

    score = matched / total if total > 0 else 1.0
    passed = score >= 0.3

    return QualityMetric(
        name="style_fidelity",
        passed=passed,
        score=score,
        detail=f"{matched}/{total} wireframe styles found in CSS "
        f"(colors={len(wf_colors)}, sizes={len(wf_font_sizes)})",
    )


def _check_navigation_integrity(
    html: str, js: str, wireframe: dict[str, Any],
) -> QualityMetric:
    """Wireframe button→target edges have JS handlers.

    Check that button ID + target screen ID co-occur in JS.
    """
    interfaces = wireframe.get("interfaces", [])
    if not interfaces:
        return QualityMetric(
            name="navigation_integrity",
            passed=True,
            score=1.0,
            detail="No wireframe interfaces",
        )

    # Extract navigation edges from wireframe
    nav_edges: list[tuple[str, str]] = []
    for iface in interfaces:
        iface_id = iface.get("interface_id", "")
        for child in iface.get("children", []):
            nav_edges.append((iface_id, child))
        for elem in iface.get("elements", []):
            target = elem.get("target_interface_id")
            if target and elem.get("event") == "click":
                nav_edges.append((iface_id, target))

    # Deduplicate
    nav_edges = list(set(nav_edges))

    if not nav_edges:
        return QualityMetric(
            name="navigation_integrity",
            passed=True,
            score=1.0,
            detail="No navigation edges in wireframe",
        )

    # Check if target screen IDs appear in JS (navigation handlers)
    js_combined = js + " " + html
    covered = 0
    for _from_id, to_id in nav_edges:
        # Check if the target screen ID appears in JS
        # Look for patterns like: showScreen('to_id'), getElementById('to_id'),
        # display = 'block', visibility, etc.
        if re.search(re.escape(to_id), js_combined, re.IGNORECASE):
            covered += 1

    score = covered / len(nav_edges)
    passed = score >= 0.4

    return QualityMetric(
        name="navigation_integrity",
        passed=passed,
        score=score,
        detail=f"{covered}/{len(nav_edges)} navigation edges have JS handlers",
    )


# ── Main Evaluation ─────────────────────────────────────────────────────────


def evaluate(
    html_content: str,
    css_content: str,
    js_content: str,
    wireframe: dict[str, Any],
) -> QualityReport:
    """Evaluate generated game code against wireframe spec.

    Args:
        html_content: Generated HTML string.
        css_content: Generated CSS string.
        js_content: Generated JS string.
        wireframe: Wireframe JSON dict (from golden sample).

    Returns:
        QualityReport with Layer 1 + Layer 2 metrics.
    """
    report = QualityReport()

    # Layer 1: Code Runnability
    report.metrics.append(_check_file_completeness(html_content, css_content, js_content))
    report.metrics.append(_check_html_validity(html_content))
    report.metrics.append(_check_js_syntax(js_content))
    report.metrics.append(_check_css_reference_integrity(html_content, css_content))

    # Layer 2: Wireframe Fidelity
    report.metrics.append(_check_screen_coverage(html_content, wireframe))
    report.metrics.append(_check_element_coverage(html_content, wireframe, js=js_content))
    report.metrics.append(_check_style_fidelity(css_content, html_content, wireframe))
    report.metrics.append(_check_navigation_integrity(html_content, js_content, wireframe))

    return report


# ── JS Summary Extraction ─────────────────────────────────────────────────


def _extract_js_summary(js: str, max_chars: int = 4000) -> str:
    """Extract a structural summary of JS code for LLM evaluation.

    Pulls out function signatures, canvas drawing calls, event listeners,
    and state variables so the LLM judge sees game structure rather than
    truncated raw code.
    """
    if not js.strip():
        return "(empty JS)"

    sections: list[str] = []

    # 1. Function signatures (named functions + arrow functions)
    func_names: list[str] = []
    # Named functions with first 2 lines of body
    func_pattern = re.compile(
        r"(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)\s*\{([^}]*)",
        re.DOTALL,
    )
    func_details: list[str] = []
    for m in func_pattern.finditer(js):
        name = m.group(1)
        params = m.group(2).strip()
        body_preview = m.group(3).strip().split("\n")[:2]
        body_str = " | ".join(line.strip() for line in body_preview if line.strip())
        func_names.append(name)

        # Check if function contains canvas calls
        func_body_start = m.start()
        # Find matching closing brace (simple heuristic: next 500 chars)
        func_body = js[func_body_start:func_body_start + 500]
        canvas_in_func = re.findall(
            r"ctx\.(fillRect|clearRect|strokeRect|fillText|strokeText|drawImage|arc|beginPath|moveTo|lineTo|stroke|fill)\b",
            func_body,
        )
        canvas_note = f" [canvas: {', '.join(set(canvas_in_func))}]" if canvas_in_func else ""
        func_details.append(f"- {name}({params}){canvas_note}: {body_str[:80]}")

    # Arrow function assignments
    arrow_pattern = re.compile(
        r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|(\w+))\s*=>"
    )
    for m in arrow_pattern.finditer(js):
        name = m.group(1)
        if name not in func_names:
            func_names.append(name)
            func_details.append(f"- {name} (arrow)")

    if func_details:
        sections.append(f"## Functions ({len(func_details)} total)\n" + "\n".join(func_details))

    # 2. Canvas drawing calls grouped by context
    canvas_calls = re.findall(
        r"ctx\.(fillRect|clearRect|strokeRect|fillText|strokeText|drawImage|arc|beginPath|moveTo|lineTo|stroke|fill)\b",
        js,
    )
    if canvas_calls:
        unique_calls = sorted(set(canvas_calls))
        sections.append(f"## Canvas Calls\n{', '.join(unique_calls)}")

    # 3. Event listeners
    event_types: list[str] = []
    for m in re.finditer(r"addEventListener\s*\(\s*['\"](\w+)['\"]", js):
        event_types.append(m.group(1))
    if event_types:
        sections.append(f"## Event Listeners\n{', '.join(sorted(set(event_types)))}")

    # 4. State variables (top-level let/var/const declarations)
    state_vars: list[str] = []
    for m in re.finditer(
        r"^(?:let|var|const)\s+(\w+)\s*=\s*(.+?);\s*$",
        js,
        re.MULTILINE,
    ):
        name = m.group(1)
        value = m.group(2).strip()[:60]
        state_vars.append(f"{name} = {value}")
    if state_vars:
        sections.append(f"## State Variables\n{', '.join(state_vars)}")

    summary = "\n\n".join(sections)

    # Fallback: if summary is too short, use raw JS
    if len(summary) < 200:
        summary = js[:max_chars]

    return summary[:max_chars]


# ── Layer 3: LLM-as-Judge ────────────────────────────────────────────────────


def semantic_evaluate(
    html: str,
    css: str,
    js: str,
    wireframe: dict[str, Any],
    prd_document: str,
    api_key: str,
    model: str = "claude-sonnet-4-20250514",
) -> QualityMetric:
    """LLM judge evaluating game code quality.

    Scores 3 dimensions (0-10 each):
    - mechanics_completeness: PRD game rules implemented in JS?
    - state_management: Game states (menu→playing→game_over) handled?
    - interaction_quality: Input handlers correct for game type?

    Combined score: sum / 30.0. Pass threshold: score >= 0.6 AND mechanics >= 6.
    """
    kwargs: dict = {"api_key": api_key}
    if api_key.startswith("sk-or-"):
        kwargs["base_url"] = "https://openrouter.ai/api"
    client = anthropic.Anthropic(**kwargs)

    # Summarize wireframe for context
    wf_screens = []
    for iface in wireframe.get("interfaces", []):
        iid = iface.get("interface_id", "?")
        elems = len(iface.get("elements", []))
        children = iface.get("children", [])
        wf_screens.append(f"  [{iid}] {elems} elements, nav→{children}")
    wf_summary = "\n".join(wf_screens)

    js_summary = _extract_js_summary(js)

    response = client.messages.create(
        model=model,
        max_tokens=1024,
        temperature=0.0,
        system=(
            "You are a game code quality evaluator. Given game code (HTML/CSS/JS), "
            "a wireframe spec, and a PRD, evaluate the implementation quality.\n"
            "The JS is provided as a structural summary showing functions, canvas calls, "
            "event listeners, and state variables.\n"
            "Score on 3 dimensions (each 0-10):\n"
            "1. mechanics_completeness: Are the PRD's game rules implemented in JS?\n"
            "2. state_management: Are game states (menu→playing→game_over) properly handled?\n"
            "3. interaction_quality: Are input handlers correct for the game type?\n\n"
            "Return ONLY valid JSON."
        ),
        messages=[
            {
                "role": "user",
                "content": (
                    f"## PRD\n{prd_document[:3000]}\n\n"
                    f"## Wireframe Screens\n{wf_summary}\n\n"
                    f"## HTML (first 3000 chars)\n```html\n{html[:3000]}\n```\n\n"
                    f"## CSS (first 2000 chars)\n```css\n{css[:2000]}\n```\n\n"
                    f"## JS (structural summary)\n```\n{js_summary}\n```\n\n"
                    "Score JSON:\n"
                    '{"mechanics_completeness": <0-10>, "state_management": <0-10>, '
                    '"interaction_quality": <0-10>, "issues": ["<list any problems>"]}'
                ),
            }
        ],
    )

    raw = response.content[0].text
    try:
        start = raw.find("{")
        last = raw.rfind("}")
        if start != -1 and last != -1:
            raw = raw[start : last + 1]
        parsed = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return QualityMetric(
            name="semantic",
            passed=False,
            score=0.0,
            detail="LLM judge response parsing failed",
        )

    mechanics = parsed.get("mechanics_completeness", 5)
    state_mgmt = parsed.get("state_management", 5)
    interaction = parsed.get("interaction_quality", 5)
    issues = parsed.get("issues", [])

    score = (mechanics + state_mgmt + interaction) / 30.0
    passed = score >= 0.6 and mechanics >= 6
    detail = (
        f"mechanics={mechanics}/10 state={state_mgmt}/10 interaction={interaction}/10"
        + (f" issues={issues}" if issues else "")
    )

    return QualityMetric(name="semantic", passed=passed, score=score, detail=detail)
