"""Enrich company profiles using the GitHub API.

Fetches public organization/user data from GitHub for companies that already
have a github_url in the database.  Only fills empty fields — never overwrites
existing data.  Bumps source_count on every successful enrichment.

Fields that can be enriched:
  - website         (from GitHub org/user homepage)
  - description     (from GitHub bio — only if ≤500 chars)
  - short_description
  - twitter_url     (from GitHub twitter_username)
  - tech_stack      (top languages from public repos)

Metadata stored in metadata_["github"]:
  - public_repos, followers, github_stars (sum of repo stars)
  - enriched_at (ISO timestamp)

Usage:
    python scripts/enrich_companies_github.py --dry-run
    python scripts/enrich_companies_github.py --limit 50
    python scripts/enrich_companies_github.py

Rate limits:
  - Without GITHUB_TOKEN: 60 requests/hour  (not practical)
  - With GITHUB_TOKEN:    5,000 requests/hour
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from datetime import datetime

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from packages.database.session import SessionLocal
from packages.database.models.company import Company

BATCH_SIZE = 50

# ---------------------------------------------------------------------------
# Pure functions (tested independently)
# ---------------------------------------------------------------------------


def extract_github_username(github_url: str) -> str | None:
    """Extract the GitHub org/user name from a URL.

    Handles variations like:
      - https://github.com/nubank
      - http://github.com/nubank/
      - github.com/nubank
      - https://github.com/nubank/some-repo

    Returns the first path segment (org/user), or None if unparseable.
    """
    if not github_url or not github_url.strip():
        return None

    url = github_url.strip().rstrip("/")

    # Remove protocol
    url = re.sub(r"^https?://", "", url)

    # Must start with github.com
    if not url.lower().startswith("github.com/"):
        return None

    path = url[len("github.com/"):]
    if not path:
        return None

    # Take first path segment (the org/user name)
    username = path.split("/")[0].strip()
    if not username:
        return None

    # Reject invalid GitHub usernames
    if not re.match(r"^[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?$", username):
        return None

    return username


def build_twitter_url(twitter_username: str | None) -> str | None:
    """Build a full Twitter/X URL from a GitHub twitter_username field.

    Returns None if the username is empty or invalid.
    """
    if not twitter_username or not twitter_username.strip():
        return None
    handle = twitter_username.strip().lstrip("@")
    if not handle:
        return None
    return f"https://twitter.com/{handle}"


def extract_top_languages(repos_data: list[dict]) -> list[str]:
    """Extract the top languages from a list of GitHub repo objects.

    Counts how many repos use each language, returns up to 5 sorted by
    frequency.  Skips repos with no language set.
    """
    lang_counts: dict[str, int] = {}
    for repo in repos_data:
        lang = repo.get("language")
        if lang:
            lang_counts[lang] = lang_counts.get(lang, 0) + 1

    sorted_langs = sorted(lang_counts.items(), key=lambda x: x[1], reverse=True)
    return [lang for lang, _ in sorted_langs[:5]]


def sum_repo_stars(repos_data: list[dict]) -> int:
    """Sum stargazers_count across all repos."""
    return sum(repo.get("stargazers_count", 0) for repo in repos_data)


def should_enrich_field(current_value: str | None) -> bool:
    """Check if a field is empty and should be enriched."""
    return not current_value or not str(current_value).strip()


# ---------------------------------------------------------------------------
# GitHub API helpers
# ---------------------------------------------------------------------------


def get_github_headers() -> dict[str, str]:
    """Build HTTP headers for GitHub API, including auth token if available."""
    headers: dict[str, str] = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def fetch_github_org(client: httpx.Client, username: str) -> dict | None:
    """Fetch a GitHub organization profile.

    Falls back to user endpoint if org returns 404.
    Returns the JSON response dict or None on error.
    """
    # Try org first
    resp = client.get(f"https://api.github.com/orgs/{username}")
    if resp.status_code == 200:
        return resp.json()

    # Fall back to user
    resp = client.get(f"https://api.github.com/users/{username}")
    if resp.status_code == 200:
        return resp.json()

    return None


def fetch_github_repos(
    client: httpx.Client, username: str, max_repos: int = 30
) -> list[dict]:
    """Fetch public repos for a GitHub org/user, sorted by stars.

    Returns up to max_repos repo objects.
    """
    resp = client.get(
        f"https://api.github.com/users/{username}/repos",
        params={
            "type": "public",
            "sort": "stars",
            "direction": "desc",
            "per_page": min(max_repos, 100),
        },
    )
    if resp.status_code != 200:
        return []
    return resp.json()


def check_rate_limit(client: httpx.Client) -> tuple[int, int]:
    """Check remaining GitHub API rate limit.

    Returns (remaining, reset_timestamp).
    """
    resp = client.get("https://api.github.com/rate_limit")
    if resp.status_code != 200:
        return 0, 0
    data = resp.json().get("rate", {})
    return data.get("remaining", 0), data.get("reset", 0)


# ---------------------------------------------------------------------------
# Enrichment logic
# ---------------------------------------------------------------------------


def enrich_company_from_github(
    company: Company,
    profile: dict,
    repos: list[dict],
) -> bool:
    """Apply GitHub data to a Company, filling only empty fields.

    Returns True if any field was updated, False otherwise.
    """
    changed = False

    # Website
    blog = (profile.get("blog") or "").strip()
    if blog and should_enrich_field(company.website):
        # Ensure it has a protocol
        if not blog.startswith("http"):
            blog = f"https://{blog}"
        company.website = blog
        changed = True

    # Description (from GitHub bio)
    bio = (profile.get("description") or profile.get("bio") or "").strip()
    if bio and should_enrich_field(company.description):
        company.description = bio
        changed = True
    if bio and should_enrich_field(company.short_description) and len(bio) <= 500:
        company.short_description = bio
        changed = True

    # Twitter URL
    twitter = profile.get("twitter_username")
    twitter_url = build_twitter_url(twitter)
    if twitter_url and should_enrich_field(company.twitter_url):
        company.twitter_url = twitter_url
        changed = True

    # Tech stack (top languages from repos)
    if repos and not company.tech_stack:
        languages = extract_top_languages(repos)
        if languages:
            company.tech_stack = languages
            changed = True

    # Always update GitHub metadata (even if other fields unchanged)
    meta = company.metadata_ or {}
    github_meta = meta.get("github", {})
    stars = sum_repo_stars(repos)
    new_github_meta = {
        "public_repos": profile.get("public_repos", 0),
        "followers": profile.get("followers", 0),
        "github_stars": stars,
        "enriched_at": datetime.utcnow().isoformat(),
    }
    if new_github_meta != github_meta:
        meta["github"] = new_github_meta
        company.metadata_ = meta
        changed = True

    if changed:
        company.source_count = (company.source_count or 1) + 1

    return changed


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------


def run(dry_run: bool = False, limit: int | None = None) -> None:
    """Enrich companies that have a github_url using the GitHub API.

    Processes companies in batches to avoid database connection timeouts
    on long-running enrichment sessions (Railway PostgreSQL drops idle
    connections after ~5 minutes).
    """
    db = SessionLocal()

    # Fetch company IDs + github_urls (lightweight query)
    query = db.query(Company.id, Company.github_url).filter(
        Company.github_url.isnot(None),
        Company.github_url != "",
        Company.status == "active",
    )
    if limit:
        query = query.limit(limit)

    company_refs = query.all()
    db.close()

    total = len(company_refs)
    print(f"Companies with github_url: {total}")

    if not total:
        print("Nothing to enrich.")
        return

    # Check for GitHub token
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        print("[WARN] No GITHUB_TOKEN set — rate limit is 60 req/hour.")
        print("       Set GITHUB_TOKEN for 5,000 req/hour.\n")

    headers = get_github_headers()
    client = httpx.Client(headers=headers, timeout=15.0)

    # Check rate limit before starting
    remaining, reset_ts = check_rate_limit(client)
    print(f"GitHub API rate limit: {remaining} requests remaining")
    if remaining < total * 2:  # ~2 requests per company (profile + repos)
        reset_time = datetime.fromtimestamp(reset_ts).strftime("%H:%M:%S")
        print(f"[WARN] May hit rate limit. Resets at {reset_time}")
    print()

    enriched = 0
    skipped = 0
    errors = 0

    # Phase 1: Fetch all GitHub data (no DB connection needed)
    # Stores (company_id, profile, repos) tuples in memory.
    github_data: list[tuple[str, dict, list[dict]]] = []

    for i, (cid, github_url) in enumerate(company_refs):
        username = extract_github_username(github_url)
        if not username:
            skipped += 1
            continue

        try:
            profile = fetch_github_org(client, username)
            if not profile:
                skipped += 1
                continue

            repos = fetch_github_repos(client, username)

            if dry_run:
                bio = (profile.get("description") or profile.get("bio") or "")[:60]
                stars = sum_repo_stars(repos)
                langs = extract_top_languages(repos)
                print(
                    f"  [{i+1:>4}/{total}] (id={str(cid)[:8]})"
                    f" — {stars}★, {len(repos)} repos, {langs[:3]}"
                    f" — \"{bio}\""
                )
                enriched += 1
            else:
                github_data.append((str(cid), profile, repos))

        except Exception as e:
            errors += 1
            print(f"  [ERROR] id={str(cid)[:8]} (@{username}): {e}")
            continue

        # Respect rate limits: small delay between requests
        if (i + 1) % 10 == 0:
            time.sleep(0.5)

    client.close()

    if dry_run:
        print(f"\n{'=' * 55}")
        print(f"Done (dry-run): {enriched} would enrich, {skipped} skipped, {errors} errors")
        return

    # Phase 2: Apply GitHub data to DB in fast batches
    # Each batch opens a fresh session, applies changes, commits, closes.
    print(f"\nGitHub data fetched for {len(github_data)} companies. Writing to DB...")

    for batch_start in range(0, len(github_data), BATCH_SIZE):
        batch = github_data[batch_start : batch_start + BATCH_SIZE]
        batch_ids = [item[0] for item in batch]

        db = SessionLocal()
        companies = db.query(Company).filter(Company.id.in_(batch_ids)).all()
        company_map = {str(c.id): c for c in companies}
        batch_enriched = 0

        for cid, profile, repos in batch:
            company = company_map.get(cid)
            if not company:
                skipped += 1
                continue

            changed = enrich_company_from_github(company, profile, repos)
            if changed:
                batch_enriched += 1
            else:
                skipped += 1

        if batch_enriched > 0:
            try:
                db.commit()
                enriched += batch_enriched
                batch_num = batch_start // BATCH_SIZE + 1
                print(f"  [batch {batch_num}] committed {batch_enriched} enriched")
            except Exception as e:
                db.rollback()
                errors += batch_enriched
                print(f"  [ERROR] Batch commit failed: {e}")

        db.close()

    print(f"\n{'=' * 55}")
    print(f"Done: {enriched} enriched, {skipped} skipped, {errors} errors")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Enrich company profiles from GitHub API"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview without writing to DB"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max companies to process (default: all)",
    )
    args = parser.parse_args()

    run(dry_run=args.dry_run, limit=args.limit)
