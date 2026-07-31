"""Google News RSS client — free, no API key, India-localized.

We query the public RSS search endpoint for a legislator and parse the returned <item>s into headlines.
Only the headline + publisher + date + a short snippet are kept; each links out to the source. Raw feed
XML is cached for provenance like every other source.

URL scheme:
  https://news.google.com/rss/search?q=<query>&hl=en-IN&gl=IN&ceid=IN:en
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus
from xml.etree import ElementTree as ET

from neta_core.http import client as http
from neta_core.pipeline import (
    ExtractionContext,
    HttpExtractionRequest,
    HttpSourceAdapter,
    RawArtifact,
    SourceAdapter,
)
from neta_core.provenance import cache_raw

# Google sometimes serves the bot UA a thin page; a browser-like UA gets the full feed.
_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
SOURCE_ID = "news.google_feed"


@dataclass(slots=True)
class ParsedArticle:
    title: str
    url: str
    publisher: str | None
    published_at: date | None
    snippet: str | None


def build_query(name: str, party: str | None = None, constituency: str | None = None) -> str:
    """Bias the search toward the politician (exact name + an office/party/seat context)."""
    ctx = ['MP', '"Lok Sabha"', '"Rajya Sabha"']
    if party:
        ctx.append(f'"{party}"')
    if constituency:
        ctx.append(f'"{constituency}"')
    return f'"{name}" ({" OR ".join(ctx)})'


def feed_url(query: str) -> str:
    return f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-IN&gl=IN&ceid=IN:en"


def _strip_html(s: str | None) -> str:
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", " ", s)
    s = s.replace("&nbsp;", " ").replace("&amp;", "&").replace("&#39;", "'").replace("&quot;", '"')
    return re.sub(r"\s+", " ", s).strip()


def _pub_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return parsedate_to_datetime(raw).date()
    except (TypeError, ValueError):
        return None


def extract_news(
    name: str,
    party: str | None = None,
    constituency: str | None = None,
    slug: str = "x",
    *,
    context: ExtractionContext,
    adapter: SourceAdapter[HttpExtractionRequest] | None = None,
) -> RawArtifact:
    """Fetch one legislator feed as a raw envelope, without parsing or canonical writes."""
    url = feed_url(build_query(name, party, constituency))
    extractor = adapter if adapter is not None else HttpSourceAdapter()
    return extractor.extract(
        HttpExtractionRequest(
            source_id=SOURCE_ID,
            native_id=f"legislator:{slug}",
            url=url,
            default_content_type="application/rss+xml",
            headers={"User-Agent": _UA},
        ),
        context=context,
    )


def parse_news_artifact(artifact: RawArtifact) -> list[ParsedArticle]:
    """Convert a stored Google News response with the existing feed parsing rules."""
    return _parse_news_payload(artifact.payload)


def fetch_news(
    name: str,
    party: str | None = None,
    constituency: str | None = None,
    slug: str = "x",
    *,
    context: ExtractionContext | None = None,
) -> tuple[list[ParsedArticle], str | None]:
    """Fetch + parse the news feed for one legislator. Returns (articles, raw_cache_relpath)."""
    if context is not None:
        artifact = extract_news(name, party, constituency, slug, context=context)
        return parse_news_artifact(artifact), artifact.provenance_ref

    url = feed_url(build_query(name, party, constituency))
    resp = http.get(url, headers={"User-Agent": _UA})
    rel = cache_raw(resp.content, suffix=f"_news_{slug}.xml")
    return _parse_news_payload(resp.content), rel


def _parse_news_payload(content: bytes) -> list[ParsedArticle]:
    out: list[ParsedArticle] = []
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return out
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        if not title or not link:
            continue
        src_el = item.find("source")
        publisher = (src_el.text or "").strip() if src_el is not None else None
        # Google News titles end with " - Publisher"; drop that for a clean headline.
        if publisher and title.endswith(f" - {publisher}"):
            title = title[: -len(f" - {publisher}")].strip()
        snippet = _strip_html(item.findtext("description"))
        if snippet and (snippet == title or title in snippet):
            snippet = None  # description is just the headline/link-list — not a useful snippet
        out.append(ParsedArticle(
            title=title, url=link, publisher=publisher,
            published_at=_pub_date(item.findtext("pubDate")),
            snippet=snippet[:240] if snippet else None,
        ))
    return out
