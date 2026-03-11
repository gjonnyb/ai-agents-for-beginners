from __future__ import annotations

import json
from dataclasses import dataclass

from backtest.metrics import BacktestMetrics
from backtest.report import AssetReport


@dataclass
class ResearchResult:
    """Output from a pattern research analysis."""

    pattern_name: str
    summary: str
    best_assets: list[dict]
    recommendation: str
    raw_response: str = ""


class ResearchAgent:
    """AI-powered pattern research agent.

    Analyzes backtest results across assets and timeframes to provide
    insights on where a pattern works best and whether it's worth automating.
    """

    def __init__(self, llm_client=None, model: str = "claude-sonnet-4-20250514"):
        self._client = llm_client
        self._model = model

    def _get_client(self):
        if self._client is not None:
            return self._client

        try:
            import anthropic
            self._client = anthropic.Anthropic()
            return self._client
        except Exception:
            pass

        try:
            import openai
            self._client = openai.OpenAI()
            self._model = "gpt-4o"
            return self._client
        except Exception:
            raise RuntimeError(
                "No LLM client available. Set ANTHROPIC_API_KEY or OPENAI_API_KEY."
            )

    def analyze_backtest_results(
        self,
        reports: list[AssetReport],
        pattern_name: str = "Wave 3 + RSI",
    ) -> ResearchResult:
        """Analyze backtest results and provide trading insights."""
        # Build a structured summary of results for the LLM
        results_data = []
        for r in reports:
            m = r.metrics
            results_data.append({
                "symbol": r.symbol,
                "timeframe": r.timeframe,
                "total_trades": m.total_trades,
                "win_rate": f"{m.win_rate:.1%}",
                "profit_factor": round(m.profit_factor, 2),
                "sharpe_ratio": round(m.sharpe_ratio, 2),
                "sortino_ratio": round(m.sortino_ratio, 2),
                "max_drawdown": f"{m.max_drawdown_pct:.1%}",
                "total_return": f"{m.total_return_pct:+.1f}%",
                "expectancy": f"${m.expectancy:,.2f}",
                "composite_score": round(m.composite_score(), 3),
                "exit_breakdown": m.exit_breakdown,
            })

        prompt = self._build_analysis_prompt(pattern_name, results_data)
        response = self._call_llm(prompt)

        # Extract best assets
        sorted_reports = sorted(
            reports, key=lambda r: r.metrics.composite_score(), reverse=True
        )
        best_assets = [
            {
                "symbol": r.symbol,
                "timeframe": r.timeframe,
                "score": r.metrics.composite_score(),
                "win_rate": r.metrics.win_rate,
                "sharpe": r.metrics.sharpe_ratio,
            }
            for r in sorted_reports[:5]
        ]

        return ResearchResult(
            pattern_name=pattern_name,
            summary=response,
            best_assets=best_assets,
            recommendation=self._extract_recommendation(response),
            raw_response=response,
        )

    def research_pattern(self, pattern_description: str) -> str:
        """Research a new pattern and suggest detection rules.

        Use this before building a new pattern detector to assess
        whether a pattern is worth automating.
        """
        prompt = f"""You are a quantitative trading research analyst. A trader wants to
evaluate whether the following technical analysis pattern is worth automating
as an algorithmic trading strategy.

Pattern description:
{pattern_description}

Provide a thorough analysis covering:

1. **Pattern Definition**: Precise, unambiguous rules for identifying this pattern
   (entry conditions, confirmation criteria, invalidation rules).

2. **Historical Context**: How has this pattern performed historically across
   different market conditions (trending, ranging, volatile)?

3. **Best Asset Classes**: Which asset classes (stocks, crypto, forex, commodities)
   and timeframes tend to work best with this pattern?

4. **Risk Considerations**: What are the main risks? False signals? Whipsaw?
   How sensitive is it to parameter tuning?

5. **Detection Rules**: Pseudocode or step-by-step algorithm for detecting this
   pattern programmatically. Be specific about thresholds and conditions.

6. **Recommendation**: Should the trader build an automated system for this pattern?
   What success rate and risk/reward should they target?

Be quantitative and specific. Avoid vague generalities."""

        return self._call_llm(prompt)

    def _build_analysis_prompt(
        self, pattern_name: str, results_data: list[dict]
    ) -> str:
        return f"""You are a quantitative trading analyst reviewing backtest results
for the "{pattern_name}" pattern across multiple assets and timeframes.

Here are the results:

{json.dumps(results_data, indent=2)}

Provide a concise analysis covering:

1. **Overall Assessment**: Is this pattern profitable? Is it consistent across assets?

2. **Best Performers**: Which assets/timeframes show the strongest results? Why?

3. **Worst Performers**: Which should be avoided? What characteristics do they share?

4. **Risk Analysis**: Comment on drawdowns, win rates, and profit factors.
   Are any results suspiciously good (possible overfitting)?

5. **Recommendation**: Should the trader deploy this pattern live? On which
   assets? With what position sizing? Any adjustments needed?

6. **Next Steps**: What additional testing or modifications would improve results?

Be specific and data-driven. Reference actual numbers from the results."""

    def _extract_recommendation(self, response: str) -> str:
        """Extract a one-line recommendation from the analysis."""
        lines = response.split("\n")
        for i, line in enumerate(lines):
            if "recommendation" in line.lower():
                # Return the next non-empty line(s)
                for j in range(i + 1, min(i + 4, len(lines))):
                    if lines[j].strip():
                        return lines[j].strip()
        return "See full analysis for recommendation."

    def _call_llm(self, prompt: str) -> str:
        """Call the LLM and return the text response."""
        client = self._get_client()

        # Detect client type and call accordingly
        if hasattr(client, "messages"):
            # Anthropic client
            response = client.messages.create(
                model=self._model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        else:
            # OpenAI-compatible client
            response = client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
            )
            return response.choices[0].message.content
