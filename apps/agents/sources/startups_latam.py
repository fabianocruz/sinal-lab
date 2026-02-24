"""StartupsLatam.com collector for LATAM startup directory.

Fetches startup profiles from the WordPress REST API at
startupslatam.com. Returns structured data for the INDEX agent.

Data source: StartupsLatam WordPress API (wp-json/wp/v2/startup)
Confidence: 0.7 (curated directory, single source).
"""

import logging
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Dict, List, Optional

import httpx

from apps.agents.base.config import DataSourceConfig

logger = logging.getLogger(__name__)

BASE_URL = "https://startupslatam.com"
STARTUP_ENDPOINT = f"{BASE_URL}/wp-json/wp/v2/startup"
INDUSTRY_ENDPOINT = f"{BASE_URL}/wp-json/wp/v2/industry"
DEFAULT_CONFIDENCE = 0.7
PER_PAGE = 100

# Map industry names from StartupsLatam to our sector normalizer inputs.
# These are mapped to English equivalents that sector_normalizer understands.
INDUSTRY_ALIASES: Dict[str, str] = {
    "Financial Technology/FinTech": "Fintech",
    "Agricultural Technology/AgTech": "agriculture",
    "Artificial Intelligence and Machine Learning": "artificial intelligence",
    "Educational Technology/EdTech": "education",
    "Healthcare/Medical Technology": "healthcare",
    "Retail and E-commerce": "ecommerce",
    "Transportation and Logistics": "logistics",
    "Human Resources and Talent Management": "human resources",
    "Construction and Architecture": "construction",
    "Energy and Sustainability": "energy",
    "IT Services and Infrastructure Management": "software",
    "Data Analytics and Business Intelligence": "analytics",
    "Cybersecurity and Data Protection": "cybersecurity",
    "Technology Consulting and Advisory Services": "software",
    "Telecommunications and Networking": "telecommunications",
    "Internet of Things/IoT": "iot",
    "Entertainment and Media": "media",
    "Virtual and Augmented Reality": "vr/ar",
    "Automation and Robotics": "automation",
    "Manufacturing and Production": "manufacturing",
    "Travel and Hospitality": "travel",
    "Scientific Research and Development": "research",
    "Technology Research and Development": "research",
    "Security and Surveillance": "cybersecurity",
    "Government and Public Administration": "govtech",
}

# Country patterns in Spanish content (adjective → country name)
_COUNTRY_PATTERNS: Dict[str, str] = {
    r"\bchilen[ao]s?\b": "Chile",
    r"\bmexican[ao]s?\b": "Mexico",
    r"\bbrasilei?[rñ][ao]s?\b": "Brazil",
    r"\bcolombiana?o?s?\b": "Colombia",
    r"\bargentin[ao]s?\b": "Argentina",
    r"\bperuan[ao]s?\b": "Peru",
    r"\buruguay[ao]s?\b": "Uruguay",
    r"\becuatorian[ao]s?\b": "Ecuador",
    r"\bbolivian[ao]s?\b": "Bolivia",
    r"\bparaguay[ao]s?\b": "Paraguay",
    r"\bvenezolan[ao]s?\b": "Venezuela",
    r"\bcostarricens[ea]s?\b": "Costa Rica",
    r"\bpanameñ[ao]s?\b": "Panama",
    # Direct country mentions
    r"\bChile\b": "Chile",
    r"\bMéxico\b": "Mexico",
    r"\bBrasil\b": "Brazil",
    r"\bColombia\b": "Colombia",
    r"\bArgentina\b": "Argentina",
    r"\bPerú\b": "Peru",
    r"\bUruguay\b": "Uruguay",
    r"\bEcuador\b": "Ecuador",
}


class _HTMLStripper(HTMLParser):
    """Strip HTML tags, keeping only text content."""

    def __init__(self):
        super().__init__()
        self._text: List[str] = []

    def handle_data(self, data: str) -> None:
        self._text.append(data)

    def get_text(self) -> str:
        import re as _re
        text = " ".join(self._text).strip()
        return _re.sub(r"\s+", " ", text)


def _strip_html(html: str) -> str:
    """Remove HTML tags from a string."""
    if not html:
        return ""
    stripper = _HTMLStripper()
    stripper.feed(html)
    return stripper.get_text()


@dataclass
class StartupsLatamCompany:
    """A company from the StartupsLatam directory."""

    name: str
    slug: str
    description: str = ""
    industry: str = ""  # raw industry name from WP taxonomy
    country: str = ""  # extracted from content text
    website: str = ""
    source_url: str = ""
    wp_id: int = 0
    industry_ids: List[int] = field(default_factory=list)


def _detect_country(text: str) -> str:
    """Detect country from Spanish-language content text.

    Looks for nationality adjectives and country names.

    Args:
        text: Plain text content (HTML already stripped).

    Returns:
        Country name or empty string if not detected.
    """
    if not text:
        return ""

    # Check first 500 chars (country is usually mentioned early)
    snippet = text[:500]

    for pattern, country in _COUNTRY_PATTERNS.items():
        if re.search(pattern, snippet, re.IGNORECASE):
            return country

    return ""


def fetch_industries(
    client: httpx.Client,
) -> Dict[int, str]:
    """Fetch the industry taxonomy mapping (id → name).

    Args:
        client: HTTP client.

    Returns:
        Dict mapping industry ID to industry name.
    """
    try:
        response = client.get(
            INDUSTRY_ENDPOINT,
            params={"per_page": 100},
            timeout=15.0,
        )
        response.raise_for_status()
        data = response.json()
    except httpx.TimeoutException:
        logger.error("Timeout fetching StartupsLatam industries")
        return {}
    except httpx.HTTPError as e:
        logger.error("HTTP error fetching StartupsLatam industries: %s", e)
        return {}
    except Exception as e:
        logger.error("Error fetching StartupsLatam industries: %s", e)
        return {}

    industries = {}
    for item in data:
        if isinstance(item, dict):
            industries[item.get("id", 0)] = item.get("name", "")

    logger.info("StartupsLatam: loaded %d industry categories", len(industries))
    return industries


def _parse_startup(
    item: dict,
    industry_map: Dict[int, str],
) -> Optional[StartupsLatamCompany]:
    """Parse a single WP startup item into a StartupsLatamCompany.

    Args:
        item: Raw JSON item from WP REST API.
        industry_map: Industry ID → name mapping.

    Returns:
        StartupsLatamCompany or None if the item lacks a name.
    """
    title = item.get("title", {})
    name = _strip_html(title.get("rendered", "") if isinstance(title, dict) else str(title)).strip()
    if not name:
        return None

    slug = item.get("slug", name.lower().replace(" ", "-"))

    # Description from Yoast SEO or content
    yoast = item.get("yoast_head_json", {}) or {}
    description = yoast.get("description", "")
    if not description:
        content_html = item.get("content", {}).get("rendered", "")
        description = _strip_html(content_html)

    # Truncate very long descriptions
    if len(description) > 500:
        description = description[:497] + "..."

    # Resolve industry IDs
    industry_ids = item.get("industry", [])
    industry_names = [industry_map.get(iid, "") for iid in industry_ids if iid in industry_map]
    industry = industry_names[0] if industry_names else ""

    # Detect country from content text
    content_text = _strip_html(item.get("content", {}).get("rendered", ""))
    country = _detect_country(content_text)
    if not country:
        country = _detect_country(description)

    source_url = item.get("link", f"{BASE_URL}/startup/{slug}/")

    return StartupsLatamCompany(
        name=name,
        slug=slug,
        description=description,
        industry=industry,
        country=country,
        source_url=source_url,
        wp_id=item.get("id", 0),
        industry_ids=industry_ids,
    )


def fetch_startups_latam(
    source: DataSourceConfig,
    client: httpx.Client,
) -> List[StartupsLatamCompany]:
    """Fetch all startups from StartupsLatam WP REST API.

    Paginates through all pages (100 items per page).

    Args:
        source: Data source configuration.
        client: HTTP client.

    Returns:
        List of StartupsLatamCompany objects.
    """
    # First, fetch industry taxonomy
    industry_map = fetch_industries(client)

    url = source.url or STARTUP_ENDPOINT
    all_startups: List[StartupsLatamCompany] = []
    page = 1

    while True:
        params = {
            "per_page": PER_PAGE,
            "page": page,
            "_fields": "id,slug,title,content,industry,yoast_head_json,link",
        }

        try:
            response = client.get(url, params=params, timeout=15.0)
            response.raise_for_status()
            data = response.json()
        except httpx.TimeoutException:
            logger.error("Timeout fetching StartupsLatam page %d", page)
            break
        except httpx.HTTPError as e:
            logger.error("HTTP error fetching StartupsLatam page %d: %s", page, e)
            break
        except Exception as e:
            logger.error("Error fetching StartupsLatam page %d: %s", page, e)
            break

        if not data:
            break

        for item in data:
            if not isinstance(item, dict):
                continue
            startup = _parse_startup(item, industry_map)
            if startup:
                all_startups.append(startup)

        # Check if there are more pages
        total_pages = int(response.headers.get("X-WP-TotalPages", "1"))
        if page >= total_pages:
            break
        page += 1

    logger.info("StartupsLatam: fetched %d startups across %d pages", len(all_startups), page)
    return all_startups
