import pytest

from scripts.normalize import (date_parts, issue_identity, normalize_doi, normalize_issn,
                               normalize_orcid, plain_text, publication_date, safe_url)


@pytest.mark.parametrize("value", ["10.1234/ABC", "doi:10.1234/ABC", "https://doi.org/10.1234%2FABC", " https://dx.doi.org/10.1234/AbC "])
def test_doi_prefix_case_and_decoding(value):
    assert normalize_doi(value) == "10.1234/abc"


@pytest.mark.parametrize("value", ["not-a-doi", "10.12/no", "https://evil.invalid/x", "10.1234/abc%0Adef"])
def test_invalid_doi_rejected(value):
    with pytest.raises(ValueError):
        normalize_doi(value)


def test_issn_checksum_and_orcid():
    assert normalize_issn("00251909") == "0025-1909"
    with pytest.raises(ValueError):
        normalize_issn("0025-1908")
    assert normalize_orcid("https://orcid.org/0000-0002-1825-0097") == "0000-0002-1825-0097"
    with pytest.raises(ValueError):
        normalize_orcid("0000-0002-1825-0098")


@pytest.mark.parametrize("parts,rendered,precision", [([2024], "2024", "year"), ([2024,2], "2024-02", "month"), ([2024,2,29], "2024-02-29", "day")])
def test_date_precision(parts, rendered, precision):
    assert date_parts({"date-parts": [parts]}) == (rendered, precision, 2024)


def test_invalid_date_and_print_priority():
    with pytest.raises(ValueError):
        date_parts({"date-parts": [[2023,2,29]]})
    assert publication_date({"published-print": {"date-parts": [[2024]]}, "published-online": {"date-parts": [[2023,12,2]]}}) == ("2024", "year", 2024)


def test_jats_is_plain_text_and_entities_are_forbidden():
    assert plain_text("<jats:p>Hello <jats:italic>world</jats:italic>.</jats:p><p>Next</p>") == "Hello world.\n\nNext"
    assert plain_text("<p>Hello</p><script>alert(1)</script>") == "Hello"
    with pytest.raises(ValueError):
        plain_text('<!DOCTYPE x [<!ENTITY x SYSTEM "file:///etc/passwd">]><p>&x;</p>')


def test_issue_and_urls():
    assert issue_identity("12", "1–2", 2024)[0] == issue_identity(" 12 ", "1-2", 2025)[0]
    assert issue_identity("12", "S1", 2024)[2] == "S1"
    assert issue_identity("12", None, 2024) is None
    assert safe_url("javascript:alert(1)") is None
    assert safe_url("https://user:pass@example.org") is None
