# Constitutional Reasoning Engine - Project Journal

**Project Start Date:** October 22, 2025
**Purpose:** Document all significant decisions, issues, and progress during the experiment setup and execution. This journal serves as both a development log and methodology documentation for the final report.

---

## Journal Entry Format
Each entry includes:
- **Date/Time:** When the event occurred
- **Category:** Setup | Bug Fix | Decision | Finding | Configuration
- **Summary:** Brief description
- **Details:** Full context and rationale
- **Impact:** How this affects the experiment or results

---

## October 22, 2025

### Entry 1: Project Initialization
**Time:** 11:45 AM
**Category:** Setup
**Summary:** Created Python project structure with Poetry and initialized git repository

**Details:**
- Set up experiments/ directory structure with src/ for modules
- Configured pyproject.toml with dependencies: litellm, pandas, matplotlib, plotly, pydantic
- Created .env for API keys (Anthropic, OpenAI, Google, xAI, Replicate, DeepSeek)
- Initialized as git repository with logical commit groups

**Impact:** Established foundation for reproducible experiment environment

---

### Entry 2: Initial Model Configuration
**Time:** 12:00 PM
**Category:** Configuration
**Summary:** Configured 3 initial models via LiteLLM unified interface

**Details:**
- Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)
- GPT-4o (gpt-4o)
- Llama 3 8B (replicate/meta/meta-llama-3-8b-instruct)

**Rationale:** Started with subset to validate pipeline before scaling to full 6 models

**Impact:** Enabled initial testing with diverse model providers (Anthropic, OpenAI, Replicate)

---

### Entry 3: State Management System Implementation
**Time:** 12:30 PM
**Category:** Setup
**Summary:** Implemented robust experiment state management with individual test tracking

**Details:**
Created ExperimentManager class with:
- Individual test completion tracking (prevents rerunning completed tests)
- Resume capability after interruption or failure
- Incremental model addition (can add new models without rerunning entire experiment)
- Test status tracking (pending/in_progress/completed/failed) with retry logic

**Rationale:** User requirement: "when we bring other models online I'm not going to want to rerun the entire job from scratch we should only pick up with the new models"

**Impact:** Enables efficient iterative experimentation and prevents data loss from failures

---

### Entry 4: Llama JSON Parsing Issues
**Time:** 1:15 PM
**Category:** Bug Fix
**Summary:** Llama 3 8B returns JSON wrapped in markdown code blocks, requiring special parsing

**Details:**
- Llama responses formatted as: \`\`\`json\\n{...}\\n\`\`\`
- Standard JSON parsing failed
- Implemented robust_json_parse() with markdown block removal
- Added multiple fallback parsing methods (control character removal, partial extraction)

**Impact:** Successfully processed Llama responses, identified pattern that affects other models

---

### Entry 5: Graceful JSON Parsing System
**Time:** 1:30 PM
**Category:** Setup
**Summary:** Implemented zero-data-loss parsing system with manual review fallback

**Details:**
Created GracefulJsonParser with:
- Multiple parsing strategies (direct JSON, markdown removal, partial extraction)
- Automatic saving of raw responses when parsing fails
- ParseStatus enum (SUCCESS, PARTIAL_SUCCESS, MANUAL_REVIEW, FAILED)
- Structured fallback data to allow experiment continuation

**Rationale:** User requirement: "We need to gracefully handle cases where the JSON parsing doesn't work, meaning I don't want to rerun the tests. If the response is coming back, we should figure out a way to capture it"

**Impact:** Zero data loss - all model responses preserved even when automated parsing fails

---

## October 23, 2025

### Entry 6: Gemini Model Selection - API Availability Issue
**Time:** 6:30 AM
**Category:** Decision
**Summary:** Switched from Gemini 2.5 Pro to Gemini 2.5 Flash due to persistent 503 errors

**Details:**
- Initial configuration used gemini-2.5-pro as specified in PROJECT_BRIEF
- Encountered 503 "Service Unavailable" errors: "The model is overloaded. Please try again later."
- Research revealed this is a common issue with Gemini 2.5 Pro via Google AI Studio API
- Switched to gemini-2.5-flash (stable production endpoint)
- Model accessible and responsive (866ms avg response time)

**External Context:**
- Gemini 2.5 Pro is in preview/beta with capacity limitations
- Gemini 2.5 Flash is production-ready with better availability
- Flash model offers "best price-to-performance ratio" per Google documentation

**Impact on Experiment:**
- Using Flash instead of Pro may affect response quality/depth
- Flash is actually faster and more cost-effective
- Should be noted in methodology: model selection constrained by API availability
- Consider this a real-world constraint that production systems would face

**Recommendation for Report:**
Document as: "Model selection was constrained by API availability. Gemini 2.5 Pro showed persistent capacity issues (503 errors), leading to selection of Gemini 2.5 Flash as the production-stable alternative."

---

### Entry 7: Max Tokens Investigation - Response Truncation
**Time:** 6:35 AM
**Category:** Finding
**Summary:** Discovered models require different max_tokens limits to generate complete responses

**Details:**

**Initial Configuration:**
- Layer 1 (Facts): 1,000 tokens
- Layer 2 (Constitutional): 1,500 tokens
- Layer 3 (Integrity): 2,000 tokens

**Problem Identified:**
- Gemini 2.5 Flash responses truncated mid-JSON at 1,500 tokens
- Llama 3 8B responses truncated even with higher limits
- Claude Sonnet 4.5 and GPT-4o worked fine with initial limits

**Testing Methodology:**
Systematically increased max_tokens for Layer 2 (constitutional reasoning) and tested:

| Model | 1,500 | 3,000 | 4,000 | 5,000 | 6,000 | Result |
|-------|-------|-------|-------|-------|-------|--------|
| Claude Sonnet 4.5 | ✅ | - | - | - | - | Complete |
| GPT-4o | ✅ | - | - | - | - | Complete |
| Gemini 2.5 Flash | ❌ Truncated | ❌ Truncated | ✅ Complete | - | - | Needs 4,000 |
| Llama 3 8B | ❌ Truncated | ❌ Truncated | ❌ Truncated | ❌ Truncated | ✅ Complete | Needs 6,000 |

**Key Findings:**
1. Different models have varying verbosity levels for same prompt
2. Smaller/open-source models (Llama) tend to be more verbose
3. max_tokens is a hard cutoff, not a target - models don't adjust output length
4. API cost is based on actual tokens used, not max_tokens limit
5. Truncation invalidates scientific validity - need complete responses

**Impact on Experiment Design:**
- Cannot use uniform max_tokens across all models
- Need automatic truncation detection and retry mechanism
- Should start with generous baseline (8,000 tokens) for Layer 2
- Must track which models need higher limits for methodology documentation

---

### Entry 8: Truncation Detection & Auto-Retry System
**Time:** 6:40 AM
**Category:** Setup
**Summary:** Implemented automatic truncation detection with progressive retry logic

**Details:**

**Created TruncationDetector class with detection methods:**
1. Incomplete JSON structure (unmatched braces)
2. Abrupt endings (no proper punctuation)
3. Missing closing braces/brackets
4. Unterminated strings

**Auto-Retry Strategy:**
- Start with 8,000 tokens baseline (safe for most models)
- If truncation detected, retry with: 12,000 → 16,000 → 20,000 → 30,000
- Maximum 3 retries per test
- Log final token requirement per model

**Rationale:**
User requirement: "we will also need to track situations where the model seems to have been cut off, and to retry those cases at higher max token thresholds. In order for our experiment to be valid, we will need complete responses for every scenario."

**Scientific Validity Concern:**
Incomplete responses cannot be fairly scored for integrity. Truncation could:
- Cut off value explanations (affects valueTransparency score)
- Eliminate tradeoff acknowledgments (affects logicalCoherence score)
- Make reasoning appear incomplete when it wasn't

**Impact:**
- Ensures 100% complete responses for all models
- Documents token requirements as model characteristic
- Maintains scientific validity by preventing truncation-induced scoring bias
- Automatically handles model verbosity differences

**For Report:**
"To ensure scientific validity, we implemented automatic truncation detection with progressive retry logic. Models requiring higher token limits were automatically retried with increasing limits (8K→12K→16K→20K→30K) until complete responses were obtained. This ensures fair comparison across models with different verbosity characteristics."

---

### Entry 9: Grok Model Selection and Testing
**Time:** 6:45 AM (October 23, 2025)
**Category:** Configuration
**Summary:** Added Grok 3 (upgraded from Grok 2) - works perfectly with baseline 8K tokens

**Details:**

**Model Selection Process:**
- Originally planned to use Grok 2 per PROJECT_BRIEF
- Attempted `xai/grok-beta` - received deprecation error
- Error message: "The model grok-beta was deprecated on 2025-09-15 and is no longer accessible via the API. Please use grok-3 instead."
- Switched to `xai/grok-3`

**Testing Results:**
- ✅ Connectivity successful (467ms response time - fastest model so far!)
- ✅ Full 3-layer pipeline test with 8,000 max_tokens: SUCCESS
- ✅ JSON parsing: Clean JSON output, no markdown blocks
- ✅ Response completeness: No truncation
- ✅ Integrity score: 95.0/100 (highest so far)

**Model Characteristics:**
- Very fast response times (467ms connectivity, ~20s for constitutional reasoning)
- Returns clean, well-formatted JSON
- No special parsing requirements (unlike Llama/Gemini)
- Works perfectly with baseline 8,000 token limit

**Impact:**
- Using Grok 3 instead of Grok 2 - newer model may have different characteristics
- Should note in report: "Used Grok 3 instead of originally planned Grok 2 due to API deprecation"
- Grok 3 appears to be one of the best-performing models for this task

**For Report:**
"xAI's Grok 2 was deprecated during experiment setup. We used Grok 3 as recommended by the API. Grok 3 demonstrated excellent performance with fast response times (467ms avg) and clean JSON output requiring no special parsing."

---

### Entry 10: DeepSeek Chat Successfully Added
**Time:** 7:00 AM (October 23, 2025)
**Category:** Configuration
**Summary:** DeepSeek Chat working after adding $5 credits - completes all 6 planned models

**Details:**

**Initial Issue:**
- Error: "Insufficient Balance" when attempting API calls
- User added $5 in credits to DeepSeek platform account

**Testing Results:**
- ✅ Connectivity successful (1,344ms response time)
- ✅ Full 3-layer pipeline test with 8,000 max_tokens: SUCCESS
- ✅ JSON parsing: JSON in markdown blocks (like Llama/Gemini)
- ✅ Response completeness: No truncation with 8K baseline
- ✅ Integrity score: 95.7/100 (highest score so far, tied with Grok!)

**Model Characteristics:**
- Fast response times (~11s for constitutional reasoning)
- Returns JSON wrapped in markdown code blocks
- Works perfectly with 8,000 token baseline
- Very high quality responses with strong reasoning

**Impact:**
- ✅ **All 6 models now operational!**
- Complete model diversity: major commercial (Claude/GPT), open-source (Llama), newer entrants (Gemini/Grok), Chinese frontier (DeepSeek)
- Ready for full 10 scenarios × 5 constitutions × 6 models = 300 tests

---

## Final Model Configuration Summary

| # | Model | Provider | Status | Speed | Token Req | JSON Format | Test Score |
|---|-------|----------|--------|-------|-----------|-------------|------------|
| 1 | Claude Sonnet 4.5 | Anthropic | ✅ | 2-3s | 2K | Clean JSON | Not tested individually |
| 2 | GPT-4o | OpenAI | ✅ | 1-2s | 2K | Clean JSON | Not tested individually |
| 3 | Llama 3 8B | Replicate | ✅ | 1-2s | 6K ⚠️ | Markdown blocks | 85.0 |
| 4 | Gemini 2.5 Flash | Google | ✅ | 0.8s | 4K ⚠️ | Markdown blocks | 91.7 |
| 5 | Grok 3 | xAI | ✅ | 0.5-1s | 8K | Clean JSON | 95.0 |
| 6 | DeepSeek Chat | DeepSeek | ✅ | 1-2s | 8K | Markdown blocks | 95.7 |

**Key Patterns Identified:**

1. **JSON Formatting:**
   - Commercial models (Claude, GPT, Grok): Clean JSON
   - Alternative models (Llama, Gemini, DeepSeek): Markdown code blocks
   - Graceful parser handles both formats automatically

2. **Token Requirements:**
   - Claude/GPT: Work with minimal tokens (2K)
   - Gemini: Needs 4K for complete responses
   - Llama: Needs 6K for complete responses (most verbose)
   - Grok/DeepSeek: Work well with 8K baseline
   - **Recommendation:** Use 8K baseline with truncation detection/retry

3. **Speed:**
   - Fastest: Grok 3 (467ms connectivity, fast reasoning)
   - Also fast: Gemini 2.5 Flash (817ms), GPT-4o (~1s)
   - Moderate: Llama, DeepSeek (~1-2s)
   - Slower: Claude Sonnet 4.5 (~2-3s)

4. **Quality (Integrity Scores from Individual Tests):**
   - Highest: DeepSeek (95.7), Grok (95.0)
   - Strong: Gemini (91.7)
   - Good: Llama (85.0)
   - Note: Claude/GPT not individually tested yet

---

## Next Steps

- [x] All 6 models added and tested individually
- [ ] Run full 1-scenario × 5 constitutions × 6 models test (30 tests)
- [ ] Analyze results across all 6 models
- [ ] Document model-specific patterns and characteristics
- [ ] Scale to full 10 scenarios (300 tests)
- [ ] Consider OpenRouter migration for unified billing/monitoring

---

## Notes for Final Report

### Methodology Considerations
1. **Model Selection Constraints:** Document API availability issues with Gemini 2.5 Pro
2. **Token Limit Variations:** Report token requirements as model characteristic
3. **Parsing Strategies:** Document that models vary in output formatting (markdown vs raw JSON)
4. **Truncation Handling:** Explain auto-retry mechanism ensuring complete responses
5. **State Management:** Note that experiment is resumable and incrementally expandable

### Potential Findings to Track
- Do more verbose models (higher token requirements) produce higher integrity scores?
- Does output formatting (markdown blocks) correlate with other model behaviors?
- Are open-source models (Llama) systematically more/less verbose than commercial models?

---

*This journal should be updated regularly throughout the experiment. Each significant decision, bug fix, or finding should be documented with context for the final report.*
