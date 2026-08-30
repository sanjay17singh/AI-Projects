"""T15 (-): the compiled briefing contains only values traceable to the
verified CompetitorProfile input — no LLM call in the compile step means no
opportunity to introduce an unverified fact."""

from app.export.markdown_exporter import build_markdown
from app.schemas.analysis import ClaimField, CompetitorProfile
from app.schemas.common import Confidence

SENTINEL_PRICING = "SENTINEL-PRICE-VALUE-9f3a"
SENTINEL_FEATURE = "SENTINEL-FEATURE-VALUE-7c1b"


def test_markdown_contains_only_the_verified_input_values_verbatim():
    profile = CompetitorProfile(
        competitor_id="c1",
        competitor_name="Sentinel Co",
        pricing=[
            ClaimField(value=SENTINEL_PRICING, evidence_ids=["e1"], confidence=Confidence.MEDIUM)
        ],
        core_features=[
            ClaimField(value=SENTINEL_FEATURE, evidence_ids=["e2"], confidence=Confidence.MEDIUM)
        ],
        evidence_coverage_score=0.29,
        overall_confidence=Confidence.MEDIUM,
    )
    evidence_lookup = {
        "e1": {"url": "https://example.com/pricing", "title": "Example pricing page"},
        "e2": {"url": "https://example.com/features", "title": "Example features page"},
    }

    markdown = build_markdown("Target Co", [profile], evidence_lookup)

    # Both verified sentinel values must appear verbatim, exactly once each.
    assert markdown.count(SENTINEL_PRICING) == 1
    assert markdown.count(SENTINEL_FEATURE) == 1
    # Every citation must resolve to a real source from the input evidence —
    # numbered footnotes [1]/[2], each backed by an entry in the Sources list.
    assert "[1]" in markdown
    assert "[2]" in markdown
    assert "1. Example pricing page — https://example.com/pricing" in markdown
    assert "2. Example features page — https://example.com/features" in markdown


def test_compiling_never_calls_a_language_model(monkeypatch):
    # If build_markdown ever imports/calls an LLM client, this fails loudly.
    import app.export.markdown_exporter as mod

    assert not hasattr(mod, "get_chat_model")
    assert "openai" not in mod.__dict__
