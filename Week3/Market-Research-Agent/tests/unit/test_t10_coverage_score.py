"""T10 (+): coverage score computes 3/10 when only 3 of 10 categories have
evidence-backed fields."""

from app.schemas.analysis import ClaimField, ExtractedProfile
from app.schemas.common import COVERAGE_CATEGORIES, Confidence
from app.services.analysis_service import compute_coverage_score


def test_coverage_score_is_three_of_ten():
    profile = ExtractedProfile(
        pricing=[ClaimField(value="$29/mo", evidence_ids=["e1"], confidence=Confidence.MEDIUM)],
        core_features=[
            ClaimField(value="CRM features", evidence_ids=["e2"], confidence=Confidence.MEDIUM)
        ],
        positioning=[
            ClaimField(
                value="Positions as simple CRM", evidence_ids=["e3"], confidence=Confidence.LOW
            )
        ],
        # target_customers, differentiators, announcements, recent_news,
        # free_trial, customer_reviews, notable_customers left as default unsupported
    )
    score = compute_coverage_score(profile)
    assert score == round(3 / len(COVERAGE_CATEGORIES), 3)
    assert len(COVERAGE_CATEGORIES) == 10
