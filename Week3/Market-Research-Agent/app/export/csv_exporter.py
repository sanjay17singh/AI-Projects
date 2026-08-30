import csv
import io

from app.schemas.analysis import CompetitorProfile
from app.schemas.common import ALL_PROFILE_CATEGORIES

# "sources" holds resolved URLs, not raw evidence_id UUIDs — a spreadsheet
# consumer has no use for an internal database key, and there's no natural
# footnote/cross-reference mechanism in CSV the way there is in Markdown/PDF,
# so we resolve straight to the real source here instead of numbering.
CSV_COLUMNS = ["competitor", "category", "field", "value", "confidence", "sources"]


def build_csv(profiles: list[CompetitorProfile], evidence_lookup: dict[str, dict]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(CSV_COLUMNS)

    for profile in profiles:
        for category in ALL_PROFILE_CATEGORIES:
            for claim in getattr(profile, category):
                sources = [
                    evidence_lookup.get(eid, {}).get("url") or eid for eid in claim.evidence_ids
                ]
                writer.writerow(
                    [
                        profile.competitor_name,
                        category,
                        category,
                        claim.value,
                        claim.confidence.value,
                        ";".join(sources),
                    ]
                )

    return buffer.getvalue()
