# Test Coverage Analysis

## Current State

The repository currently has **no test coverage**. The only test-related artifact is an empty `contractor-crm/tests/__init__.py` file. No test frameworks are installed, no test configuration exists, and CI/CD pipelines only validate markdown (broken links, spelling, locale checks) -- they do not run any code tests.

---

## Recommended Test Improvements

### Priority 1 -- Pure Business Logic (High Value, Low Effort)

These modules contain deterministic math and logic with no external dependencies, making them ideal first targets.

#### 1. `trading-agent/risk/position_sizing.py`
- **What to test:** `fixed_fractional_size()` and `kelly_size()` functions
- **Why:** Financial calculations where bugs can cause real monetary loss. Both functions have clear inputs/outputs, edge cases (zero capital, zero risk, negative Kelly), and capping logic.
- **Example tests:**
  - Verify fixed fractional sizing with known risk/stop values
  - Verify Kelly criterion produces expected fraction
  - Verify position capping at `max_position_pct`
  - Edge cases: zero `risk_per_unit`, zero capital, zero entry price

#### 2. `trading-agent/backtest/metrics.py`
- **What to test:** `_max_drawdown()`, `_sharpe_ratio()`, `_sortino_ratio()`, `calculate_metrics()`, `BacktestMetrics.composite_score()`
- **Why:** These are standard financial metrics with well-known expected values. Incorrect metrics lead to bad strategy selection.
- **Example tests:**
  - Sharpe/Sortino with known return series
  - Max drawdown on a hand-crafted equity curve
  - Win rate and profit factor with a fixed trade list
  - Composite score calculation

#### 3. `trading-agent/patterns/rsi.py`
- **What to test:** `compute_rsi()`, zone detection, divergence detection, local extrema finding
- **Why:** RSI is a well-defined formula. Correctness can be verified against reference implementations (e.g., `ta` library).
- **Example tests:**
  - RSI output matches expected values for a known price series
  - Oversold/overbought zone detection at threshold boundaries
  - Bullish divergence: lower price low + higher RSI low
  - Bearish divergence: higher price high + lower RSI high

#### 4. `trading-agent/risk/stop_manager.py`
- **What to test:** `create_stop()`, `update()`, `is_stopped()`
- **Why:** Stop-loss progression (initial -> breakeven -> trailing) is critical for risk management. State machine logic is highly testable.
- **Example tests:**
  - Initial stop creation
  - Breakeven trigger when target is hit
  - Trailing stop updates as price moves favorably
  - Stop-out detection for long and short positions

#### 5. `contractor-crm/services/scoring.py`
- **What to test:** Recency scoring thresholds, frequency scoring, revenue trend calculation, satisfaction scoring, tier assignment
- **Why:** Customer scoring directly affects business decisions. The function has clear threshold-based logic.
- **Example tests:** (requires mocking DB session)
  - Recency score for interactions at 7, 14, 30, 60, 90+ day thresholds
  - Frequency score at 1, 3, 6, 10+ interaction counts
  - Score normalization: verify capped at 0-100
  - Tier assignment: platinum (80+), gold (60+), silver (40+), bronze (below)

#### 6. `contractor-crm/services/concentration.py`
- **What to test:** HHI calculation, concentration level classification, flag generation
- **Why:** Revenue concentration analysis uses the Herfindahl-Hirschman Index -- a well-defined metric.
- **Example tests:**
  - HHI = 10000 for a single customer (monopoly)
  - HHI for equal revenue split across N customers
  - Concentration level thresholds (highly concentrated / moderately / diversified)
  - Flag generation when a single customer exceeds threshold

---

### Priority 2 -- Pattern Recognition and Signal Logic (High Value, Medium Effort)

These modules contain complex algorithms that benefit from regression tests to prevent subtle breakage.

#### 7. `trading-agent/patterns/elliott_wave.py`
- **What to test:** Swing point detection, wave validation rules, confidence scoring
- **Why:** Elliott Wave detection is complex with many edge cases. Regression tests prevent subtle changes from breaking pattern recognition.
- **Example tests:**
  - Swing point detection on synthetic zigzag data
  - Bullish wave validation: wave2 retraces 38.2-78.6% of wave1
  - Bearish wave validation with same retracement rules
  - Confidence scoring: ideal range (50-61.8%) returns highest scores
  - Wave3 target calculation using Fibonacci extensions

#### 8. `trading-agent/signals/wave3_rsi.py`
- **What to test:** RSI confirmation logic, signal building (entry/stop/target prices)
- **Why:** This combines two pattern detectors -- bugs in signal generation lead to bad trades.
- **Example tests:**
  - Signal generation from known wave structure + RSI data
  - Entry, stop-loss, and target price calculations
  - Confidence boosting from RSI conditions

#### 9. `trading-agent/risk/portfolio_risk.py`
- **What to test:** `can_open_position()` checks, drawdown calculation, circuit breaker
- **Why:** Portfolio risk manager is the final safety gate before trade execution.
- **Example tests:**
  - Max positions check
  - Single position size limit
  - Total exposure limit
  - Circuit breaker triggers at drawdown threshold
  - Circuit breaker blocks new positions when active

---

### Priority 3 -- Integration / API Tests (High Value, Higher Effort)

These require mocking external services (database, LLM APIs, market data APIs) but cover critical integration points.

#### 10. `trading-agent/execution/paper_broker.py`
- **What to test:** Order submission, position management, account equity calculation
- **Why:** Paper broker is self-contained (no external API calls), making it a good integration test target.
- **Example tests:**
  - Buy order fills and creates position
  - Sell order reduces/closes position
  - Average entry price calculation on position adds
  - Account equity = cash + sum of position market values

#### 11. `trading-agent/backtest/engine.py`
- **What to test:** Full backtest run with synthetic signals, exit logic, PnL calculations
- **Why:** The backtest engine is the primary validation tool for trading strategies.
- **Example tests:**
  - Single long trade: entry to target exit
  - Single short trade: entry to stop-loss exit
  - Partial exit at first target
  - Time stop (end of data forces close)
  - Equity curve tracking

#### 12. `contractor-crm/api/` endpoints
- **What to test:** CRUD operations for customers, contacts, projects, interactions
- **Why:** API endpoints are the primary interface for the CRM application.
- **Example tests:** (using FastAPI TestClient + SQLite in-memory DB)
  - Create, read, update, delete for each entity
  - Filtering and search query parameters
  - Soft delete behavior (customers)
  - Pipeline summary aggregation
  - Win/loss analytics calculation

#### 13. `contractor-crm/agents/orchestrator.py`
- **What to test:** JSON parsing from LLM responses, prompt construction
- **Why:** LLM response parsing is fragile and benefits from tests with varied response formats.
- **Example tests:** (mock `chat()` function)
  - Parse valid JSON from markdown code blocks
  - Handle malformed JSON gracefully
  - Verify prompt includes correct data

---

### Priority 4 -- Data Provider Tests (Medium Value, Requires Mocking)

#### 14. `trading-agent/data/yfinance_provider.py`
- **What to test:** Timeframe mapping, column normalization, 4-hour resampling
- **Why:** Data quality issues propagate through the entire pipeline.
- **Example tests:** (mock yfinance download)
  - Column rename logic
  - 4-hour resampling from 1-hour data
  - Empty data handling

---

## Recommended Test Infrastructure

### Setup Steps

1. **Add test dependencies** to each project's `requirements.txt`:
   ```
   pytest>=8.0
   pytest-cov>=4.0
   pytest-asyncio>=0.23  # for async tests
   httpx>=0.27           # for FastAPI TestClient
   ```

2. **Create `pyproject.toml`** or `pytest.ini` for each project with configuration:
   ```toml
   [tool.pytest.ini_options]
   testpaths = ["tests"]
   addopts = "--cov --cov-report=term-missing"
   ```

3. **Add a CI workflow** (`.github/workflows/tests.yml`) that runs tests on PRs.

4. **Directory structure:**
   ```
   contractor-crm/
     tests/
       test_scoring.py
       test_concentration.py
       test_api_customers.py
       test_api_contacts.py
       test_api_projects.py
       conftest.py          # shared fixtures (DB session, test client)

   trading-agent/
     tests/
       test_position_sizing.py
       test_metrics.py
       test_rsi.py
       test_elliott_wave.py
       test_stop_manager.py
       test_portfolio_risk.py
       test_paper_broker.py
       test_backtest_engine.py
       conftest.py          # shared fixtures (sample DataFrames)
   ```

---

## Impact Summary

| Priority | Modules | Est. Test Count | Risk Mitigated |
|----------|---------|----------------|----------------|
| P1 | 6 modules | ~40-60 tests | Financial calculations, scoring logic |
| P2 | 3 modules | ~20-30 tests | Pattern recognition, risk management |
| P3 | 4 modules | ~30-40 tests | API correctness, integration |
| P4 | 1 module | ~5-10 tests | Data pipeline integrity |
| **Total** | **14 modules** | **~95-140 tests** | |

Starting with Priority 1 would cover the highest-risk pure logic with the least setup effort. The trading agent's financial calculations and the CRM's scoring/concentration services should be tested first.
