"""Wireframe Quality Evaluation: PDCA Check phase.

Compares generated wireframes against golden samples using:
1. Structural metrics (screen coverage, element types, navigation graph)
2. LLM-as-judge semantic evaluation (faithfulness, UX quality, completeness)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import anthropic


@dataclass
class QualityMetric:
    """A single quality metric result."""
    name: str
    passed: bool
    score: float  # 0.0 to 1.0
    detail: str = ""


@dataclass
class QualityReport:
    """Full quality evaluation report for a wireframe."""
    metrics: list[QualityMetric] = field(default_factory=list)

    @property
    def overall_score(self) -> float:
        if not self.metrics:
            return 0.0
        return sum(m.score for m in self.metrics) / len(self.metrics)

    @property
    def passed(self) -> bool:
        critical = ["screen_coverage", "navigation_accuracy"]
        for m in self.metrics:
            if m.name in critical and not m.passed:
                return False
        return True

    @property
    def failures(self) -> list[QualityMetric]:
        return [m for m in self.metrics if not m.passed]

    def summary(self) -> str:
        lines = [f"Overall: {self.overall_score:.0%} ({len(self.failures)} failures)"]
        for m in self.metrics:
            status = "PASS" if m.passed else "FAIL"
            lines.append(f"  [{status}] {m.name}: {m.score:.0%} — {m.detail}")
        return "\n".join(lines)


# ── Structural Evaluation ────────────────────────────────────────────────────


def evaluate(
    generated: dict[str, Any],
    golden: dict[str, Any],
) -> QualityReport:
    """Compare generated wireframe against golden sample.

    Args:
        generated: Generated wireframe.json dict.
        golden: Golden sample wireframe.json dict.

    Returns:
        QualityReport with detailed metrics.
    """
    report = QualityReport()

    report.metrics.append(_check_screen_coverage(generated, golden))
    report.metrics.append(_check_element_coverage(generated, golden))
    report.metrics.append(_check_navigation_accuracy(generated, golden))
    report.metrics.append(_check_layout_completeness(generated))
    report.metrics.append(_check_element_types(generated))

    return report


_SYNONYM_GROUPS = [
    {"main", "menu", "start", "home", "title", "entry", "launch"},
    {"gameplay", "play", "playing"},
    {"level", "stage", "world", "map"},
    {"over", "end", "result", "finish", "death", "fail", "lose", "complete",
     "win", "victory", "success", "clear"},
    {"pause", "stop", "suspend"},
    {"setting", "config", "option", "preference"},
    {"leader", "score", "board", "rank", "high"},
    {"shop", "store", "buy", "purchase"},
    {"inventory", "bag", "item", "equip"},
    {"select", "choose", "pick", "preparation", "loadout"},
]


def _match_screens(
    gen: dict, gold: dict,
) -> list[tuple[dict, dict]]:
    """Match generated screens to golden screens by name/type similarity.

    Two-pass approach: exact ID matches first, then fuzzy matching.
    Returns list of (gen_screen, gold_screen) pairs.
    """
    gen_screens = gen.get("interfaces", [])
    gold_screens = gold.get("interfaces", [])
    matched = []
    used_gold = set()
    used_gen = set()

    # Pass 1: exact ID matches (highest confidence)
    for gi, gs in enumerate(gen_screens):
        gid = gs.get("interface_id", "").lower()
        for ri, rs in enumerate(gold_screens):
            if ri in used_gold:
                continue
            if gid == rs.get("interface_id", "").lower():
                matched.append((gs, rs))
                used_gold.add(ri)
                used_gen.add(gi)
                break

    # Pass 2: fuzzy matching on remaining screens
    for gi, gs in enumerate(gen_screens):
        if gi in used_gen:
            continue
        gid = gs.get("interface_id", "").lower()
        gname = gs.get("interface_name", "").lower()
        gtype = gs.get("type", "page")

        best_match = None
        best_score = 0

        for i, golds in enumerate(gold_screens):
            if i in used_gold:
                continue
            gold_id = golds.get("interface_id", "").lower()
            gold_name = golds.get("interface_name", "").lower()
            gold_type = golds.get("type", "page")

            score = 0
            # ID substring
            if gid in gold_id or gold_id in gid:
                score += 2

            # Synonym group matching — screens with same role
            combined = f"{gid} {gname}"
            gold_combined = f"{gold_id} {gold_name}"
            for group in _SYNONYM_GROUPS:
                gen_hits = {w for w in group if w in combined}
                gold_hits = {w for w in group if w in gold_combined}
                if gen_hits and gold_hits:
                    score += 1.5
                    break

            # Same type
            if gtype == gold_type:
                score += 0.5
            # Name overlap (Chinese chars)
            name_overlap = sum(1 for c in gname if c in gold_name)
            score += min(1.0, name_overlap / max(len(gold_name), 1) * 2)

            if score > best_score:
                best_score = score
                best_match = i

        if best_match is not None and best_score >= 1.5:
            matched.append((gs, gold_screens[best_match]))
            used_gold.add(best_match)

    return matched


def _check_screen_coverage(gen: dict, gold: dict) -> QualityMetric:
    """Screen coverage using fuzzy matching (not exact ID)."""
    gen_screens = gen.get("interfaces", [])
    gold_screens = gold.get("interfaces", [])

    if not gold_screens:
        return QualityMetric(
            name="screen_coverage", passed=True, score=1.0,
            detail="No golden screens to compare"
        )

    matched = _match_screens(gen, gold)
    match_ratio = len(matched) / max(len(gold_screens), 1)
    count_ratio = min(len(gen_screens), len(gold_screens)) / max(len(gen_screens), len(gold_screens))

    score = (match_ratio * 2 + count_ratio) / 3
    passed = score >= 0.5

    match_detail = ", ".join(
        f"{g.get('interface_id')}↔{r.get('interface_id')}"
        for g, r in matched
    )
    detail = (
        f"{len(matched)}/{len(gold_screens)} matched "
        f"(gen={len(gen_screens)} gold={len(gold_screens)}) "
        f"[{match_detail}]"
    )

    return QualityMetric(name="screen_coverage", passed=passed, score=score, detail=detail)


def _check_element_coverage(gen: dict, gold: dict) -> QualityMetric:
    """Per-screen element count similarity using fuzzy-matched screens."""
    matched = _match_screens(gen, gold)

    if not matched:
        gen_total = sum(len(i.get("elements", [])) for i in gen.get("interfaces", []))
        gold_total = sum(len(i.get("elements", [])) for i in gold.get("interfaces", []))
        if gold_total == 0:
            return QualityMetric(
                name="element_coverage", passed=True, score=1.0,
                detail="No golden elements"
            )
        ratio = min(gen_total, gold_total) / max(gen_total, gold_total)
        return QualityMetric(
            name="element_coverage", passed=ratio >= 0.4,
            score=ratio,
            detail=f"gen={gen_total} gold={gold_total} elements (no matched screens)"
        )

    scores = []
    details = []
    for gen_s, gold_s in matched:
        gen_count = len(gen_s.get("elements", []))
        gold_count = len(gold_s.get("elements", []))
        if gold_count == 0:
            scores.append(1.0)
        else:
            ratio = min(gen_count, gold_count) / max(gen_count, gold_count)
            scores.append(ratio)
        details.append(f"{gen_s.get('interface_id')}:{gen_count}/{gold_count}")

    avg_score = sum(scores) / len(scores)
    passed = avg_score >= 0.5
    detail = f"{' '.join(details)} avg={avg_score:.2f}"

    return QualityMetric(name="element_coverage", passed=passed, score=avg_score, detail=detail)


def _check_navigation_accuracy(gen: dict, gold: dict) -> QualityMetric:
    """Navigation accuracy using fuzzy-matched screen IDs.

    Compares navigation edge count similarity and structure rather than
    exact ID matching, since generated IDs often differ from golden.
    """
    matched = _match_screens(gen, gold)
    if not matched:
        # Fallback: compare edge count
        gen_edges = _extract_nav_edges(gen)
        gold_edges = _extract_nav_edges(gold)
        if not gold_edges:
            return QualityMetric(
                name="navigation_accuracy", passed=True, score=1.0,
                detail="No golden nav edges"
            )
        ratio = min(len(gen_edges), len(gold_edges)) / max(len(gen_edges), len(gold_edges))
        return QualityMetric(
            name="navigation_accuracy", passed=ratio >= 0.5,
            score=ratio,
            detail=f"gen={len(gen_edges)} gold={len(gold_edges)} edges (no matched screens)"
        )

    # Build ID mapping: gold_id → gen_id
    id_map = {g.get("interface_id"): r.get("interface_id") for g, r in matched}
    reverse_map = {v: k for k, v in id_map.items()}

    gen_edges = _extract_nav_edges(gen)
    gold_edges = _extract_nav_edges(gold)

    # Build mapping: gen_id → gold_id
    gen_to_gold = {g.get("interface_id"): r.get("interface_id") for g, r in matched}
    gold_to_gen = {v: k for k, v in gen_to_gold.items()}

    # For each golden edge, check if equivalent exists in generated
    gold_covered = 0
    for from_id, to_id in gold_edges:
        gen_from = gold_to_gen.get(from_id)
        gen_to = gold_to_gen.get(to_id)
        if gen_from and gen_to and (gen_from, gen_to) in gen_edges:
            gold_covered += 1

    recall = gold_covered / len(gold_edges) if gold_edges else 1.0
    count_ratio = min(len(gen_edges), len(gold_edges)) / max(len(gen_edges), len(gold_edges)) if gold_edges else 1.0

    # Score weighted toward recall (covering golden edges matters most)
    score = recall * 0.7 + count_ratio * 0.3
    passed = score >= 0.4
    detail = (
        f"gold_covered={gold_covered}/{len(gold_edges)} "
        f"gen={len(gen_edges)} gold={len(gold_edges)} "
        f"matched_screens={len(matched)}"
    )

    return QualityMetric(name="navigation_accuracy", passed=passed, score=score, detail=detail)


def _extract_nav_edges(wireframe: dict) -> set[tuple[str, str]]:
    """Extract navigation edges from wireframe."""
    edges = set()
    for iface in wireframe.get("interfaces", []):
        iface_id = iface.get("interface_id", "")
        for child in iface.get("children", []):
            edges.add((iface_id, child))
        # Reverse edges from parents
        for parent in iface.get("parents", []):
            edges.add((parent, iface_id))
        # Also check button targets
        for elem in iface.get("elements", []):
            target = elem.get("target_interface_id")
            if target and elem.get("event") == "click":
                edges.add((iface_id, target))
    return edges


def _check_layout_completeness(gen: dict) -> QualityMetric:
    """Check that every screen has at least a background + one interactive element."""
    interfaces = gen.get("interfaces", [])
    if not interfaces:
        return QualityMetric(
            name="layout_completeness", passed=False, score=0.0,
            detail="No interfaces"
        )

    complete = 0
    for iface in interfaces:
        elements = iface.get("elements", [])
        is_popup = iface.get("type") == "popup"
        has_bg = any(
            e.get("type") in ("image", "css") and e.get("rect", {}).get("z_index", 99) == 0
            for e in elements
        )
        # Popups: a css panel at any z_index counts as background
        if not has_bg and is_popup:
            has_bg = any(
                e.get("type") == "css"
                for e in elements
            )
        has_interactive = any(
            e.get("event") or e.get("type") == "button"
            for e in elements
        )
        has_content = any(
            e.get("type") in ("text", "button") and e.get("inner_text")
            for e in elements
        )
        if has_bg and (has_interactive or has_content):
            complete += 1

    score = complete / len(interfaces)
    passed = score >= 0.8
    detail = f"{complete}/{len(interfaces)} screens complete"

    return QualityMetric(name="layout_completeness", passed=passed, score=score, detail=detail)


def _check_element_types(gen: dict) -> QualityMetric:
    """Check diversity of element types (should have image, text, button)."""
    all_types = set()
    for iface in gen.get("interfaces", []):
        for elem in iface.get("elements", []):
            all_types.add(elem.get("type", ""))

    expected = {"image", "text", "button"}
    present = all_types & expected
    score = len(present) / len(expected)
    passed = score >= 0.66  # at least 2 of 3
    detail = f"types={sorted(all_types)} expected={sorted(expected)}"

    return QualityMetric(name="element_types", passed=passed, score=score, detail=detail)


# ── LLM-as-Judge Semantic Evaluation ─────────────────────────────────────────


def semantic_evaluate(
    generated: dict[str, Any],
    golden: dict[str, Any],
    prd_document: str,
    api_key: str,
    model: str = "claude-sonnet-4-20250514",
) -> QualityMetric:
    """LLM judge comparing generated wireframe to golden sample.

    Scores 3 dimensions (0-10 each):
    - faithfulness: Does wireframe reflect PRD's described features?
    - ux_quality: Is layout intuitive, following UX best practices?
    - completeness: Are all key screens and elements present?
    """
    kwargs: dict = {"api_key": api_key}
    if api_key.startswith("sk-or-"):
        kwargs["base_url"] = "https://openrouter.ai/api"
    client = anthropic.Anthropic(**kwargs)

    gen_summary = _wireframe_summary(generated)
    gold_summary = _wireframe_summary(golden)

    response = client.messages.create(
        model=model,
        max_tokens=1024,
        temperature=0.0,
        system=(
            "You are a UI/UX quality evaluator. Compare a generated wireframe "
            "against a golden sample wireframe.\n"
            "Score on 3 dimensions (each 0-10):\n"
            "1. faithfulness: Does the generated wireframe match the PRD's features?\n"
            "2. ux_quality: Is the layout intuitive and well-organized?\n"
            "3. completeness: Are all key screens and elements present?\n\n"
            "Return ONLY valid JSON."
        ),
        messages=[{"role": "user", "content": (
            f"## PRD\n{prd_document[:3000]}\n\n"
            f"## Generated Wireframe\n{gen_summary}\n\n"
            f"## Golden Sample Wireframe\n{gold_summary}\n\n"
            "Score JSON:\n"
            '{"faithfulness": <0-10>, "ux_quality": <0-10>, "completeness": <0-10>, '
            '"issues": ["<list any problems>"]}'
        )}],
    )

    raw = response.content[0].text
    try:
        start = raw.find("{")
        last = raw.rfind("}")
        if start != -1 and last != -1:
            raw = raw[start:last + 1]
        parsed = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return QualityMetric(
            name="semantic", passed=False, score=0.0,
            detail="LLM judge response parsing failed"
        )

    faithfulness = parsed.get("faithfulness", 5)
    ux_quality = parsed.get("ux_quality", 5)
    completeness = parsed.get("completeness", 5)
    issues = parsed.get("issues", [])

    score = (faithfulness + ux_quality + completeness) / 30.0
    passed = score >= 0.6 and faithfulness >= 6
    detail = (
        f"faith={faithfulness}/10 ux={ux_quality}/10 comp={completeness}/10"
        + (f" issues={issues}" if issues else "")
    )

    return QualityMetric(name="semantic", passed=passed, score=score, detail=detail)


def _wireframe_summary(wireframe: dict) -> str:
    """Produce a concise text summary of a wireframe for LLM evaluation."""
    lines = []
    title = wireframe.get("project", {}).get("title", "Unknown")
    lines.append(f"Product: {title}")

    interfaces = wireframe.get("interfaces", [])
    lines.append(f"Screens: {len(interfaces)}")

    for iface in interfaces:
        iid = iface.get("interface_id", "?")
        iname = iface.get("interface_name", "?")
        itype = iface.get("type", "page")
        elements = iface.get("elements", [])
        children = iface.get("children", [])

        elem_types = {}
        for e in elements:
            t = e.get("type", "?")
            elem_types[t] = elem_types.get(t, 0) + 1

        lines.append(
            f"  [{iid}] {iname} ({itype}) — "
            f"{len(elements)} elements {dict(elem_types)}, "
            f"nav→{children}"
        )

    return "\n".join(lines)
