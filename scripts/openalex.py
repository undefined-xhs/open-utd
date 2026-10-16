"""Reserved optional enrichment boundary; Crossref-only builds need no API key."""


def enrich(*args, **kwargs):
    raise NotImplementedError("OpenAlex enrichment is not enabled. The production pipeline currently uses Crossref; DOI/ORCID identities are retained for future enrichment.")
