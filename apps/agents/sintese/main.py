"""CLI entry point for the SINTESE agent.

Usage:
    python -m apps.agents.sintese.main [--edition N] [--output PATH] [--dry-run]
    python -m apps.agents.sintese.main --edition 3 --persist --send
"""

import argparse
import logging
import sys
import os
import uuid
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from apps.agents.sintese.agent import SinteseAgent
from apps.agents.sintese.newsletter import (
    markdown_to_html,
    send_via_beehiiv,
    send_via_resend,
    wrap_in_email_template,
)


def setup_logging(verbose: bool = False) -> None:
    """Configure structured logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def persist_to_db(agent, result, metadata):
    """Save agent run and content piece to the database."""
    from dotenv import load_dotenv
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    load_dotenv()
    db_url = os.getenv("DATABASE_URL", "postgresql://sinal:sinal_dev@localhost:5432/sinal_dev")
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        from packages.database.models.agent_run import AgentRun
        from packages.database.models.content_piece import ContentPiece

        now = datetime.now(timezone.utc)

        agent_run = AgentRun(
            id=uuid.uuid4(),
            agent_name=agent.agent_name,
            run_id=agent.run_id,
            started_at=metadata.get("started_at", now),
            completed_at=now,
            status="completed",
            items_collected=metadata.get("items_collected", 0),
            items_processed=metadata.get("items_processed", 0),
            items_output=1,
            avg_confidence=result.confidence.composite if hasattr(result.confidence, "composite") else None,
            data_sources={"sources": agent.provenance.get_sources() if hasattr(agent, "provenance") else []},
            error_count=0,
        )
        session.add(agent_run)

        slug = f"sinal-semanal-{agent.edition_number}"
        existing = session.query(ContentPiece).filter_by(slug=slug).first()
        if existing:
            existing.body_md = result.body_md
            existing.body_html = markdown_to_html(result.body_md)
            existing.confidence_dq = result.confidence.dq_display
            existing.confidence_ac = result.confidence.ac_display
            existing.sources = result.sources
            existing.summary = result.summary
            existing.review_status = "pending_review"
            existing.agent_run_id = agent.run_id
        else:
            content = ContentPiece(
                id=uuid.uuid4(),
                title=result.title,
                slug=slug,
                body_md=result.body_md,
                body_html=markdown_to_html(result.body_md),
                summary=result.summary,
                content_type=result.content_type,
                agent_name=agent.agent_name,
                agent_run_id=agent.run_id,
                sources=result.sources,
                confidence_dq=result.confidence.dq_display,
                confidence_ac=result.confidence.ac_display,
                review_status="pending_review",
            )
            session.add(content)

        session.commit()
        logging.getLogger("sintese.main").info("Persisted run %s and content to database", agent.run_id)
    except Exception as e:
        session.rollback()
        logging.getLogger("sintese.main").error("Failed to persist to database: %s", e)
        raise
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="SINTESE — Sinal.lab Newsletter Synthesizer Agent"
    )
    parser.add_argument(
        "--edition", type=int, default=1,
        help="Newsletter edition number (default: 1)",
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Path to save the newsletter Markdown output",
    )
    parser.add_argument(
        "--html", type=str, default=None,
        help="Path to save the newsletter HTML output",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Run without saving output or sending emails",
    )
    parser.add_argument(
        "--persist", action="store_true",
        help="Save agent run and content to the database",
    )
    parser.add_argument(
        "--send", action="store_true",
        help="Send newsletter via Resend/Beehiiv (requires API keys)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    logger = logging.getLogger("sintese.main")
    logger.info("Starting SINTESE agent, edition #%d", args.edition)

    # Run the agent
    agent = SinteseAgent(edition_number=args.edition)
    result = agent.run()

    # Validate output
    errors = result.validate()
    if errors:
        logger.warning("Output validation issues: %s", errors)

    # Display results
    metadata = agent.get_run_metadata()
    logger.info("Run metadata: %s", metadata)
    logger.info("Confidence: %s", result.confidence.to_dict())
    logger.info("Provenance summary: %s", agent.provenance.summary())

    if args.dry_run:
        logger.info("Dry run — not saving output")
        print("\n" + "=" * 60)
        print(result.to_markdown()[:2000])
        print("..." if len(result.to_markdown()) > 2000 else "")
        print("=" * 60)
        return

    # Save Markdown output
    md_content = result.to_markdown()
    if args.output:
        output_path = args.output
    else:
        os.makedirs("apps/agents/sintese/output", exist_ok=True)
        output_path = f"apps/agents/sintese/output/sinal-semanal-{args.edition}.md"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    logger.info("Markdown saved to %s", output_path)

    # Save HTML output
    html_body = markdown_to_html(result.body_md)
    html_full = wrap_in_email_template(html_body, result.title)

    if args.html:
        with open(args.html, "w", encoding="utf-8") as f:
            f.write(html_full)
        logger.info("HTML saved to %s", args.html)

    # Persist to database
    if args.persist:
        logger.info("Persisting to database...")
        persist_to_db(agent, result, metadata)

    # Send newsletter
    if args.send:
        logger.info("Sending newsletter...")
        subject = f"Sinal Semanal #{args.edition}"
        beehiiv_ok = send_via_beehiiv(html_full, subject)
        if not beehiiv_ok:
            logger.info("Beehiiv not configured, skipping")
        resend_ok = send_via_resend(html_full, subject, to_email="subscribers@sinal.ai")
        if not resend_ok:
            logger.info("Resend not configured or send failed")

    print(f"\nSinal Semanal #{args.edition} generated successfully!")
    print(f"  Items analyzed: {metadata['items_collected']}")
    print(f"  Items scored: {metadata['items_processed']}")
    print(f"  Sources: {agent.provenance.summary()['unique_sources']}")
    print(f"  Confidence: {result.confidence.grade} (DQ: {result.confidence.dq_display}/5, AC: {result.confidence.ac_display}/5)")
    print(f"  Output: {output_path}")
    if args.persist:
        print("  DB: persisted")
    if args.send:
        print("  Delivery: attempted")


if __name__ == "__main__":
    main()
