"""Pure footnote-style citation numbering, shared by the Markdown/PDF
exporters and the Streamlit briefing page. No DB access here — resolving an
evidence_id to a real title/url happens in services/export_service.py
(the DB-touching layer); this module only assigns [1], [2], ... numbers and
builds the ordered source list, given that lookup as plain data.

Numbering is scoped to whatever sequence of evidence_id lists you pass in —
call build_citation_index() once per competitor so each one gets its own
[1]..[N], restarting at 1, matching how footnotes work in a real report."""

from collections.abc import Iterable
from dataclasses import dataclass, field


@dataclass
class Source:
    number: int
    evidence_id: str
    title: str
    url: str


@dataclass
class CitationIndex:
    numbers: dict[str, int] = field(default_factory=dict)
    sources: list[Source] = field(default_factory=list)

    def number_for(self, evidence_id: str) -> int | None:
        return self.numbers.get(evidence_id)

    def marker_for(self, evidence_id: str) -> str:
        number = self.numbers.get(evidence_id)
        return f"[{number}]" if number is not None else "[?]"


def build_citation_index(
    evidence_id_sequences: Iterable[list[str]], evidence_lookup: dict[str, dict]
) -> CitationIndex:
    index = CitationIndex()
    for ids in evidence_id_sequences:
        for evidence_id in ids:
            if evidence_id in index.numbers:
                continue
            number = len(index.sources) + 1
            index.numbers[evidence_id] = number
            info = evidence_lookup.get(evidence_id, {})
            index.sources.append(
                Source(
                    number=number,
                    evidence_id=evidence_id,
                    title=info.get("title") or "Source",
                    url=info.get("url") or "",
                )
            )
    return index
