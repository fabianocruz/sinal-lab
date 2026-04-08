#!/usr/bin/env python3
"""Automated QA for newsletter editions before publishing.

Runs a series of checks on all agent outputs for a given edition
and reports issues. Designed to run before publish_newsletter.py.

Usage:
    python scripts/qa_newsletter.py --edition 53 --week 15
"""

import argparse
import logging
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import yaml

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))

logger = logging.getLogger(__name__)

AGENT_FILES = {
    "sintese": {"file": "apps/agents/sintese/output/sinal-semanal-{edition}.md", "period": "edition"},
    "radar": {"file": "apps/agents/radar/output/radar-week-{week}.md", "period": "week"},
    "codigo": {"file": "apps/agents/codigo/output/codigo-week-{week}.md", "period": "week"},
    "funding": {"file": "apps/agents/funding/output/funding-week-{week}.md", "period": "week"},
    "mercado": {"file": "apps/agents/mercado/output/mercado-week-{week}.md", "period": "week"},
}

# Blocked content patterns
BLOCKED_PATTERNS = [
    (re.compile(r"\u2014"), "Em dash (U+2014) found"),
    (re.compile(r"\u2013"), "En dash (U+2013) found"),
    (re.compile(r"EFEX", re.I), "EFEX (seed data) found"),
    (re.compile(r"Sendwave", re.I), "Sendwave (seed data) found"),
    (re.compile(r"BemAgro", re.I), "BemAgro (seed data) found"),
    (re.compile(r"Lorem ipsum", re.I), "Lorem ipsum found"),
    (re.compile(r"mancheteesportiva", re.I), "Blocked source: mancheteesportiva"),
    (re.compile(r"conteudo patrocinado|conteúdo patrocinado", re.I), "Sponsored content found"),
]

# Self-rejection patterns (LLM says "skip this")
REJECTION_PATTERNS = [
    re.compile(r"nao ha razao.+?investigar", re.I),
    re.compile(r"nao ha insight.+?acionavel", re.I),
    re.compile(r"filtrem e sigam em frente", re.I),
    re.compile(r"nao invista tempo avaliando", re.I),
]

# Date patterns that should match current year
WRONG_YEAR_PATTERNS = [
    re.compile(r"Q[1-4]\s+2025"),
    re.compile(r"funding LATAM em 2025"),
    re.compile(r"em 2025"),
]


def check_file(agent: str, path: Path, edition: int) -> List[Tuple[str, str]]:
    """Run all QA checks on a single agent output.

    Returns list of (severity, message) tuples.
    """
    issues: List[Tuple[str, str]] = []

    if not path.exists():
        issues.append(("ERROR", f"Output file not found: {path}"))
        return issues

    content = path.read_text("utf-8")
    size = len(content)

    # Size check
    if size < 200:
        issues.append(("ERROR", f"Output too short ({size} chars)"))
    elif size < 1000:
        issues.append(("WARN", f"Output suspiciously short ({size} chars)"))

    # Parse frontmatter
    if content.strip().startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = yaml.safe_load(parts[1]) or {}
            except yaml.YAMLError:
                issues.append(("ERROR", "Invalid YAML frontmatter"))
                fm = {}
            body = parts[2]
        else:
            fm = {}
            body = content
    else:
        fm = {}
        body = content
        issues.append(("WARN", "No YAML frontmatter found"))

    # Check title
    title = fm.get("title", "")
    if not title:
        issues.append(("ERROR", "No title in frontmatter"))
    elif len(title) > 120:
        issues.append(("WARN", f"Title too long ({len(title)} chars)"))

    # Check confidence
    dq = fm.get("confidence_dq", 0)
    ac = fm.get("confidence_ac", 0)
    if dq < 0.3:
        issues.append(("WARN", f"Low data quality: {dq}"))
    if ac < 0.3:
        issues.append(("WARN", f"Low analysis confidence: {ac}"))

    # Check source count
    sources = fm.get("sources", [])
    source_count = fm.get("source_count", len(sources) if isinstance(sources, list) else 0)
    if source_count == 0:
        issues.append(("ERROR", "source_count is 0"))
    elif source_count == 1:
        issues.append(("WARN", "Single source only"))

    # Blocked content
    for pattern, message in BLOCKED_PATTERNS:
        matches = pattern.findall(body)
        if matches:
            count = len(matches)
            issues.append(("ERROR" if "seed" in message.lower() or "source" in message.lower() else "WARN",
                          f"{message} ({count}x)"))

    # Self-rejection (filler)
    for pattern in REJECTION_PATTERNS:
        if pattern.search(body):
            issues.append(("ERROR", f"Self-rejected content found: {pattern.pattern[:40]}"))

    # Wrong year
    for pattern in WRONG_YEAR_PATTERNS:
        if pattern.search(body):
            issues.append(("ERROR", f"Wrong year reference: {pattern.pattern}"))

    # Duplicate items (same URL appearing twice)
    urls = re.findall(r'https?://[^\s\)\"\']+', body)
    url_counts: Dict[str, int] = {}
    for url in urls:
        url_clean = url.rstrip(".,;:)")
        url_counts[url_clean] = url_counts.get(url_clean, 0) + 1
    duplicates = {url: c for url, c in url_counts.items() if c > 2 and "sinal.tech" not in url}
    if duplicates:
        issues.append(("WARN", f"Duplicate URLs: {list(duplicates.keys())[:3]}"))

    # Item count
    items = re.findall(r"^\*\*\d+\.", body, re.MULTILINE)
    if len(items) == 0 and agent != "mercado":
        issues.append(("WARN", "No numbered items found"))

    return issues


def main() -> None:
    parser = argparse.ArgumentParser(description="Newsletter QA checker")
    parser.add_argument("--edition", type=int, required=True)
    parser.add_argument("--week", type=int, required=True)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    total_issues = 0
    errors = 0

    for agent, config in AGENT_FILES.items():
        path = _PROJECT_ROOT / config["file"].format(edition=args.edition, week=args.week)
        issues = check_file(agent, path, args.edition)

        if issues:
            print(f"\n{'='*60}")
            print(f"  {agent.upper()}: {len(issues)} issue(s)")
            print(f"{'='*60}")
            for severity, msg in issues:
                icon = "X" if severity == "ERROR" else "!"
                print(f"  [{icon}] {severity}: {msg}")
            total_issues += len(issues)
            errors += sum(1 for s, _ in issues if s == "ERROR")
        else:
            print(f"  {agent.upper()}: OK")

    print(f"\n{'='*60}")
    print(f"  TOTAL: {total_issues} issues ({errors} errors)")
    print(f"{'='*60}")

    if errors > 0:
        print("\n  FAIL: Fix errors before publishing")
        sys.exit(1)
    elif total_issues > 0:
        print("\n  WARN: Review warnings before publishing")
        sys.exit(0)
    else:
        print("\n  PASS: All checks passed")
        sys.exit(0)


if __name__ == "__main__":
    main()
