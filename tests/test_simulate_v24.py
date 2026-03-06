"""Tests for V2.4 simulate_conversation with FactExtractor + adaptive frequency."""

import json
from unittest.mock import MagicMock, patch

from super_brain.models import (
    Fact, Reality, FactExtractionResult, Soul, ThinkSlowResult, ThinkFastResult,
    PersonalityDNA, SampleSummary, Trait,
)


def test_simulate_returns_soul_when_fact_extractor_provided():
    """simulate_conversation returns (conversation, ts_results, soul) with fact_extractor."""
    from eval_conversation import simulate_conversation, Chatter, PersonalitySpeaker
    from super_brain.profile_gen import generate_profile
    from super_brain.think_slow import ThinkSlow
    from super_brain.fact_extractor import FactExtractor

    # We need to mock the LLM calls
    with patch.object(Chatter, "next_message", return_value="Tell me more about that."):
        with patch.object(PersonalitySpeaker, "respond", return_value="I work as an engineer."):
            with patch.object(ThinkSlow, "extract") as mock_ts:
                with patch.object(FactExtractor, "extract") as mock_fe:
                    # ThinkSlow mock return
                    mock_profile = PersonalityDNA(
                        id="partial",
                        sample_summary=SampleSummary(
                            total_tokens=0, conversation_count=0,
                            date_range=["u", "u"], contexts=["t"],
                            confidence_overall=0.5,
                        ),
                    )
                    mock_ts.return_value = ThinkSlowResult(
                        partial_profile=mock_profile,
                        confidence_map={},
                        low_confidence_traits=[],
                        observations=[],
                        incisive_questions=[],
                    )

                    # FactExtractor mock return
                    mock_fe.return_value = FactExtractionResult(
                        new_facts=[
                            Fact(category="career", content="engineer", confidence=0.9, source_turn=3),
                        ],
                        reality=Reality(
                            summary="An engineer",
                            domains={"career": "engineer"},
                            constraints=[],
                            resources=[],
                        ),
                        secrets=["avoids personal topics"],
                        contradictions=[],
                    )

                    profile = generate_profile("test", seed=0)
                    chatter = Chatter.__new__(Chatter)
                    speaker = PersonalitySpeaker.__new__(PersonalitySpeaker)
                    think_slow = ThinkSlow.__new__(ThinkSlow)
                    fact_extractor = FactExtractor.__new__(FactExtractor)

                    result = simulate_conversation(
                        chatter, speaker, profile, n_turns=6, seed=0,
                        think_slow=think_slow,
                        fact_extractor=fact_extractor,
                    )

                    # Should return 3-tuple now
                    assert len(result) == 3
                    conversation, ts_results, soul = result
                    assert isinstance(soul, Soul)
                    assert len(soul.facts) >= 1
                    assert soul.facts[0].content == "engineer"


def test_simulate_without_fact_extractor_returns_old_format():
    """Without fact_extractor, simulate_conversation returns (conversation, ts_results)."""
    from eval_conversation import simulate_conversation, Chatter, PersonalitySpeaker
    from super_brain.profile_gen import generate_profile
    from super_brain.think_slow import ThinkSlow

    with patch.object(Chatter, "next_message", return_value="Tell me more."):
        with patch.object(PersonalitySpeaker, "respond", return_value="Sure thing."):
            with patch.object(ThinkSlow, "extract") as mock_ts:
                mock_profile = PersonalityDNA(
                    id="partial",
                    sample_summary=SampleSummary(
                        total_tokens=0, conversation_count=0,
                        date_range=["u", "u"], contexts=["t"],
                        confidence_overall=0.5,
                    ),
                )
                mock_ts.return_value = ThinkSlowResult(
                    partial_profile=mock_profile,
                    confidence_map={},
                    low_confidence_traits=[],
                    observations=[],
                    incisive_questions=[],
                )

                profile = generate_profile("test", seed=0)
                chatter = Chatter.__new__(Chatter)
                speaker = PersonalitySpeaker.__new__(PersonalitySpeaker)
                think_slow = ThinkSlow.__new__(ThinkSlow)

                result = simulate_conversation(
                    chatter, speaker, profile, n_turns=4, seed=0,
                    think_slow=think_slow,
                )

                # Old format: 2-tuple (conversation, ts_results)
                assert len(result) == 2
                conversation, ts_results = result
                assert isinstance(conversation, list)
