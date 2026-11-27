# Risk assessment safety fixes

## Changes

1. **Legal evidence validation**
   - Prompt-side filtering now rejects URLs outside `chinhphu.vn` and `thuvienphapluat.vn`.
   - Agent 3 only accepts legal references with an allowed URL and at least 100 characters of content.
   - `VerifiedRisk` requires at least one legal reference and `evidence_type="direct_contradictory"`.
   - A `keep` rejected by validation gets another bounded LLM turn instead of immediately ending the candidate.

2. **Chunk ID validation**
   - Agent 1/2 output must reference a chunk ID from the current batch, not merely any batch in the contract.

3. **Duplicate search and retries**
   - Query normalization catches repeated searches despite case, whitespace, and punctuation changes.
   - Repeated queries are not sent to Tavily again.
   - Search errors can be retried with a different query, while actual tool calls remain capped by `MAX_AGENT3_TOOL_CALLS_PER_ISSUE`.
   - Distinct legal references are retained across search attempts (up to three per configured search attempt).
   - Trace actions distinguish actual `search_legal` calls from skipped duplicate/invalid/over-limit attempts.

4. **Regression tests**
   - `tests/test_agent_safety.py` covers cross-batch chunk IDs, URL allowlisting, duplicate-query prevention, evidence accumulation, invalid `keep`, short content, retries after tool errors, and `VerifiedRisk` schema constraints.

## Run tests

From the parent application environment, with the project's dependencies and `config.settings` available:

```bash
python -m pytest -q modes/risk_assessment/tests/test_agent_safety.py
```

If this folder is used as a standalone `risk_assessment` package, run:

```bash
python -m pytest -q risk_assessment/tests/test_agent_safety.py
```

The tests mock LLM and search calls; they do not call the live FPT LLM or Tavily API.
