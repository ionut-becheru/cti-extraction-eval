"""
Public-CTI corpus ingestion package.

Each adapter exposes one function:
    fetch_and_yield_records(cache_dir: Path, max_records: int | None, **kwargs)
        -> Iterator[dict]

yielding normalized records ({raw_text, source_forum, source, timestamp, url,
file_type, file_info}) ready for the DarkWeb pipeline.

The orchestrator in __main__.py iterates adapters, dedupes, and writes
a single JSON array to disk that the pipeline ingests via ijson.
"""
from . import mitre_attack, nvd, cisa_kev, aptner, dnrti, cyner, stackexchange

SOURCES = {
    "mitre":         mitre_attack,
    "nvd":           nvd,
    "cisa":          cisa_kev,
    "aptner":        aptner,
    "dnrti":         dnrti,
    "cyner":         cyner,
    "stackexchange": stackexchange,
}
