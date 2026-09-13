"""Structural tests for the LLM-as-judge callables: each judge must call
`with_structured_output` with the right model class and return the expected
shape. Uses `tests.fixtures.fake_llm.FakeChatModel` (the repo's existing
LLM-mocking pattern) — never a live API call."""

from unittest.mock import patch

from app.schemas.analysis import ClaimField, CompetitorProfile, Conflict, ConflictingValue, RedFlag
from eval.judges.conflict_judge import ConflictJudgeVerdict, judge_conflict
from eval.judges.faithfulness_judge import FaithfulnessJudgeVerdict, judge_faithfulness
from eval.judges.red_flag_judge import RedFlagMatchResult, judge_red_flags
from eval.schemas.eval_models import GoldConflict, GoldRedFlag
from tests.fixtures.fake_llm import FakeChatModel


def test_judge_red_flags_calls_structured_output_and_returns_match_result():
    expected = RedFlagMatchResult(
        matched_gold_ids=["RF-1"],
        correct_agent_flag_ids=["agent-1"],
        reason="matched on price hike",
    )
    fake = FakeChatModel({RedFlagMatchResult: expected})

    agent_flags = [
        RedFlag(
            red_flag_id="agent-1",
            type="pricing",
            severity="high",
            description="Raised prices 20%",
            evidence_ids=["EV-1"],
        )
    ]
    gold_flags = [
        GoldRedFlag(
            red_flag_id="RF-1",
            type="pricing",
            description="Price increase",
            severity="high",
            is_critical=False,
        )
    ]

    with patch("eval.judges.red_flag_judge.get_chat_model", return_value=fake):
        result = judge_red_flags(agent_flags, gold_flags, evidence=[], settings=object())

    assert result == expected
    assert RedFlagMatchResult in fake.structured_runnables
    assert fake.structured_runnables[RedFlagMatchResult].call_count == 1


def test_judge_conflict_calls_structured_output_and_returns_verdict():
    expected = ConflictJudgeVerdict(score=4, reason="Correctly resolved with provenance")
    fake = FakeChatModel({ConflictJudgeVerdict: expected})

    gold_conflict = GoldConflict(
        field="pricing",
        value_a="$10/mo",
        value_b="$12/mo",
        evidence_ids_a=["EV-1"],
        evidence_ids_b=["EV-2"],
        expected_preferred_value="$12/mo",
    )
    agent_conflict = Conflict(
        field="pricing",
        values=[
            ConflictingValue(value="$10/mo", evidence_ids=["EV-1"]),
            ConflictingValue(value="$12/mo", evidence_ids=["EV-2"]),
        ],
        resolution_status="resolved",
        preferred_value="$12/mo",
        resolution_reason="More recent source",
    )

    with patch("eval.judges.conflict_judge.get_chat_model", return_value=fake):
        result = judge_conflict(gold_conflict, agent_conflict, evidence=[], settings=object())

    assert result == expected
    assert ConflictJudgeVerdict in fake.structured_runnables


def test_judge_conflict_handles_missing_agent_conflict():
    expected = ConflictJudgeVerdict(score=0, reason="Agent never reported this conflict")
    fake = FakeChatModel({ConflictJudgeVerdict: expected})
    gold_conflict = GoldConflict(field="pricing", value_a="$10/mo", value_b="$12/mo")

    with patch("eval.judges.conflict_judge.get_chat_model", return_value=fake):
        result = judge_conflict(gold_conflict, None, evidence=[], settings=object())

    assert result.score == 0


def test_judge_faithfulness_calls_structured_output_and_returns_verdict():
    expected = FaithfulnessJudgeVerdict(
        score=3, unsupported_items=["over-claimed detail"], reason="ok"
    )
    fake = FakeChatModel({FaithfulnessJudgeVerdict: expected})

    profile = CompetitorProfile(
        competitor_id="c1",
        competitor_name="Acme",
        pricing=[ClaimField(value="$10/mo", evidence_ids=["EV-1"])],
    )

    with patch("eval.judges.faithfulness_judge.get_chat_model", return_value=fake):
        result = judge_faithfulness(profile, evidence=[], settings=object())

    assert result == expected
    assert FaithfulnessJudgeVerdict in fake.structured_runnables
