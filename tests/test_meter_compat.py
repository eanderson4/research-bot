"""Drift guards against llm-meter (github.com/eanderson4/llm-meter).

llm-meter measures provider mechanics (TTFT, tok/s) and shares research-bot's
result-field conventions; its schema is the cross-repo contract. These tests
fail CI when the two repos disagree on list rates or field conventions.
llm-meter is a dev-group dependency only — skip cleanly if it's absent.
"""
import pytest

pytest.importorskip("llm_meter")

from llm_meter import pricing as meter_pricing  # noqa: E402
from llm_meter import schema as meter_schema  # noqa: E402

from research_bot import pricing  # noqa: E402


def test_shared_model_list_rates_match():
    shared = set(pricing.RATES) & set(meter_pricing.RATES)
    assert shared, "repos no longer share any model — did a rename land in only one?"
    mismatched = {m: (pricing.RATES[m], meter_pricing.RATES[m])
                  for m in shared if pricing.RATES[m] != meter_pricing.RATES[m]}
    assert not mismatched, f"list rates drifted between repos: {mismatched}"


def test_anthropic_list_rates_match():
    assert meter_pricing.RATES["claude-opus-4-8"] == pricing.ANTHROPIC_OPUS
    assert meter_pricing.RATES["claude-sonnet-5"] == pricing.ANTHROPIC_SONNET


def test_bench_result_fields_map_onto_meter_schema():
    # The fields research-bot's bench records (bench.py runners) share with the
    # contract. If llm-meter renames one, this stops validating.
    bench_style = {"tokens_in": 1200, "tokens_out": 340, "seconds": 4.1, "cost_usd": 0.00027}
    rec = {"ts": "2026-07-20T00:00:00", "kind": "completion",
           "provider": "deepseek", "model": "deepseek-v4-flash", "ok": True, **bench_style}
    assert meter_schema.problems(rec) == []


def test_meter_schema_still_rejects_garbage():
    # Guards against the contract going vacuous upstream.
    assert meter_schema.problems({"kind": "banana", "tokens_out": "many"})
