"""Shared CLI module for all Sinal.lab agents.

Extracts the duplicated setup_logging, argparse, output writing, and
persistence orchestration from 5 agent main.py files into one place.

Usage:
    # In any agent's main.py:
    from apps.agents.base.cli import run_agent_cli
    from apps.agents.myagent.agent import MyAgent

    def main():
        run_agent_cli(
            agent_class=MyAgent,
            description="MY_AGENT — Description",
            default_output_dir="apps/agents/myagent/output",
            slug_fn=lambda agent, args: f"myagent-week-{args.week}",
        )
"""

import argparse
import logging
import os
from datetime import datetime
from typing import Any, Callable, Optional, Type

from apps.agents.base.output import AgentOutput
from apps.agents.base.persistence import persist_agent_output

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """Configure structured logging.

    Args:
        verbose: If True, set level to DEBUG; otherwise INFO.
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.getLogger().setLevel(level)


def build_base_parser(
    description: str,
    period_arg: str = "week",
    period_help: Optional[str] = None,
    extra_args_fn: Optional[Callable[[argparse.ArgumentParser], None]] = None,
) -> argparse.ArgumentParser:
    """Build an ArgumentParser with standard agent args.

    Standard args: --{period_arg}, --output, --dry-run, --persist, --verbose.

    Args:
        description: Parser description text.
        period_arg: Name of the period argument ("week" or "edition").
        period_help: Help text for the period argument.
        extra_args_fn: Optional callback to add agent-specific arguments.

    Returns:
        Configured ArgumentParser.
    """
    parser = argparse.ArgumentParser(description=description)

    if period_help is None:
        if period_arg == "edition":
            period_help = "Edition number (default: 1)"
        else:
            period_help = "Week number (default: current week)"

    if period_arg == "edition":
        default_val = 1
    else:
        default_val = datetime.now().isocalendar()[1]

    parser.add_argument(
        f"--{period_arg}",
        type=int,
        default=default_val,
        help=period_help,
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Path to save the Markdown output",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without saving output",
    )
    parser.add_argument(
        "--persist",
        action="store_true",
        help="Save agent run and content to the database",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--auto-publish",
        action="store_true",
        help="Persist content as 'published' instead of 'pending_review'",
    )

    if extra_args_fn:
        extra_args_fn(parser)

    return parser


def write_markdown_output(
    result: AgentOutput,
    output_path: Optional[str],
    default_dir: str,
    default_filename: str,
) -> str:
    """Write agent output Markdown to disk.

    Args:
        result: AgentOutput to write.
        output_path: Explicit path (if provided by user).
        default_dir: Directory for auto-generated path.
        default_filename: Filename for auto-generated path.

    Returns:
        The actual path where the file was written.
    """
    if output_path:
        actual_path = output_path
    else:
        os.makedirs(default_dir, exist_ok=True)
        actual_path = os.path.join(default_dir, default_filename)

    # Ensure parent directory exists
    parent_dir = os.path.dirname(actual_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    md_content = result.to_markdown()
    with open(actual_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    logger.info("Markdown saved to %s", actual_path)
    return actual_path


def display_run_summary(
    agent: Any,
    result: AgentOutput,
    output_path: str,
    persisted: bool = False,
) -> None:
    """Print a standardized run summary.

    Args:
        agent: The agent instance (for metadata).
        result: The AgentOutput produced.
        output_path: Where the Markdown was saved.
        persisted: Whether data was persisted to DB.
    """
    metadata = agent.get_run_metadata()

    print(f"\n{agent.agent_name.upper()} Report generated successfully!")
    print(f"  items_collected: {metadata.get('items_collected', 0)}")
    print(f"  items_processed: {metadata.get('items_processed', 0)}")

    prov_sources = 0
    if hasattr(agent, "provenance"):
        prov_sources = len(agent.provenance.get_sources())
    print(f"  Sources: {prov_sources}")

    print(
        f"  Confidence: {result.confidence.grade} "
        f"(DQ: {result.confidence.dq_display}/5, "
        f"AC: {result.confidence.ac_display}/5)"
    )
    print(f"  Output: {output_path}")

    if persisted:
        print("  DB: persisted")


def run_agent_cli(
    agent_class: Type,
    description: str,
    default_output_dir: str = "output",
    period_arg: str = "week",
    slug_fn: Optional[Callable[..., str]] = None,
    filename_fn: Optional[Callable[..., str]] = None,
    post_run_fn: Optional[Callable[..., None]] = None,
    extra_args_fn: Optional[Callable[[argparse.ArgumentParser], None]] = None,
) -> None:
    """Main entry point replacing ~100 lines of boilerplate per agent.

    Args:
        agent_class: The agent class to instantiate.
        description: CLI description.
        default_output_dir: Directory for auto-generated output files.
        period_arg: Period argument name ("week" or "edition").
        slug_fn: Callable(agent, args) -> slug string for persistence.
        filename_fn: Callable(agent, args) -> filename for output.
        post_run_fn: Callable(agent, result, args, session) for agent-specific
            post-processing (e.g. persist domain entities).
        extra_args_fn: Callable(parser) to add agent-specific CLI args.
    """
    parser = build_base_parser(
        description=description,
        period_arg=period_arg,
        extra_args_fn=extra_args_fn,
    )
    args = parser.parse_args()
    setup_logging(args.verbose)

    period_value = getattr(args, period_arg)
    agent_log = logging.getLogger(f"{agent_class.agent_name}.main")
    agent_log.info(
        "Starting %s agent, %s #%d",
        agent_class.agent_name.upper(),
        period_arg,
        period_value,
    )

    # Construct agent with the period kwarg
    agent = agent_class(**{f"{period_arg}_number": period_value})
    result = agent.run()

    # Validate output
    errors = result.validate()
    if errors:
        agent_log.warning("Output validation issues: %s", errors)

    # Display metadata
    metadata = agent.get_run_metadata()
    agent_log.info("Run metadata: %s", metadata)
    agent_log.info("Confidence: %s", result.confidence.to_dict())

    # Dry run — print preview and exit
    if args.dry_run:
        agent_log.info("Dry run — not saving output")
        print("\n" + "=" * 60)
        md = result.to_markdown()
        print(md[:2000])
        if len(md) > 2000:
            print("...")
        print("=" * 60)
        return

    # Write Markdown output
    if filename_fn:
        default_filename = filename_fn(agent, args)
    else:
        default_filename = f"{agent.agent_name}-{period_arg}-{period_value}.md"

    output_path = write_markdown_output(
        result,
        output_path=args.output,
        default_dir=default_output_dir,
        default_filename=default_filename,
    )

    # Persist to database
    persisted = False
    if args.persist:
        review_status = "published" if args.auto_publish else "pending_review"
        agent_log.info("Persisting to database (review_status=%s)...", review_status)
        try:
            from packages.database.session import get_session
            session = get_session()

            try:
                slug = slug_fn(agent, args) if slug_fn else f"{agent.agent_name}-{period_arg}-{period_value}"
                persist_agent_output(session, agent, result, slug=slug, review_status=review_status)

                # Agent-specific post-processing
                if post_run_fn:
                    post_run_fn(agent, result, args, session)

                persisted = True
            finally:
                session.close()
        except Exception as e:
            agent_log.error("Failed to persist: %s", e, exc_info=True)

    # Display summary
    display_run_summary(agent, result, output_path, persisted=persisted)
