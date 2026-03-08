"""Lightweight static validation for generated module code."""

from __future__ import annotations

from dataclasses import dataclass, field

from intention_graph.modular_code_gen.models import ModuleCode, ModuleInterface


@dataclass
class ModuleValidationResult:
    is_valid: bool
    issues: list[str] = field(default_factory=list)


def validate_module(
    code: ModuleCode, interface: ModuleInterface
) -> ModuleValidationResult:
    """Run lightweight static checks on generated module code.

    Checks:
    1. Balanced braces/parens
    2. Each export function name appears in code
    3. IIFE namespace wrapper pattern present
    4. Not empty / not trivially short (<50 chars)
    """
    issues: list[str] = []
    js = code.js_code

    # Check 1: not empty / not trivially short
    if len(js.strip()) < 50:
        issues.append(f"Code too short ({len(js.strip())} chars, min 50)")

    # Check 2: balanced braces
    if js.count("{") != js.count("}"):
        issues.append(
            f"Unbalanced braces: {js.count('{')} open vs {js.count('}')} close"
        )

    # Check 3: balanced parens
    if js.count("(") != js.count(")"):
        issues.append(
            f"Unbalanced parens: {js.count('(')} open vs {js.count(')')} close"
        )

    # Check 4: each export function name appears in code
    for fn in interface.exports:
        if fn.name not in js:
            issues.append(f"Export function '{fn.name}' not found in code")

    # Check 5: IIFE namespace pattern
    if "(function()" not in js.replace(" ", "") and "(function ()" not in js:
        issues.append("IIFE namespace wrapper pattern not found")

    return ModuleValidationResult(is_valid=len(issues) == 0, issues=issues)
