"""Pure metadata normalization. No network, markup rendering, or guessed identities."""
from __future__ import annotations

import html
import re
from datetime import date
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit

from defusedxml import ElementTree


def clean_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_doi(value: object) -> str | None:
    if not value:
        return None
    doi = unquote(str(value).strip())
    doi = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", doi, flags=re.I).strip().lower()
    if not re.fullmatch(r"10\.\d{4,9}/[^\s\x00-\x1f]+", doi):
        raise ValueError(f"Invalid DOI: {str(value)[:120]}")
    return doi


def normalize_issn(value: object) -> str:
    compact = str(value).strip().upper().replace("-", "")
    if not re.fullmatch(r"\d{7}[\dX]", compact):
        raise ValueError(f"Invalid ISSN: {value}")
    checksum = sum(int(d) * (8-i) for i, d in enumerate(compact[:7]))
    check = (11 - checksum % 11) % 11
    if compact[-1] != ("X" if check == 10 else str(check)):
        raise ValueError(f"Invalid ISSN checksum: {value}")
    return compact[:4] + "-" + compact[4:]


def normalize_orcid(value: object) -> str | None:
    if not value:
        return None
    raw = re.sub(r"^https?://orcid\.org/", "", str(value).strip(), flags=re.I).upper()
    if not re.fullmatch(r"\d{4}-\d{4}-\d{4}-\d{3}[\dX]", raw):
        raise ValueError("Invalid ORCID format")
    total = 0
    for digit in raw.replace("-", "")[:-1]:
        total = (total + int(digit)) * 2
    check = (12 - total % 11) % 11
    if raw[-1] != ("X" if check == 10 else str(check)):
        raise ValueError("Invalid ORCID checksum")
    return raw


def safe_url(value: object) -> str | None:
    if not value:
        return None
    value = str(value).strip()
    parsed = urlsplit(value)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        return None
    if any(ord(char) < 32 for char in value):
        return None
    return value


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden += 1
        if tag in {"p", "br", "div", "jats:p"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.hidden = max(0, self.hidden-1)
        if tag in {"p", "div", "jats:p"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def plain_text(value: object) -> str | None:
    if not value:
        return None
    value = str(value)
    # Reject entity declarations rather than asking a parser to recover hostile XML.
    if re.search(r"<!\s*(?:DOCTYPE|ENTITY)", value, re.I):
        raise ValueError("XML entities/DOCTYPE are not allowed in metadata")
    if "<" not in value:
        return clean_text(html.unescape(value)) or None
    try:
        ElementTree.fromstring('<root xmlns:jats="http://jats.nlm.nih.gov">' + value + '</root>')
    except ElementTree.ParseError:
        pass  # Deposits often contain non-XML HTML; HTMLParser never resolves entities remotely.
    parser = _TextExtractor()
    parser.feed(value)
    lines = [clean_text(line) for line in "".join(parser.parts).splitlines()]
    return "\n\n".join(line for line in lines if line) or None


def date_parts(value: object) -> tuple[str | None, str | None, int | None]:
    if not isinstance(value, dict) or not value.get("date-parts"):
        return None, None, None
    parts = value["date-parts"][0]
    if not isinstance(parts, list) or not 1 <= len(parts) <= 3:
        raise ValueError("Invalid publication date parts")
    if any(not isinstance(part, int) for part in parts):
        raise ValueError("Publication date parts must be integers")
    date(parts[0], parts[1] if len(parts)>1 else 1, parts[2] if len(parts)>2 else 1)
    rendered = f"{parts[0]:04d}" + "".join(f"-{part:02d}" for part in parts[1:])
    return rendered, ("year", "month", "day")[len(parts)-1], parts[0]


def publication_date(record: dict) -> tuple[str | None, str | None, int | None]:
    # Final issue date takes precedence over online-first date when assigned.
    keys = ("published-print", "published", "published-online", "issued")
    for key in keys:
        result = date_parts(record.get(key))
        if result[0]:
            return result
    return None, None, None


def issue_identity(volume: object, number: object, year: int | None) -> tuple[str, str, str] | None:
    volume, number = clean_text(volume), clean_text(number)
    if not volume or not number:
        return None
    # Unicode dashes and harmless whitespace changes do not create new issues.
    canonical = lambda text: re.sub(r"\s+", "", text.translate(str.maketrans("–—−", "---"))).casefold()
    return f"v:{canonical(volume)}|i:{canonical(number)}", volume, number


def normalize_authors(record: dict) -> list[dict]:
    authors = []
    for author in record.get("author") or []:
        name = clean_text(author.get("name")) or clean_text(" ".join(filter(None, [author.get("given"), author.get("family")])))
        if not name:
            continue
        try:
            orcid = normalize_orcid(author.get("ORCID"))
        except ValueError:
            orcid = None  # Invalid supplied IDs cannot establish identity.
        authors.append({"byline_name": name, "orcid": orcid,
                        "affiliation_text": "; ".join(clean_text(a.get("name")) for a in author.get("affiliation", []) if a.get("name")) or None})
    return authors


def normalize_record(record: dict) -> dict:
    titles = record.get("title") or []
    if isinstance(titles, str):
        titles = [titles]
    title = plain_text(titles[0]) if titles else None
    if not title:
        raise ValueError("Article lacks a title")
    pub_date, precision, year = publication_date(record)
    return {
        "doi": normalize_doi(record.get("DOI")), "title": title,
        # The SQLite snapshot is public too. Do not persist unlicensed abstracts.
        "abstract_text": None,
        # Crossref work-level licenses are not sufficient evidence of abstract rights.
        "abstract_source": "Crossref" if record.get("abstract") else None,
        "abstract_license_url": None, "abstract_display_status": "unknown",
        "abstract_rights_verified": 0,
        "publication_date": pub_date, "date_precision": precision, "publication_year": year,
        "pages": clean_text(record.get("page")) or None, "article_type": record.get("type"),
        "landing_url": safe_url(record.get("URL")), "metadata_source": "Crossref",
        "source_modified_at": (record.get("indexed") or {}).get("date-time"),
        "authors": normalize_authors(record),
        "issue": issue_identity(record.get("volume"), record.get("issue"), year),
    }
