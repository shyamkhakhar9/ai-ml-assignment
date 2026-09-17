"""Download public Singapore travel sources into data/raw as Markdown."""

from __future__ import annotations

import argparse
import json
import re
from typing import Any

import httpx
from bs4 import BeautifulSoup

from kb.paths import RAW_DIR, SOURCES_PATH, USER_AGENT

WIKIVOYAGE_API = "https://en.wikivoyage.org/w/api.php"


def load_source_catalog() -> dict[str, Any]:
    with SOURCES_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def _client() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": USER_AGENT, "Accept": "application/json,text/html"},
        follow_redirects=True,
        timeout=60.0,
    )


def fetch_wikivoyage_extract(title: str = "Singapore") -> str:
    params = {
        "action": "query",
        "titles": title,
        "prop": "extracts",
        "explaintext": 1,
        "redirects": 1,
        "format": "json",
        "formatversion": 2,
    }
    with _client() as client:
        response = client.get(WIKIVOYAGE_API, params=params)
        response.raise_for_status()
        pages = response.json()["query"]["pages"]
        extract = pages[0].get("extract") or ""
    if not extract.strip():
        raise RuntimeError(f"Wikivoyage returned an empty extract for {title}")
    extract = _wikitext_headings_to_markdown(extract.strip())
    return (
        "# Wikivoyage Singapore Travel Guide\n\n"
        "Source: https://en.wikivoyage.org/wiki/Singapore\n"
        "License: Creative Commons Attribution-ShareAlike.\n\n"
        f"{extract}\n"
    )


def _wikitext_headings_to_markdown(extract: str) -> str:
    extract = re.sub(r"^=== (.+) ===\s*$", r"### \1", extract, flags=re.MULTILINE)
    extract = re.sub(r"^== (.+) ==\s*$", r"## \1", extract, flags=re.MULTILINE)
    return extract


def html_to_markdown(html: str, title: str, url: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    text = soup.get_text("\n", strip=True)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    body = "\n".join(lines)
    for marker in (title, "Essential Singapore", "Itineraries", "Things To Do"):
        idx = body.find(marker)
        if idx > 200:
            body = body[idx:]
            break
    return f"# {title}\n\nSource: {url}\n\n{body}\n"


def fetch_html_pages(pages: list[dict[str, str]], combined_title: str, canonical_url: str) -> str:
    parts = [f"# {combined_title}\n", f"Canonical source: {canonical_url}\n"]
    with _client() as client:
        for page in pages:
            try:
                response = client.get(page["url"])
                response.raise_for_status()
                md = html_to_markdown(response.text, page["title"], page["url"])
                parts.append(md)
                parts.append("\n---\n")
                print(f"  fetched {page['url']} ({len(md)} chars)")
            except httpx.HTTPError as exc:
                print(f"  skipped {page['url']}: {exc}")
    return "\n".join(parts)


def write_raw(filename: str, content: str) -> None:
    path = RAW_DIR / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"Wrote {path} ({len(content)} chars)")


def fetch_all(*, refresh_web: bool = False) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    catalog = load_source_catalog()

    wikivoyage = fetch_wikivoyage_extract()
    write_raw("wikivoyage-singapore.md", wikivoyage)

    if not refresh_web:
        print(
            "Kept curated Visit Singapore Markdown in data/raw/. "
            "Re-scrape those pages with: python -m kb.fetch_sources --refresh-web"
        )
        print(f"Fetched Wikivoyage for {catalog['destination']}.")
        return

    essential_pages = [
        {
            "title": "Visit Singapore: Essential Travel Information",
            "url": "https://www.visitsingapore.com/travel-guide-tips/traveller-information/",
        }
    ]
    write_raw(
        "visit-singapore-essential.md",
        fetch_html_pages(
            essential_pages,
            "Visit Singapore: Essential Travel Information",
            essential_pages[0]["url"],
        ),
    )

    itinerary_pages = [
        {
            "title": "Singapore Itineraries hub",
            "url": "https://www.visitsingapore.com/travel-tips/travelling-to-singapore/itineraries/",
        },
        {
            "title": "4 Days in Singapore",
            "url": "https://www.visitsingapore.com/travel-tips/travelling-to-singapore/itineraries/4-days-in-singapore/",
        },
        {
            "title": "24 Hours in Singapore",
            "url": "https://www.visitsingapore.com/travel-tips/travelling-to-singapore/itineraries/24-hours-in-singapore/",
        },
        {
            "title": "Places to visit with family",
            "url": "https://www.visitsingapore.com/travel-tips/travelling-to-singapore/itineraries/places-to-visit-with-family/",
        },
        {
            "title": "Singapore city explorer guide",
            "url": "https://www.visitsingapore.com/travel-tips/travelling-to-singapore/itineraries/singapore-city-tour-guide/",
        },
        {
            "title": "Outdoor adventure itinerary",
            "url": "https://www.visitsingapore.com/travel-tips/travelling-to-singapore/itineraries/outdoor-adventure-activities-in-singapore/",
        },
        {
            "title": "Singapore food guide",
            "url": "https://www.visitsingapore.com/travel-tips/travelling-to-singapore/itineraries/singapore-food-guide/",
        },
    ]
    write_raw(
        "visit-singapore-itineraries.md",
        fetch_html_pages(
            itinerary_pages,
            "Visit Singapore: Sample Itineraries",
            itinerary_pages[0]["url"],
        ),
    )

    things_pages = [
        {
            "title": "Things to do in Singapore",
            "url": "https://www.visitsingapore.com/see-do-singapore/",
        },
        {
            "title": "Family fun",
            "url": "https://www.visitsingapore.com/things-to-do/top-things-to-do/family-fun/",
        },
        {
            "title": "Gardens by the Bay",
            "url": "https://www.visitsingapore.com/neighbourhood/featured-neighbourhood/marina-bay/gardens-by-the-bay/",
        },
        {
            "title": "Chinatown",
            "url": "https://www.visitsingapore.com/neighbourhood/featured-neighbourhood/chinatown/",
        },
        {
            "title": "Buddha Tooth Relic Temple",
            "url": "https://www.visitsingapore.com/neighbourhood/featured-neighbourhood/chinatown/buddha-tooth-relic-temple/",
        },
        {
            "title": "Peranakan Museum",
            "url": "https://www.visitsingapore.com/neighbourhood/featured-neighbourhood/civic-district/peranakan-museum/",
        },
        {
            "title": "Little India",
            "url": "https://www.visitsingapore.com/neighbourhood/featured-neighbourhood/little-india/",
        },
        {
            "title": "Kampong Gelam",
            "url": "https://www.visitsingapore.com/neighbourhood/featured-neighbourhood/kampong-gelam/",
        },
        {
            "title": "Green spaces",
            "url": "https://www.visitsingapore.com/things-to-do/urban-wellness/green-spaces/",
        },
    ]
    write_raw(
        "visit-singapore-things-to-do.md",
        fetch_html_pages(
            things_pages,
            "Visit Singapore: Things to Do",
            things_pages[0]["url"],
        ),
    )

    print(f"Fetched sources for {catalog['destination']}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download Singapore knowledge-base sources")
    parser.add_argument(
        "--refresh-web",
        action="store_true",
        help="Also re-scrape Visit Singapore HTML (can be noisy on JS pages)",
    )
    args = parser.parse_args()
    fetch_all(refresh_web=args.refresh_web)
