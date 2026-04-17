#!/usr/bin/env python3
"""Unified agent runner for Sinal.lab.

Runs one or more agents via subprocess (default) or in-process with
editorial-in-the-loop (--orchestrate).

Usage:
    # Subprocess mode (default, backward-compatible)
    python scripts/run_agents.py sintese --edition 3 --persist
    python scripts/run_agents.py radar --persist
    python scripts/run_agents.py all --output
    python scripts/run_agents.py all --persist --dry-run

    # Orchestrate mode (in-process, editorial review, evidence items)
    python scripts/run_agents.py radar --week 8 --orchestrate
    python scripts/run_agents.py all --week 8 --orchestrate --no-editorial
"""

import argparse
import importlib
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load .env so all API keys (X_BEARER_TOKEN, PRODUCTHUNT_TOKEN, etc.)
# are available to agents run as subprocesses via os.environ.
load_dotenv(PROJECT_ROOT / ".env")

AGENTS = {
    "sintese": {
        "module": "apps.agents.sintese.main",
        "description": "Newsletter synthesis from RSS/Atom feeds",
        "class_module": "apps.agents.sintese.agent",
        "class_name": "SinteseAgent",
        "period_arg": "edition",
        "slug_pattern": "sinal-semanal-{period}",
        "output_dir": "apps/agents/sintese/output",
        "filename_pattern": "sinal-semanal-{period}.md",
    },
    "radar": {
        "module": "apps.agents.radar.main",
        "description": "Emerging trend detection (HN, GitHub, arXiv)",
        "class_module": "apps.agents.radar.agent",
        "class_name": "RadarAgent",
        "period_arg": "week",
        "slug_pattern": "radar-week-{period}",
        "output_dir": "apps/agents/radar/output",
        "filename_pattern": "radar-week-{period}.md",
    },
    "codigo": {
        "module": "apps.agents.codigo.main",
        "description": "Developer ecosystem signals (GitHub, npm, PyPI)",
        "class_module": "apps.agents.codigo.agent",
        "class_name": "CodigoAgent",
        "period_arg": "week",
        "slug_pattern": "codigo-week-{period}",
        "output_dir": "apps/agents/codigo/output",
        "filename_pattern": "codigo-week-{period}.md",
    },
    "funding": {
        "module": "apps.agents.funding.main",
        "description": "Investment tracking (VC announcements, funding rounds)",
        "class_module": "apps.agents.funding.agent",
        "class_name": "FundingAgent",
        "period_arg": "week",
        "slug_pattern": "funding-semanal-{period}",
        "output_dir": "apps/agents/funding/output",
        "filename_pattern": "funding-week-{period}.md",
    },
    "mercado": {
        "module": "apps.agents.mercado.main",
        "description": "LATAM startup mapping and ecosystem intelligence",
        "class_module": "apps.agents.mercado.agent",
        "class_name": "MercadoAgent",
        "period_arg": "week",
        "slug_pattern": "mercado-week-{period}",
        "output_dir": "apps/agents/mercado/output",
        "filename_pattern": "mercado-week-{period}.md",
    },
    "index": {
        "module": "apps.agents.index.main",
        "description": "LATAM Startup Index — comprehensive registry from bulk sources",
        "class_module": "apps.agents.index.agent",
        "class_name": "IndexAgent",
        "period_arg": "week",
        "slug_pattern": "index-week-{period}",
        "output_dir": "apps/agents/index/output",
        "filename_pattern": "index-week-{period}.md",
    },
    "social_signals": {
        "module": "apps.agents.social_signals.main",
        "description": "Social Signal Intelligence for AI, Fintech, and Banking (DEPRECATED: use vozes+pulso)",
        "class_module": "apps.agents.social_signals.agent",
        "class_name": "SocialSignalsAgent",
        "period_arg": "week",
        "slug_pattern": "social-signals-week-{period}",
        "output_dir": "apps/agents/social_signals/output",
        "filename_pattern": "social-signals-week-{period}.md",
    },
    "vozes": {
        "module": "apps.agents.vozes.main",
        "description": "Social voice monitoring, collection, and authority scoring",
        "class_module": "apps.agents.vozes.agent",
        "class_name": "VozesAgent",
        "period_arg": "week",
        "slug_pattern": "vozes-week-{period}",
        "output_dir": "apps/agents/vozes/output",
        "filename_pattern": "vozes-week-{period}.md",
    },
    "pulso": {
        "module": "apps.agents.pulso.main",
        "description": "Social signal clustering, scoring, and weekly pulse generation",
        "class_module": "apps.agents.pulso.agent",
        "class_name": "PulsoAgent",
        "period_arg": "week",
        "slug_pattern": "pulso-week-{period}",
        "output_dir": "apps/agents/pulso/output",
        "filename_pattern": "pulso-week-{period}.md",
    },
    "feed_curator": {
        "module": "apps.agents.feed_curator.main",
        "description": "Feed Curator — AI editorial curation of social signals (Ana Torres)",
        "class_module": "apps.agents.feed_curator.agent",
        "class_name": "FeedCuratorAgent",
        "period_arg": None,
        "slug_pattern": "feed-curated",
        "output_dir": "apps/agents/feed_curator/output",
        "filename_pattern": "feed-curated.md",
        "skip_content_piece": True,  # Feed items go to curated_feed_items, not content_pieces
    },
}


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [run_agents] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def run_agent(name: str, extra_args: List[str], dry_run: bool = False) -> int:
    """Run a single agent as a subprocess."""
    logger = logging.getLogger("run_agents")

    if name not in AGENTS:
        logger.error("Unknown agent: %s. Valid: %s", name, list(AGENTS.keys()))
        return 1

    agent_cfg = AGENTS[name]
    cmd = [sys.executable, "-m", agent_cfg["module"]] + extra_args

    if dry_run:
        cmd.append("--dry-run")

    logger.info("Running %s: %s", name.upper(), " ".join(cmd))
    logger.info("  Description: %s", agent_cfg["description"])

    result = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT)},
    )

    if result.returncode == 0:
        logger.info("%s completed successfully", name.upper())
    else:
        logger.error("%s failed with exit code %d", name.upper(), result.returncode)

    return result.returncode


# ---------------------------------------------------------------------------
# Domain-specific persistence callbacks for orchestrate mode
# Signature: (agent, agent_output, session) — matches orchestrator's domain_persist_fn
# ---------------------------------------------------------------------------


def _funding_domain_persist(agent: Any, agent_output: Any, session: Any) -> None:
    """Persist FUNDING-specific data (funding rounds)."""
    from apps.agents.funding.db_writer import persist_all_events

    scored_events = getattr(agent, "_scored_events", [])
    if scored_events:
        events_with_confidence = [
            (scored.event, scored.confidence.composite) for scored in scored_events
        ]
        stats = persist_all_events(session, events_with_confidence)
        logging.getLogger("run_agents").info("Persisted funding rounds: %s", stats)


def _mercado_domain_persist(agent: Any, agent_output: Any, session: Any) -> None:
    """Persist MERCADO-specific data (company profiles)."""
    from apps.agents.mercado.db_writer import persist_all_profiles

    scored_profiles = getattr(agent, "_scores", [])
    if scored_profiles:
        profiles_with_confidence = [
            (scored.profile, scored.composite_score) for scored in scored_profiles
        ]
        stats = persist_all_profiles(session, profiles_with_confidence)
        logging.getLogger("run_agents").info("Persisted company profiles: %s", stats)


def _index_domain_persist(agent: Any, agent_output: Any, session: Any) -> None:
    """Persist INDEX-specific data (company registry from bulk sources)."""
    from apps.agents.index.db_writer import persist_index_results

    scored_companies = getattr(agent, "_scored_companies", [])
    if scored_companies:
        stats = persist_index_results(session, scored_companies)
        logging.getLogger("run_agents").info("Persisted INDEX companies: %s", stats)


def _social_signals_domain_persist(agent: Any, agent_output: Any, session: Any) -> None:
    """Persist social signal clusters, individual signals, and weekly pulse."""
    from apps.agents.social_signals.db_writer import persist_social_signals

    persist_social_signals(agent, agent_output, session)


def _vozes_domain_persist(agent: Any, agent_output: Any, session: Any) -> None:
    """Persist individual social signals from VOZES."""
    from apps.agents.vozes.db_writer import persist_vozes_signals

    persist_vozes_signals(agent, agent_output, session)


def _pulso_domain_persist(agent: Any, agent_output: Any, session: Any) -> None:
    """Persist signal clusters and weekly pulse from PULSO."""
    from apps.agents.pulso.db_writer import persist_pulso_data

    persist_pulso_data(agent, agent_output, session)


def _feed_curator_domain_persist(agent: Any, agent_output: Any, session: Any) -> None:
    """Persist curated feed items."""
    from apps.agents.feed_curator.db_writer import persist_curated_feed

    persist_curated_feed(agent, agent_output, session)


DOMAIN_PERSIST_FNS: Dict[str, Callable[..., None]] = {
    "funding": _funding_domain_persist,
    "mercado": _mercado_domain_persist,
    "index": _index_domain_persist,
    "social_signals": _social_signals_domain_persist,
    "vozes": _vozes_domain_persist,
    "pulso": _pulso_domain_persist,
    "feed_curator": _feed_curator_domain_persist,
}


def _load_agent_class(name: str) -> type:
    """Lazily import and return an agent class by name."""
    cfg = AGENTS[name]
    mod = importlib.import_module(cfg["class_module"])
    return getattr(mod, cfg["class_name"])


def orchestrate_single_agent(
    name: str,
    period_value: int,
    session: Any,
    enable_editorial: bool = True,
    enable_evidence: bool = True,
) -> int:
    """Run one agent in-process using the orchestrator.

    Returns 0 on success, 1 on failure.
    """
    logger = logging.getLogger("run_agents")

    if name not in AGENTS:
        logger.error("Unknown agent: %s", name)
        return 1

    cfg = AGENTS[name]

    try:
        from apps.agents.base.orchestrator import orchestrate_agent_run

        agent_class = _load_agent_class(name)

        if cfg["period_arg"] is not None:
            period_kwarg = f"{cfg['period_arg']}_number"
            agent = agent_class(**{period_kwarg: period_value})
            slug = cfg["slug_pattern"].format(period=period_value)
        else:
            agent = agent_class()
            slug = cfg["slug_pattern"]
        domain_fn = DOMAIN_PERSIST_FNS.get(name)

        logger.info(
            "Orchestrating %s (slug=%s, editorial=%s, evidence=%s)",
            name.upper(), slug, enable_editorial, enable_evidence,
        )

        result = orchestrate_agent_run(
            agent,
            session=session,
            slug=slug,
            enable_editorial=enable_editorial,
            enable_evidence=enable_evidence,
            persist=True,
            domain_persist_fn=domain_fn,
        )

        grade = result.agent_output.confidence.grade
        logger.info(
            "%s completed: grade=%s, persisted=%s, editorial=%s",
            name.upper(),
            grade,
            result.persisted,
            "approved" if (result.editorial_result and result.editorial_result.publish_ready) else "pending",
        )
        return 0

    except Exception as e:
        logger.error("%s failed: %s", name.upper(), e, exc_info=True)
        return 1


def orchestrate_vozes_pulso(
    week_value: int,
    session: Any,
    enable_editorial: bool = True,
    enable_evidence: bool = True,
) -> int:
    """Run VOZES -> PULSO pipeline: collect signals, then cluster and score.

    VOZES collects and classifies social signals, exports them as JSON.
    PULSO reads the JSON, clusters, scores, and generates the Weekly Pulse.

    Returns 0 on success, 1 on failure.
    """
    logger = logging.getLogger("run_agents")
    import tempfile

    # Step 1: Run VOZES
    logger.info("=" * 40)
    logger.info("PIPELINE Step 1/2: Running VOZES (collect + classify)")
    vozes_code = orchestrate_single_agent(
        "vozes",
        period_value=week_value,
        session=session,
        enable_editorial=False,  # VOZES is a data agent, no editorial
        enable_evidence=enable_evidence,
    )
    if vozes_code != 0:
        logger.error("VOZES failed, aborting pipeline")
        return 1

    # Step 2: Run PULSO with DB session injected so it can load VOZES signals
    logger.info("=" * 40)
    logger.info("PIPELINE Step 2/2: Running PULSO (cluster + score)")

    try:
        from apps.agents.base.orchestrator import orchestrate_agent_run
        from apps.agents.pulso.agent import PulsoAgent

        pulso_agent = PulsoAgent(week_number=week_value)
        pulso_agent.set_db_session(session)

        slug = f"pulso-week-{week_value}"
        domain_fn = DOMAIN_PERSIST_FNS.get("pulso")

        logger.info(
            "Orchestrating PULSO (slug=%s, editorial=%s, evidence=%s)",
            slug, enable_editorial, enable_evidence,
        )

        result = orchestrate_agent_run(
            pulso_agent,
            session=session,
            slug=slug,
            enable_editorial=enable_editorial,
            enable_evidence=enable_evidence,
            persist=True,
            domain_persist_fn=domain_fn,
        )

        grade = result.agent_output.confidence.grade
        logger.info(
            "PULSO completed: grade=%s, persisted=%s, editorial=%s",
            grade,
            result.persisted,
            "approved" if (result.editorial_result and result.editorial_result.publish_ready) else "pending",
        )
    except Exception as e:
        logger.error("PULSO failed: %s", e, exc_info=True)
        return 1

    logger.info("VOZES -> PULSO pipeline completed successfully")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sinal.lab unified agent runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available agents:
  sintese          Newsletter synthesis from RSS/Atom feeds
  radar            Emerging trend detection
  codigo           Developer ecosystem signals
  funding          Investment tracking (VC announcements, funding rounds)
  mercado          LATAM startup mapping and ecosystem intelligence
  index            LATAM Startup Index (comprehensive registry from bulk sources)
  vozes            Social voice monitoring, collection, and authority scoring
  pulso            Social signal clustering, scoring, and weekly pulse
  social_signals   (deprecated) Use vozes+pulso instead
  feed_curator     Feed Curator -- AI editorial curation of social signals
  vozes_pulso      Pipeline: VOZES -> PULSO (collect, classify, cluster, score)
  all              Run all agents sequentially
        """,
    )
    parser.add_argument(
        "agent",
        choices=list(AGENTS.keys()) + ["all", "vozes_pulso"],
        help="Agent to run (or 'all' or 'vozes_pulso' pipeline)",
    )
    parser.add_argument(
        "--week", type=int, default=None,
        help="Week number (for week-based agents)",
    )
    parser.add_argument(
        "--edition", type=int, default=1,
        help="Edition number (for sintese agent)",
    )
    parser.add_argument(
        "--persist", action="store_true",
        help="Save results to database (subprocess mode)",
    )
    parser.add_argument(
        "--send", action="store_true",
        help="Send newsletter (sintese only, subprocess mode)",
    )
    parser.add_argument(
        "--output", action="store_true",
        help="Save Markdown output to each agent's output/ directory",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Run without saving or sending",
    )
    parser.add_argument(
        "--orchestrate", action="store_true",
        help="Run in-process with editorial review and evidence persistence",
    )
    parser.add_argument(
        "--no-editorial", action="store_true",
        help="Skip editorial review (orchestrate mode only)",
    )
    parser.add_argument(
        "--no-evidence", action="store_true",
        help="Skip evidence item persistence (orchestrate mode only)",
    )
    parser.add_argument(
        "--publish", action="store_true",
        help="Send unified newsletter via Resend Broadcasts after all agents complete",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Verbose logging",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger("run_agents")

    # Resolve agent list
    if args.agent == "vozes_pulso":
        is_pipeline = True
        agents_to_run = []  # handled specially
    elif args.agent == "all":
        is_pipeline = False
        agents_to_run = list(AGENTS.keys())
    else:
        is_pipeline = False
        agents_to_run = [args.agent]

    exit_codes = []
    from datetime import datetime

    if args.week is None:
        week_val = datetime.now().isocalendar()[1]
    else:
        week_val = args.week

    if is_pipeline or args.orchestrate:
        # In-process mode (required for pipeline, optional for single agents)
        from packages.database.session import get_session

        session = get_session()
        try:
            if is_pipeline:
                # VOZES -> PULSO pipeline
                code = orchestrate_vozes_pulso(
                    week_value=week_val,
                    session=session,
                    enable_editorial=not args.no_editorial,
                    enable_evidence=not args.no_evidence,
                )
                exit_codes.append(code)
            else:
                for name in agents_to_run:
                    cfg = AGENTS[name]
                    if cfg["period_arg"] == "edition":
                        period_value = args.edition
                    elif cfg["period_arg"] is not None:
                        period_value = week_val
                    else:
                        period_value = 0  # No period concept (e.g. feed_curator)

                    code = orchestrate_single_agent(
                        name,
                        period_value=period_value,
                        session=session,
                        enable_editorial=not args.no_editorial,
                        enable_evidence=not args.no_evidence,
                    )
                    exit_codes.append(code)
        finally:
            session.close()
    else:
        # Subprocess mode (default, backward-compatible)
        for name in agents_to_run:
            cfg = AGENTS[name]
            extra_args = []

            if name == "sintese":
                extra_args.extend(["--edition", str(args.edition)])
                if args.send:
                    extra_args.append("--send")

            if args.week is not None and cfg["period_arg"] == "week":
                extra_args.extend(["--week", str(args.week)])

            if args.persist:
                extra_args.append("--persist")

            if args.output:
                period = args.edition if cfg["period_arg"] == "edition" else week_val
                filename = cfg["filename_pattern"].format(period=period)
                output_path = str(PROJECT_ROOT / cfg["output_dir"] / filename)
                extra_args.extend(["--output", output_path])

            if args.verbose:
                extra_args.append("--verbose")

            code = run_agent(name, extra_args, dry_run=args.dry_run)
            exit_codes.append(code)

    failed = sum(1 for c in exit_codes if c != 0)
    total = len(exit_codes)

    logger.info("=" * 40)
    logger.info("Results: %d/%d agents succeeded", total - failed, total)

    if failed:
        logger.error("%d agent(s) failed", failed)
        sys.exit(1)

    # Publish unified newsletter if requested and all agents succeeded
    if args.publish and failed == 0:
        from scripts.publish_newsletter import publish_newsletter

        logger.info("Sending unified newsletter broadcast via Resend...")
        publish_newsletter(
            edition=args.edition,
            week=week_val,
            dry_run=args.dry_run,
        )


if __name__ == "__main__":
    main()
