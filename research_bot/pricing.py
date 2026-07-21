"""All list prices in one place. Every cost estimate in the repo reads from here.

Prices are published per-token API list rates as of 2026-07. List-vs-list is
the deliberate comparison basis throughout: subscription/flat-rate plans don't
price a production workload, so published per-token rates are the only stable
unit for comparing stacks. Update this file when a provider reprices.
"""

# $/M tokens: (input, output, cached-input)
RATES = {
    "deepseek-v4-flash": (0.14, 0.28, 0.0028),
    "deepseek-v4-pro": (0.435, 0.87, 0.003625),
    "glm-5.2": (1.40, 4.40, 0.26),
    "z-ai/glm-5.2": (1.40, 4.40, 0.26),
    "kimi-k3": (3.0, 15.0, 0.30),
    "claude-fable-5": (10.0, 50.0, 1.00),
    "gpt-5.6-sol": (5.0, 30.0, 0.50),
}

# Anthropic list rates for `research report --anthropic` (input, output, cached-input)
ANTHROPIC_OPUS = (15.0, 75.0, 1.50)
ANTHROPIC_SONNET = (3.0, 15.0, 0.30)

KAGI_SEARCH_USD = 0.025        # per search (Search API, $25/1k)
KAGI_EXTRACT_PAGE_USD = 0.004  # per successfully extracted page ($4/1k)


def llm_cost(model, tokens_in, tokens_out, cached_in=0):
    """Metered $ for one call at list rates; 0 for models not in RATES."""
    r_in, r_out, r_cached = RATES.get(model, (0, 0, 0))
    return ((tokens_in - cached_in) * r_in + cached_in * r_cached + tokens_out * r_out) / 1e6
