"""PRD Quality Evaluation: Automated metrics for PRD completeness, faithfulness, and specificity.

Evaluates generated PRDs against quality criteria derived from iterative testing.
Works with any PRD output from OneSentencePrd or PrdGenerator.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from intention_graph.one_sentence_prd import _COMPLEXITY_PROFILES


# ── Banned phrases from _PRD_SYSTEM_PROMPT ───────────────────────────────────

_BANNED_PHRASES = [
    "synergize", "synergizes", "synergy",
    "directly influences", "feeds into",
    "gating", "essential for progression",
    "ensures", "complements", "reinforces",
    "integrates with",
]

# Over-design indicators: systems that arcade games should NOT have
_ARCADE_BANNED_SYSTEMS = [
    "技能树", "天赋系统", "装备系统", "背包系统",
    "skill tree", "talent system", "equipment system", "inventory",
    "gacha", "battle pass", "赛季通行证",
]


@dataclass
class QualityMetric:
    """A single quality metric result."""
    name: str
    passed: bool
    score: float  # 0.0 to 1.0
    detail: str = ""


@dataclass
class QualityReport:
    """Full quality evaluation report for a PRD."""
    metrics: list[QualityMetric] = field(default_factory=list)

    @property
    def overall_score(self) -> float:
        """Weighted average of all metric scores."""
        if not self.metrics:
            return 0.0
        return sum(m.score for m in self.metrics) / len(self.metrics)

    @property
    def passed(self) -> bool:
        """True if all critical metrics pass."""
        critical = ["completeness", "banned_phrases", "inferred_accuracy"]
        for m in self.metrics:
            if m.name in critical and not m.passed:
                return False
        return True

    @property
    def failures(self) -> list[QualityMetric]:
        """List of failed metrics."""
        return [m for m in self.metrics if not m.passed]

    def summary(self) -> str:
        """Human-readable summary."""
        lines = [f"Overall: {self.overall_score:.0%} ({len(self.failures)} failures)"]
        for m in self.metrics:
            status = "PASS" if m.passed else "FAIL"
            lines.append(f"  [{status}] {m.name}: {m.score:.0%} — {m.detail}")
        return "\n".join(lines)


def evaluate_batch(
    results: list[dict[str, Any]],
) -> list[tuple[str, QualityReport]]:
    """Evaluate multiple PRD results and return named reports.

    Args:
        results: List of dicts, each with keys:
            "name" (str), "prd_document" (str), "metadata" (dict)

    Returns:
        List of (name, QualityReport) tuples
    """
    reports = []
    for r in results:
        name = r.get("name", r["metadata"].get("detected_game", "unknown"))
        report = evaluate(r["prd_document"], r["metadata"])
        reports.append((name, report))
    return reports


def batch_summary(reports: list[tuple[str, QualityReport]]) -> str:
    """Aggregate summary of multiple PRD quality reports."""
    lines = []
    total_score = 0
    total_passed = 0

    for name, report in reports:
        status = "PASS" if report.passed else "FAIL"
        lines.append(f"  [{status}] {name}: {report.overall_score:.0%}")
        total_score += report.overall_score
        if report.passed:
            total_passed += 1

        for f in report.failures:
            lines.append(f"         - {f.name}: {f.detail}")

    avg = total_score / len(reports) if reports else 0
    lines.insert(0, f"Batch: {total_passed}/{len(reports)} passed, avg score {avg:.0%}")
    return "\n".join(lines)


def evaluate(
    prd_document: str,
    metadata: dict[str, Any],
) -> QualityReport:
    """Evaluate a PRD document against quality criteria.

    Args:
        prd_document: The PRD text (markdown)
        metadata: The metadata dict from OneSentencePrd.generate()

    Returns:
        QualityReport with detailed metrics
    """
    report = QualityReport()

    complexity = metadata.get("complexity", "mid-core")
    profile = _COMPLEXITY_PROFILES.get(complexity, _COMPLEXITY_PROFILES["mid-core"])
    core_systems = metadata.get("core_systems", [])

    report.metrics.append(_check_completeness(prd_document))
    report.metrics.append(_check_length(prd_document, profile))
    report.metrics.append(_check_system_count(prd_document, profile))
    report.metrics.append(_check_inferred_accuracy(prd_document, core_systems))
    report.metrics.append(_check_banned_phrases(prd_document))
    report.metrics.append(_check_faithfulness(prd_document, complexity))
    report.metrics.append(_check_specificity(prd_document))
    report.metrics.append(_check_design_questions(prd_document))

    return report


# ── Individual metric checkers ───────────────────────────────────────────────


def _check_completeness(doc: str) -> QualityMetric:
    """Check all 4 mandatory sections are present."""
    sections = [
        ("游戏总览", "## 1"),
        ("核心游戏循环", "## 2"),
        ("游戏系统", "## 3"),
        ("美术与音效风格", "## 4"),
    ]
    found = []
    missing = []
    for name, prefix in sections:
        if name in doc:
            found.append(name)
        else:
            missing.append(name)

    score = len(found) / len(sections)
    passed = len(missing) == 0
    detail = f"{len(found)}/4 sections" + (f" (missing: {missing})" if missing else "")

    return QualityMetric(name="completeness", passed=passed, score=score, detail=detail)


def _check_length(doc: str, profile: dict) -> QualityMetric:
    """Check PRD meets minimum character length."""
    min_chars = profile.get("min_prd_chars", 5000)
    actual = len(doc)
    score = min(1.0, actual / min_chars)
    passed = actual >= min_chars
    detail = f"{actual} chars (min: {min_chars})"

    return QualityMetric(name="length", passed=passed, score=score, detail=detail)


def _check_system_count(doc: str, profile: dict) -> QualityMetric:
    """Check number of game systems in Section 3."""
    max_systems = profile.get("max_systems", 8)

    # Extract section 3
    section3_match = re.search(r"## 3\. 游戏系统(.*?)## 4\. 美术", doc, re.DOTALL)
    if not section3_match:
        return QualityMetric(
            name="system_count", passed=False, score=0.0,
            detail="Could not find Section 3"
        )

    section3 = section3_match.group(1)
    sys_headers = re.findall(r"### (.+)", section3)
    actual = len(sys_headers)

    # Allow ±1 from target
    target = max_systems
    diff = abs(actual - target)
    if diff == 0:
        score = 1.0
    elif diff == 1:
        score = 0.8
    elif diff == 2:
        score = 0.5
    else:
        score = 0.2

    passed = diff <= 2
    detail = f"{actual} systems (target: {target})"

    return QualityMetric(name="system_count", passed=passed, score=score, detail=detail)


def _check_inferred_accuracy(doc: str, core_systems: list[str]) -> QualityMetric:
    """Check that no core systems are falsely marked [INFERRED]."""
    # Find all [INFERRED] system headers
    section3_match = re.search(r"## 3\. 游戏系统(.*?)## 4\. 美术", doc, re.DOTALL)
    if not section3_match:
        return QualityMetric(
            name="inferred_accuracy", passed=True, score=1.0,
            detail="No Section 3 found (skip)"
        )

    section3 = section3_match.group(1)
    inferred_headers = re.findall(r"### (.+\[INFERRED\].*)", section3)

    # Check if any inferred system matches a core system
    false_positives = []
    for header in inferred_headers:
        header_clean = header.replace("[INFERRED]", "").strip()
        for core in core_systems:
            # Fuzzy match: core system name is substring of header
            if core.lower() in header_clean.lower() or header_clean.lower() in core.lower():
                false_positives.append(f"{header_clean} ← matches core '{core}'")
                break

    total_inferred = len(inferred_headers)
    false_positive_count = len(false_positives)

    if total_inferred == 0:
        score = 1.0
        passed = True
        detail = "0 [INFERRED] tags"
    elif false_positive_count == 0:
        score = 1.0
        passed = True
        detail = f"{total_inferred} [INFERRED] (all legitimate)"
    else:
        score = 1.0 - (false_positive_count / max(total_inferred, 1))
        passed = False
        detail = f"{false_positive_count} false positives: {false_positives}"

    return QualityMetric(name="inferred_accuracy", passed=passed, score=score, detail=detail)


def _check_banned_phrases(doc: str) -> QualityMetric:
    """Check for banned technical jargon."""
    doc_lower = doc.lower()
    found = [phrase for phrase in _BANNED_PHRASES if phrase in doc_lower]

    score = 1.0 if not found else max(0.0, 1.0 - len(found) * 0.2)
    passed = len(found) == 0
    detail = f"Found: {found}" if found else "No banned phrases"

    return QualityMetric(name="banned_phrases", passed=passed, score=score, detail=detail)


def _check_faithfulness(doc: str, complexity: str) -> QualityMetric:
    """Check for over-design (arcade games shouldn't have complex systems)."""
    if complexity != "arcade":
        return QualityMetric(
            name="faithfulness", passed=True, score=1.0,
            detail=f"Non-arcade ({complexity}): skip over-design check"
        )

    doc_lower = doc.lower()
    violations = [
        term for term in _ARCADE_BANNED_SYSTEMS
        if term.lower() in doc_lower and "[INFERRED]" not in doc
    ]

    score = 1.0 if not violations else max(0.0, 1.0 - len(violations) * 0.25)
    passed = len(violations) == 0
    detail = f"Over-design: {violations}" if violations else "Faithful to arcade design"

    return QualityMetric(name="faithfulness", passed=passed, score=score, detail=detail)


def _check_specificity(doc: str) -> QualityMetric:
    """Check for concrete numbers and specific details."""
    # Look for numbers (indicates specific design values)
    numbers = re.findall(r"\d+", doc)
    # Look for concrete gameplay moments (player-facing language)
    action_phrases = len(re.findall(
        r"你[会将要能用按看感移]|你的|玩家|每秒|每次|每关",
        doc,
    ))

    # Scoring: more numbers and action phrases = more specific
    number_score = min(1.0, len(numbers) / 30)  # expect ~30 numbers
    action_score = min(1.0, action_phrases / 15)  # expect ~15 player references

    score = (number_score + action_score) / 2
    passed = score >= 0.4
    detail = f"{len(numbers)} numbers, {action_phrases} player references"

    return QualityMetric(name="specificity", passed=passed, score=score, detail=detail)


def _check_design_questions(doc: str) -> QualityMetric:
    """Check that 设计考量 sections contain actual questions (? or ？)."""
    # Find all 设计考量 blocks
    design_blocks = re.findall(
        r"\*\*设计考量\*\*[：:]\s*(.*?)(?=\*\*|###|$)",
        doc,
        re.DOTALL,
    )

    if not design_blocks:
        return QualityMetric(
            name="design_questions", passed=False, score=0.0,
            detail="No 设计考量 sections found"
        )

    blocks_with_question = sum(
        1 for block in design_blocks
        if "?" in block or "？" in block
    )

    score = blocks_with_question / len(design_blocks)
    passed = score >= 0.8  # at least 80% should have questions
    detail = f"{blocks_with_question}/{len(design_blocks)} have questions"

    return QualityMetric(name="design_questions", passed=passed, score=score, detail=detail)
