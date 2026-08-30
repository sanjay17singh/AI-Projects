"""T19 (+): a competitor with all fields "Not publicly available" (coverage=0)
still routes to compile_briefing once gap-retries are exhausted, and produces
a valid briefing section rather than failing compilation."""

from app.export.markdown_exporter import build_markdown
from app.graphs.edges import edge_coverage_check
from app.schemas.analysis import CompetitorProfile
from app.schemas.common import ALL_PROFILE_CATEGORIES, Confidence


def test_under_coverage_with_gap_retries_exhausted_proceeds_to_compile():
    state = {
        "analysis_results": [{"competitor_id": "c1", "evidence_coverage_score": 0.0}],
        "gap_retry_counts": {"c1": 1},  # already used its one gap-research attempt
        "max_gap_retries": 1,
        "coverage_threshold": 0.6,
        "competitors": [{"id": "c1", "name": "Acme"}],
    }
    assert edge_coverage_check(state) == "compile_briefing"


def test_all_unknown_profile_still_produces_valid_markdown():
    profile = CompetitorProfile(
        competitor_id="c1",
        competitor_name="Acme",
        evidence_coverage_score=0.0,
        overall_confidence=Confidence.LOW,
    )
    markdown = build_markdown("Target Co", [profile], {})
    assert "Acme" in markdown
    assert markdown.count("Not publicly available.") == len(ALL_PROFILE_CATEGORIES)
    assert "Coverage score: 0.00" in markdown
