"""Optional aggregate Master Quality Judge — five independent 0-4 dimension
judgments over the full scenario+profile+evidence, deliberately excluding
cost and latency (operational performance stays separate from answer
quality). Feeds eval/evaluators/quality_score.compute_quality_score."""

from app.clients.openai_client import get_chat_model
from app.config import Settings
from app.schemas.analysis import CompetitorProfile
from eval.judges.prompts import build_judge_system_prompt, format_evidence_block
from eval.schemas.eval_models import GoldenScenario, QualityJudgeVerdict

_TASK = (
    "You are the Master Quality Judge for a competitor research profile produced by an agent. "
    "Score five independent dimensions, each 0-4 (4=excellent, 0=failing), based only on the "
    "scenario, the gold reference outputs, the agent's profile, and the frozen evidence "
    "provided:\n\n"
    "- factual_correctness: are the agent's claims factually consistent with the evidence and "
    "the gold reference outputs?\n"
    "- evidence_faithfulness: does every material claim stay within what its cited evidence "
    "actually supports?\n"
    "- coverage: how much of the gold expected information did the agent recover?\n"
    "- conflict_handling: were any conflicting values in the evidence identified and handled "
    "appropriately (preserved, correctly resolved or correctly left unresolved)?\n"
    "- red_flag_handling: were the expected red flags identified, without fabricating flags that "
    "aren't supported?\n\n"
    "Do NOT factor cost or latency into any of these scores — this judge is about answer quality "
    "only. Keep the overall reason concise."
)


def judge_quality(
    scenario: GoldenScenario,
    profile: CompetitorProfile,
    evidence: list[dict],
    settings: Settings,
) -> QualityJudgeVerdict:
    model = get_chat_model(settings, fast=False, temperature=0.0).with_structured_output(
        QualityJudgeVerdict
    )

    ref = scenario.reference_outputs
    gold_block = (
        f"expected_claims={ref.expected_claims}\n"
        f"expected_red_flags={[f.model_dump() for f in ref.expected_red_flags]}\n"
        f"expected_conflicts={[c.model_dump() for c in ref.expected_conflicts]}\n"
        f"gold_facts={[f.model_dump() for f in ref.gold_facts]}\n"
        f"expected_unknowns={ref.expected_unknowns}\n"
        f"expected_current_values={ref.expected_current_values}"
    )

    messages = [
        ("system", build_judge_system_prompt(_TASK)),
        (
            "human",
            f"Scenario question: {scenario.inputs.question}\n"
            f"Target company: {scenario.inputs.target_company}\n\n"
            f"Gold reference outputs:\n{gold_block}\n\n"
            f"Agent-produced profile:\n{profile.model_dump_json(indent=2)}\n\n"
            f"Frozen evidence:\n{format_evidence_block(evidence)}",
        ),
    ]
    return model.invoke(messages)
