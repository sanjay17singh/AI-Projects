"""Semantic equivalence between GoldFact.statement and an agent's claims for
that fact's category — wording differs so exact-string matching doesn't
work. Feeds eval/evaluators/coverage.py (ground_truth_coverage)."""

from pydantic import BaseModel, Field

from app.clients.openai_client import get_chat_model
from app.config import Settings
from app.schemas.analysis import CompetitorProfile
from eval.judges.prompts import build_judge_system_prompt
from eval.schemas.eval_models import GoldFact


class CoverageMatchResult(BaseModel):
    matched_items: list[str] = Field(
        default_factory=list,
        description="fact_id of every GoldFact whose statement is recovered by some agent claim.",
    )
    reason: str


_TASK = (
    "You are checking how many gold (expected) facts about a competitor were actually recovered "
    "by an agent's extracted claims, using semantic equivalence rather than exact wording — a "
    "gold fact is 'recovered' if any agent claim in the matching category states the same "
    "underlying fact, even with different phrasing, units, or level of detail (as long as it is "
    "not contradicted).\n\n"
    "Never mark a gold fact as recovered unless some actual agent claim supports it. Return the "
    "fact_id of every gold fact you judge as recovered in matched_items."
)


def judge_coverage(
    gold_facts: list[GoldFact],
    profile: CompetitorProfile,
    settings: Settings,
) -> CoverageMatchResult:
    model = get_chat_model(settings, fast=False, temperature=0.0).with_structured_output(
        CoverageMatchResult
    )

    facts_block = "\n".join(
        f"- fact_id={f.fact_id!r} category={f.category!r}: {f.statement}" for f in gold_facts
    ) or "(no gold facts defined)"

    categories = sorted({f.category for f in gold_facts})
    claims_block_parts = []
    for category in categories:
        claims = getattr(profile, category, [])
        claim_texts = "; ".join(c.value for c in claims if not c.is_unsupported) or "(no claims)"
        claims_block_parts.append(f"- [{category}] {claim_texts}")
    claims_block = "\n".join(claims_block_parts) or "(no relevant categories in profile)"

    messages = [
        ("system", build_judge_system_prompt(_TASK)),
        (
            "human",
            f"Gold facts:\n{facts_block}\n\n"
            f"Agent claims by category:\n{claims_block}",
        ),
    ]
    return model.invoke(messages)
