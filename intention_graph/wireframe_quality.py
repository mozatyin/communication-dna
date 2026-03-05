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


def _check_screen_coverage(gen: dict, gold: dict) -> QualityMetric:
    """Jaccard similarity of screen IDs."""
    gen_ids = {i["interface_id"] for i in gen.get("interfaces", [])}
    gold_ids = {i["interface_id"] for i in gold.get("interfaces", [])}

    if not gold_ids:
        return QualityMetric(
            name="screen_coverage", passed=True, score=1.0,
            detail="No golden screens to compare"
        )

    intersection = gen_ids & gold_ids
    union = gen_ids | gold_ids
    jaccard = len(intersection) / len(union) if union else 0.0

    # Also check count similarity
    count_ratio = min(len(gen_ids), len(gold_ids)) / max(len(gen_ids), len(gold_ids)) if gold_ids else 0.0

    score = (jaccard + count_ratio) / 2
    passed = score >= 0.5
    detail = (
        f"gen={sorted(gen_ids)} gold={sorted(gold_ids)} "
        f"overlap={sorted(intersection)} jaccard={jaccard:.2f}"
    )

    return QualityMetric(name="screen_coverage", passed=passed, score=score, detail=detail)


def _check_element_coverage(gen: dict, gold: dict) -> QualityMetric:
    """Per-screen element count similarity."""
    gen_screens = {i["interface_id"]: i for i in gen.get("interfaces", [])}
    gold_screens = {i["interface_id"]: i for i in gold.get("interfaces", [])}

    shared = set(gen_screens.keys()) & set(gold_screens.keys())
    if not shared:
        # No shared screens — compare total element counts
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
            detail=f"gen={gen_total} gold={gold_total} elements (no shared screens)"
        )

    scores = []
    details = []
    for sid in shared:
        gen_count = len(gen_screens[sid].get("elements", []))
        gold_count = len(gold_screens[sid].get("elements", []))
        if gold_count == 0:
            scores.append(1.0)
        else:
            ratio = min(gen_count, gold_count) / max(gen_count, gold_count)
            scores.append(ratio)
        details.append(f"{sid}:{gen_count}/{gold_count}")

    avg_score = sum(scores) / len(scores)
    passed = avg_score >= 0.5
    detail = f"{' '.join(details)} avg={avg_score:.2f}"

    return QualityMetric(name="element_coverage", passed=passed, score=avg_score, detail=detail)


def _check_navigation_accuracy(gen: dict, gold: dict) -> QualityMetric:
    """F1 score of navigation edges (parent→child)."""
    gen_edges = _extract_nav_edges(gen)
    gold_edges = _extract_nav_edges(gold)

    if not gold_edges:
        return QualityMetric(
            name="navigation_accuracy", passed=True, score=1.0,
            detail="No golden nav edges"
        )

    true_positives = gen_edges & gold_edges
    precision = len(true_positives) / len(gen_edges) if gen_edges else 0.0
    recall = len(true_positives) / len(gold_edges) if gold_edges else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    passed = f1 >= 0.5
    detail = f"P={precision:.2f} R={recall:.2f} F1={f1:.2f} gen={len(gen_edges)} gold={len(gold_edges)}"

    return QualityMetric(name="navigation_accuracy", passed=passed, score=f1, detail=detail)


def _extract_nav_edges(wireframe: dict) -> set[tuple[str, str]]:
    """Extract navigation edges from wireframe."""
    edges = set()
    for iface in wireframe.get("interfaces", []):
        iface_id = iface.get("interface_id", "")
        for child in iface.get("children", []):
            edges.add((iface_id, child))
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
        has_bg = any(
            e.get("type") in ("image", "css") and e.get("rect", {}).get("z_index", 99) == 0
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
