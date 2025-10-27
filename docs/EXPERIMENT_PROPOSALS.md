# Novel LLM-as-Judge Validation Experiments

**Date:** October 26, 2025
**Purpose:** Propose 5 research experiments addressing gaps in LLM evaluator validation literature
**Goal:** Demonstrate research rigor, extend existing work, produce publishable findings

---

## Experiment Selection Criteria

Each proposed experiment:
1. **Fills an identified research gap** from literature review
2. **Uses publicly available human-labeled datasets** (no expensive annotation required)
3. **Is feasible within 2-4 weeks** with existing infrastructure
4. **Produces publishable results** valued by AI safety community
5. **Extends existing research** in meaningful ways (not mere replication)

---

## Experiment 1: Systematic Rubric Design Validation

### Research Gap Addressed

**Gap:** No systematic comparison of rubric structures (binary vs 3-point vs 5-point vs 0-100) across multiple evaluation dimensions and evaluator models with human ground truth validation.

**Existing work:**
- Google Research: Boolean rubrics reduce variance vs Likert (health domain only)
- Databricks: Tested 0-1 to 0-10 scales for RAG tasks (no formal validation)

**What's missing:**
- Controlled study across multiple rubric formats
- Multiple evaluation criteria (not just single domain)
- Multiple evaluator models (not just GPT-4)
- Validated against human ground truth

---

### Research Question

**Primary:** Which rubric design (binary, ternary, 5-point Likert, 0-100 continuous) maximizes inter-rater reliability between LLM judges and human evaluators across different evaluation criteria?

**Secondary:**
- Does optimal rubric design vary by evaluation criterion type (objective vs subjective)?
- Does optimal rubric design vary by evaluator model (Claude vs GPT vs Gemini)?
- What is the cost-benefit tradeoff? (granularity lost vs reliability gained)

---

### Dataset

**Primary:** OpenAI WebGPT Comparisons (20,000 pairwise comparisons with human factuality ratings)
- **Access:** https://huggingface.co/datasets/openai/webgpt_comparisons
- **Size:** 20K human-labeled examples
- **Domain:** Factual correctness of model responses to questions
- **Format:** Pairwise preferences (which response is more factually accurate)
- **Relevance:** Directly tests factuality evaluation (our core interest)

**Subset for experiment:** 200 examples (100 for calibration, 100 for testing)
- Literature suggests 30-50 sufficient for validation, 100-200 for strong benchmarking
- Stratified sampling across difficulty levels (if metadata available)

**Secondary (if time permits):** OpenAI Summarization (64K examples with coherence ratings)
- Tests whether findings generalize to subjective criteria (coherence vs factuality)

---

### Methodology

#### Phase 1: Rubric Design (Week 1)

**Four rubric formats for factuality evaluation:**

**Format 1: Binary (Pass/Fail)**
```
Question: Is the response factually accurate?
- PASS: All claims are supported by evidence, no contradictions
- FAIL: Contains unsupported claims or contradictions

Score: PASS = 100, FAIL = 0
```

**Format 2: Ternary (3-point scale)**
```
Question: Evaluate factual accuracy:
0 = Major factual errors or contradictions
1 = Mostly accurate with minor unsupported claims
2 = Fully accurate with all claims supported

Score: 0, 1, or 2 → Convert to 0, 50, 100
```

**Format 3: 5-point Likert scale**
```
Question: Rate factual accuracy (1-5):
1 = Completely inaccurate (multiple major errors)
2 = Mostly inaccurate (several errors)
3 = Mixed (some accurate, some inaccurate claims)
4 = Mostly accurate (minor issues)
5 = Completely accurate (all supported)

Score: 1-5 → Convert to 0, 25, 50, 75, 100
```

**Format 4: 0-100 continuous scale**
```
Question: Rate factual accuracy on 0-100 scale where:
- 0 = Completely fabricated
- 25 = Major errors with some truth
- 50 = Half accurate, half inaccurate
- 75 = Mostly accurate with minor issues
- 100 = Completely accurate

Score: 0-100
```

**Each format includes:**
- Clear definitions/anchors for each score
- 3-5 few-shot examples showing scoring rationale
- Chain-of-thought requirement (explain before scoring)

#### Phase 2: Evaluator Selection (Week 1)

**Test 4 evaluators:**
1. claude-sonnet-4-5 (strict, from our data)
2. gpt-4o (moderate, from our data)
3. gemini-2-5-flash (lenient, from our data)
4. claude-3-5-haiku (fast/cheap alternative)

**Why these:** Represent leniency spectrum from our Phase 1 findings.

#### Phase 3: Data Collection (Week 2)

**Experimental design:**
- 4 rubric formats × 4 evaluators × 100 test examples = **1,600 evaluations**
- Each evaluation includes temperature sweep: [0.0, 0.3, 0.7] = **4,800 total API calls**
- Estimated cost: ~$50-75 (most calls to cheaper models)

**For each (rubric, evaluator, example, temperature):**
1. Send evaluation prompt to LLM
2. Parse response to extract score and reasoning
3. Log: rubric_format, evaluator, temperature, raw_response, parsed_score, reasoning, timestamp

#### Phase 4: Analysis (Week 2-3)

**Metrics:**

1. **Agreement with human ground truth:**
   - Convert human pairwise preferences to pointwise scores (response A > B → A=100, B=0 if clear preference)
   - Calculate correlation (Pearson r, Spearman ρ) between LLM scores and human scores
   - Calculate Cohen's Kappa (accounts for chance agreement)
   - Calculate classification accuracy for binary predictions

2. **Inter-rater reliability (across evaluators):**
   - For each rubric format, calculate mean pairwise correlation across 4 evaluators
   - Higher correlation = rubric reduces evaluator disagreement

3. **Within-evaluator consistency (across temperatures):**
   - For each (rubric, evaluator), measure variance of scores across temperature settings
   - Lower variance = more stable scoring

4. **Cost-benefit analysis:**
   - Granularity: How many distinct scores actually used? (e.g., 0-100 scale but only uses 80-95)
   - Reliability gain per granularity lost

**Hypotheses:**
- H1: Binary rubrics will show highest inter-rater reliability (Google's finding)
- H2: Continuous (0-100) will show lowest reliability due to anchoring problems
- H3: 3-point scale will optimize reliability vs granularity tradeoff
- H4: Optimal rubric will NOT vary by evaluator model (rubric design is universal)
- H5: Optimal rubric will NOT vary by criterion type (factuality is objective, should favor binary)

#### Phase 5: Reporting (Week 3-4)

**Deliverables:**
1. **Research paper** (5-8 pages):
   - Introduction: Motivation, research gaps
   - Related work: Google, Databricks, rubric design literature
   - Methodology: Dataset, rubrics, evaluators, metrics
   - Results: Correlation tables, reliability analysis, statistical tests
   - Discussion: Implications for LLM judge design
   - Conclusion: Recommendations (which rubric for which use case)

2. **Code release:**
   - Rubric templates (reusable for other researchers)
   - Evaluation harness (generic framework for LLM judge validation)
   - Analysis scripts (correlation, reliability metrics)

3. **Dataset contribution:**
   - LLM judge scores for WebGPT subset (public release to HuggingFace)
   - Enables future meta-analysis

---

### Success Metrics

**Minimum viable:**
- Complete 1,600 evaluations across all conditions
- Calculate reliability metrics for each rubric format
- Identify which rubric has highest human agreement (statistically significant difference)

**Strong outcome:**
- Replicate Google's finding (binary > Likert) on different dataset/domain
- Extend finding to multiple models (not just GPT-4)
- Quantify tradeoff curve (reliability vs granularity)
- Provide actionable recommendations

**Publication-quality:**
- Novel contribution: First systematic comparison across 4 rubric types × 4 models × objective criterion
- Statistical rigor: Power analysis, significance testing, effect sizes
- Practical impact: Clear recommendations for practitioners
- Reproducibility: Public code, data, rubrics

---

### Timeline & Resources

**Week 1:** Rubric design, evaluator setup, infrastructure (20 hours)
**Week 2:** Data collection (1,600-4,800 API calls, automated), preliminary analysis (15 hours)
**Week 3:** Statistical analysis, visualization, hypothesis testing (20 hours)
**Week 4:** Paper writing, code documentation, public release (20 hours)

**Total:** 3-4 weeks, 75 hours, ~$75 API costs

---

### Extension Opportunities

If initial results are strong:
1. Test on **subjective criteria** using OpenAI Summarization (coherence ratings)
2. Test **multi-dimensional rubrics** (e.g., binary questions for 3 sub-criteria vs single 0-100 score)
3. Test **rubric with examples vs without** (measure impact of few-shot calibration)
4. Test **explanation quality** (do binary rubrics produce clearer reasoning?)

---

## Experiment 2: Temperature/Seed Optimization for LLM Evaluators

### Research Gap Addressed

**Gap:** No comprehensive study of optimal temperature/seed settings for LLM evaluation tasks.

**Existing work:**
- Anecdotal evidence that variance exists even at temperature=0
- Studies showing "LLMs rarely 100% stable across 5 re-runs"
- No systematic optimization for evaluation (vs generation) tasks

**What's missing:**
- Which temperature minimizes within-evaluator variance while maintaining discriminative power?
- Does optimal temperature vary by model family (Claude vs GPT vs Gemini)?
- Does optimal temperature vary by evaluation task (objective vs subjective)?
- Quantified tradeoff: consistency (low temp) vs sensitivity (higher temp)?
- Does seed provide true reproducibility, or just illusion?

---

### Research Question

**Primary:** What temperature setting optimizes the tradeoff between evaluation consistency (low variance across runs) and discriminative power (ability to detect quality differences) for LLM judges?

**Secondary:**
- Is temperature=0 actually optimal for evaluations, or do higher temperatures improve reliability?
- Does fixed seed provide reproducibility, or do outputs still vary?
- Does optimal temperature differ by model architecture?
- Does optimal temperature differ by objective vs subjective criteria?

---

### Dataset

**Primary:** MT-Bench (3,000 expert human votes on 80 questions, 6 models)
- **Access:** https://github.com/lm-sys/FastChat
- **Size:** 3K expert ratings
- **Domain:** Chat quality (multi-turn dialogue)
- **Format:** Expert ratings on model responses
- **Relevance:** Gold standard for LLM evaluation validation

**Subset for experiment:** 50 questions with human ratings
- Stratified across difficulty/topic if metadata available
- Each question has multiple model responses with human quality ratings

---

### Methodology

#### Phase 1: Experimental Design (Week 1)

**Temperature sweep:** [0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0]
**Seed sweep:** 5 different seeds per temperature: [42, 123, 456, 789, 1011]
**Evaluators:** 4 models (claude-sonnet-4-5, gpt-4o, gemini-2-5-flash, claude-3-5-haiku)

**Evaluation rubric:** Fixed 5-point Likert scale for chat quality (use MT-Bench standard rubric)

**Trials:**
- 50 examples × 7 temperatures × 5 seeds × 4 evaluators = **7,000 evaluations**
- Estimated cost: ~$75-100

#### Phase 2: Data Collection (Week 1-2)

**For each (example, temperature, seed, evaluator):**
1. Evaluate with specified temperature and seed
2. Extract score (1-5 converted to 0-100)
3. Log: temperature, seed, score, raw_response, timestamp, token_count

**Control for confounds:**
- Use identical prompt across all conditions
- Same max_tokens across all conditions
- Same system message across all conditions

#### Phase 3: Analysis (Week 2-3)

**Metrics:**

1. **Within-evaluator consistency (across seeds):**
   ```
   For each (evaluator, temperature, example):
   - Calculate variance of scores across 5 seeds
   - Lower variance = more consistent
   ```

2. **Agreement with human ground truth (across temperatures):**
   ```
   For each (evaluator, temperature):
   - Calculate correlation with human ratings
   - Higher correlation = better discriminative power
   ```

3. **Optimal temperature:**
   ```
   For each evaluator:
   - Plot: X-axis = temperature, Y-axis = (human_correlation - within_variance)
   - Peak = optimal temperature (best tradeoff)
   ```

4. **Seed reproducibility:**
   ```
   For temperature=0 with fixed seed:
   - Measure: Do scores vary across runs?
   - Test: Is variance significantly > 0?
   ```

**Hypotheses:**
- H1: Temperature=0 will NOT be optimal (conventional wisdom is wrong)
- H2: Optimal temperature will be 0.2-0.3 (low but not zero, allows some sampling diversity)
- H3: Fixed seed will NOT provide perfect reproducibility (variance > 0 even at temp=0)
- H4: Optimal temperature will vary by model (different architectures, different optima)
- H5: Gemini models will need higher temperature due to over-confidence (from our Phase 1 data showing ceiling effects)

#### Phase 4: Visualization & Reporting (Week 3-4)

**Key visualizations:**
1. **Pareto frontier:** Consistency vs Discriminative Power (identify optimal points)
2. **Temperature heatmap:** Model × Temperature → Human Correlation
3. **Variance plots:** Temperature → Within-Evaluator Variance (by model)
4. **Seed stability:** Violin plots showing score distribution across seeds

**Deliverables:**
1. **Recommended temperature settings per model** for evaluation tasks
2. **Quantified benefit of multi-seed averaging** (e.g., "5 seeds reduces variance by 40%")
3. **Seed reproducibility report:** Is seed useful or just placebo?

---

### Success Metrics

**Minimum viable:**
- Complete 7,000 evaluations
- Identify optimal temperature for each model (highest correlation × lowest variance)
- Test whether temperature=0 is actually optimal

**Strong outcome:**
- Discover that temperature=0 is sub-optimal (challenges conventional wisdom)
- Find model-specific optimal temperatures (practical recommendations)
- Quantify seed variance even at temperature=0 (methodological warning)

**Publication-quality:**
- Novel finding: Optimal temperature for evaluation ≠ 0
- Practical impact: Clear recommendations (e.g., "Use temperature=0.3 for Claude judges")
- Reproducibility: Public dataset of score variance across temperatures

---

### Timeline & Resources

**Week 1:** Infrastructure setup, preliminary data collection (20 hours)
**Week 2:** Full data collection (7K evaluations, automated) (10 hours)
**Week 3:** Statistical analysis, optimization, visualization (25 hours)
**Week 4:** Paper writing, recommendations, public release (20 hours)

**Total:** 3-4 weeks, 75 hours, ~$100 API costs

---

### Extension Opportunities

1. **Objective vs subjective criteria:** Test on factuality (WebGPT) vs coherence (Summarization)
2. **Multi-seed aggregation strategies:** Mean vs median vs mode
3. **Top-p/top-k interaction:** Does top-p=0.9 + temp=0.3 outperform temp=0?
4. **Fine-tuned judges:** Do optimal temperatures change for fine-tuned models?

---

## Experiment 3: Ensemble Composition Optimization

### Research Gap Addressed

**Gap:** No systematic study of optimal ensemble composition for LLM judges - how many evaluators, diverse vs homogeneous, voting strategy, cost-benefit tradeoff.

**Existing work:**
- Evidence that ensembles improve reliability (ICE: 27% gain)
- Examples using 3 models (PoLL framework)
- No systematic optimization of ensemble parameters

**What's missing:**
- How many evaluators? (3 vs 5 vs 7 vs 9?)
- Composition: Diverse models (Claude+GPT+Gemini) or homogeneous (3× GPT-4)?
- Voting strategy: Majority, mean, median, weighted by model reliability?
- When do reliability gains plateau? (diminishing returns)
- Cost-benefit analysis: Is ensemble worth 3-5× cost?

---

### Research Question

**Primary:** What ensemble composition (size, diversity, aggregation strategy) maximizes reliability improvement per dollar spent for LLM-as-judge systems?

**Secondary:**
- Does ensemble size follow law of diminishing returns? (5 better than 3, but not 2× better?)
- Is diversity (different model families) better than homogeneity (same model, different seeds)?
- Which aggregation strategy is best: mean, median, mode, or confidence-weighted voting?
- Can we predict which trials need ensemble evaluation (detect high-variance cases beforehand)?

---

### Dataset

**Primary:** Anthropic HH-RLHF (170,000 pairwise comparisons for helpfulness/harmlessness)
- **Access:** https://huggingface.co/datasets/Anthropic/hh-rlhf
- **Size:** 170K human preference pairs
- **Domain:** Helpfulness and harmlessness (Anthropic's HHH framework)
- **Format:** Pairwise comparisons (response A vs B, which is better?)
- **Relevance:** Large dataset, highly relevant to AI safety (Anthropic's core research)

**Subset for experiment:** 200 pairwise comparisons
- Stratified across helpfulness and harmlessness dimensions
- Mix of clear preferences and close calls (if metadata available)

---

### Methodology

#### Phase 1: Evaluator Pool Setup (Week 1)

**7 evaluators across 3 model families:**
- **Claude:** sonnet-4-5, haiku
- **GPT:** gpt-4o, gpt-4o-mini
- **Gemini:** gemini-2-5-flash, gemini-2-5-pro
- **DeepSeek:** deepseek-chat (add diversity beyond big 3)

**Why 7:** Allows testing ensembles of size 1, 3, 5, 7

**Evaluation task:** Pairwise preference (which response is better for helpfulness/harmlessness?)

#### Phase 2: Ensemble Configurations (Week 1)

**Test 15 ensemble configurations:**

**Size variations:**
1. Single: Best individual model (baseline)
2. Pair: Top 2 models
3. Triple: Top 3 models (literature standard)
4. Quintuple: Top 5 models
5. Septuple: All 7 models

**Composition variations (for size=3):**
6. Homogeneous-same: 3× claude-sonnet-4-5 (different seeds)
7. Homogeneous-family: 3 Claude models (sonnet + haiku + opus if available)
8. Diverse-top: Top model from each family (Claude, GPT, Gemini)
9. Diverse-balanced: Mix of strict/moderate/lenient (Sonnet + GPT-4o + Flash)

**Aggregation strategies (for size=3, diverse-top):**
10. Mean: Average of 3 scores
11. Median: Middle score
12. Majority: Mode (most common vote)
13. Weighted: Weighted by individual model's human-agreement from Phase 1
14. Confidence-weighted: Weight by model's self-reported confidence
15. Iterative consensus: Models see each other's reasoning, then re-vote

#### Phase 3: Data Collection (Week 2)

**Trials:**
- 200 examples × 15 configurations = **3,000 base evaluations**
- Configurations with multiple models multiply this
- Total: ~**10,000 evaluations** (accounting for ensemble sizes)
- Estimated cost: ~$100-150

**For each configuration:**
1. Evaluate each response in pair
2. Determine preference (A > B, B > A, or tie)
3. Log: configuration, individual scores, aggregated score, reasoning

#### Phase 4: Analysis (Week 2-3)

**Metrics:**

1. **Agreement with human ground truth:**
   ```
   For each configuration:
   - % agreement with human pairwise preferences
   - Cohen's Kappa (chance-corrected agreement)
   ```

2. **Reliability improvement curve:**
   ```
   Plot: Ensemble size (X) vs Human Agreement (Y)
   - Fit curve to identify diminishing returns point
   - Calculate marginal gain per additional evaluator
   ```

3. **Cost-benefit analysis:**
   ```
   For each configuration:
   - Cost = (number of API calls) × (avg price per call)
   - Benefit = (human agreement % - baseline single model %)
   - Efficiency = Benefit / Cost
   ```

4. **Variance detection:**
   ```
   For trials where ensemble shows high disagreement:
   - Do these correlate with human "close call" cases?
   - Can we predict high-variance trials beforehand? (e.g., by response length, topic, etc.)
   ```

**Hypotheses:**
- H1: Ensemble of 3 diverse models > single best model (literature finding)
- H2: Diminishing returns after 5 evaluators (cost not justified)
- H3: Diverse ensemble > homogeneous ensemble (different biases cancel out)
- H4: Median aggregation > mean (robust to outliers like Gemini Pro's ceiling effect)
- H5: Weighted voting improves over simple majority (calibrate by reliability)
- H6: High ensemble variance predicts human "close call" cases

#### Phase 5: Optimization (Week 3)

**Develop heuristic:**
```python
def evaluate(example):
    # Cheap pre-screening
    initial_score = cheap_model(example)
    confidence = cheap_model.confidence

    if confidence > 0.9:
        # Clear case, no ensemble needed
        return initial_score
    else:
        # Ambiguous, use ensemble
        ensemble_scores = [model(example) for model in top_3_diverse]
        return median(ensemble_scores)
```

**Test heuristic:**
- Does it achieve 90% of full-ensemble accuracy at 50% cost?
- What's the optimal confidence threshold?

#### Phase 6: Reporting (Week 4)

**Deliverables:**
1. **Ensemble configuration recommendations** by use case:
   - High accuracy needed: 5-model diverse ensemble, median aggregation
   - Cost-constrained: 3-model diverse ensemble
   - Production: Adaptive (single + ensemble for low-confidence cases)

2. **Diminishing returns analysis:** "Adding 4th and 5th evaluator improves accuracy by only 2% each"

3. **Practical tooling:**
   - Ensemble evaluation class (easily configurable)
   - Cost calculator (estimate ensemble overhead)

---

### Success Metrics

**Minimum viable:**
- Test 15 configurations, identify best (highest agreement with humans)
- Show that ensemble > single evaluator (validate literature)
- Calculate cost-benefit for each configuration

**Strong outcome:**
- Identify optimal ensemble size (where gains plateau)
- Show diverse > homogeneous (novel if true)
- Develop adaptive ensemble (uses single model for clear cases, ensemble for ambiguous)

**Publication-quality:**
- Novel contribution: First systematic comparison of ensemble parameters
- Practical impact: Cost-benefit analysis with recommendations
- Methodological: Heuristic for detecting when ensemble is needed

---

### Timeline & Resources

**Week 1:** Evaluator setup, configuration design (15 hours)
**Week 2:** Data collection (10K evaluations, automated) (10 hours)
**Week 3:** Analysis, optimization, adaptive heuristic (30 hours)
**Week 4:** Paper writing, tooling, recommendations (20 hours)

**Total:** 3-4 weeks, 75 hours, ~$150 API costs

---

### Extension Opportunities

1. **Multi-turn evaluation:** Does ensemble benefit persist in dialogue (MT-Bench)?
2. **Iterative consensus:** Compare ICE framework to simple voting
3. **Cross-domain generalization:** Train ensemble on HH-RLHF, test on WebGPT
4. **Active learning:** Can ensemble uncertainty guide which examples need human review?

---

## Experiment 4: Chain-of-Thought Impact on LLM Judge Reliability

### Research Gap Addressed

**Gap:** Mixed evidence on CoT effectiveness for LLM judges - no controlled study isolating its impact across task types and models.

**Existing work:**
- Anecdotal reports: CoT reduces variance, increases human agreement
- Counter-evidence: "Little evidence to favor CoT for NLG evaluation"
- "For simpler tasks, CoT has neutral or negative effects"

**What's missing:**
- Controlled comparison: Same rubric ± CoT requirement
- Across multiple task types (objective vs subjective)
- Across multiple models (not just GPT-4)
- Measuring: (a) inter-rater reliability, (b) human agreement, (c) within-model consistency
- Quantify cost: CoT increases token usage by how much?

---

### Research Question

**Primary:** Does requiring chain-of-thought (explanation before scoring) improve LLM judge reliability, and does the benefit vary by evaluation criterion type (objective vs subjective)?

**Secondary:**
- Does CoT improve agreement with human ground truth?
- Does CoT reduce within-evaluator variance (across seeds)?
- Does CoT improve inter-evaluator agreement (across models)?
- Does CoT benefit vary by model (Claude vs GPT vs Gemini)?
- What is the cost overhead? (tokens, latency)
- Does CoT quality (explanation depth) correlate with score accuracy?

---

### Datasets

**Objective criterion (Factuality):** OpenAI WebGPT (20K factuality comparisons)
**Subjective criterion (Coherence):** OpenAI Summarization (64K coherence ratings)

**Subset:** 100 examples from each (200 total)
- Allows testing whether CoT effect differs by criterion type

---

### Methodology

#### Phase 1: Rubric Design (Week 1)

**Create 2 versions of same rubric:**

**Version A: Direct Scoring (No CoT)**
```
Evaluate the factual accuracy of this response on a scale of 0-100.

Score: [0-100]
```

**Version B: Chain-of-Thought (CoT Required)**
```
Evaluate the factual accuracy of this response.

First, identify:
1. What claims are made in the response?
2. Which claims are supported by the provided context?
3. Are there any contradictions or unsupported claims?

Then, based on your analysis, provide a score from 0-100.

Reasoning: [Your analysis]
Score: [0-100]
```

**Key difference:** Version B requires explicit reasoning **before** scoring.

#### Phase 2: Experimental Design (Week 1)

**Conditions:**
- 2 rubric versions (Direct vs CoT)
- 2 criteria (Factuality vs Coherence)
- 4 evaluators (claude-sonnet-4-5, gpt-4o, gemini-2-5-flash, claude-3-5-haiku)
- 5 seeds per condition (test within-evaluator consistency)
- 100 examples per criterion

**Trials:**
- 2 rubrics × 2 criteria × 4 evaluators × 100 examples × 5 seeds = **8,000 evaluations**
- Estimated cost: ~$100-125 (CoT increases token usage)

#### Phase 3: Data Collection (Week 2)

**For each evaluation:**
1. Apply rubric (Direct or CoT version)
2. Extract score and reasoning (if CoT)
3. Log: rubric_type, criterion, evaluator, seed, score, reasoning, token_count, latency

**Control:**
- Same system message across all conditions
- Same temperature (use optimal from Experiment 2)
- Same max_tokens (adjust for CoT overhead)

#### Phase 4: Analysis (Week 2-3)

**Metrics:**

1. **Agreement with human ground truth:**
   ```
   For each (rubric_type, criterion, evaluator):
   - Calculate correlation with human ratings (Pearson r, Spearman ρ)
   - Higher = better alignment
   ```

2. **Within-evaluator consistency:**
   ```
   For each (rubric_type, criterion, evaluator, example):
   - Calculate variance across 5 seeds
   - Lower variance = more consistent
   ```

3. **Inter-evaluator reliability:**
   ```
   For each (rubric_type, criterion):
   - Calculate mean pairwise correlation across 4 evaluators
   - Higher = rubric reduces disagreement
   ```

4. **Cost overhead:**
   ```
   CoT_overhead = (avg_tokens_CoT - avg_tokens_Direct) / avg_tokens_Direct
   Latency_overhead = (avg_latency_CoT - avg_latency_Direct) / avg_latency_Direct
   ```

5. **Explanation quality analysis (if CoT):**
   ```
   - Length of reasoning (token count)
   - Does longer reasoning correlate with accuracy?
   - Qualitative: Do explanations cite evidence? Make logical inferences?
   ```

**Hypotheses:**
- H1: CoT improves human agreement for **objective criteria** (factuality) but not subjective (coherence)
- H2: CoT reduces within-evaluator variance (forces consistent reasoning process)
- H3: CoT improves inter-evaluator agreement (shared reasoning framework)
- H4: CoT benefit is larger for Claude models (trained on CoT via Constitutional AI)
- H5: CoT overhead is 30-50% more tokens (quantify cost)
- H6: Longer explanations do NOT correlate with higher accuracy (verbosity ≠ quality)

#### Phase 5: Qualitative Analysis (Week 3)

**Manual review of 50 CoT explanations:**
- Categorize reasoning types: Evidence-citing, Logical inference, Hedging, Confabulation
- Score explanation quality (0-3 scale)
- Test: Does explanation quality predict score accuracy?

**Goal:** Understand **when** CoT helps vs hurts

#### Phase 6: Reporting (Week 4)

**Deliverables:**
1. **Recommendation:** When to use CoT (objective criteria) vs when to skip (subjective, cost-sensitive)
2. **Cost-benefit calculator:** "CoT improves factuality agreement by 8% at 40% cost increase - worth it?"
3. **Prompt templates:** Optimized CoT rubrics based on findings

---

### Success Metrics

**Minimum viable:**
- Complete 8,000 evaluations (2 rubric types × 2 criteria × 4 models)
- Show whether CoT improves reliability (yes/no, effect size)
- Quantify cost overhead

**Strong outcome:**
- Nuanced finding: CoT helps for objective, neutral/negative for subjective (reconciles mixed literature)
- Identify which models benefit most from CoT
- Provide cost-benefit tradeoff (when is overhead justified?)

**Publication-quality:**
- Novel contribution: First controlled study isolating CoT effect across criterion types
- Methodological rigor: 5 seeds per condition, multiple models
- Practical impact: Clear recommendations for when to use CoT
- Qualitative depth: Explanation quality analysis (what makes good reasoning?)

---

### Timeline & Resources

**Week 1:** Rubric design, infrastructure (15 hours)
**Week 2:** Data collection (8K evaluations, automated) (10 hours)
**Week 3:** Quantitative analysis + qualitative review (30 hours)
**Week 4:** Paper writing, templates, recommendations (20 hours)

**Total:** 3-4 weeks, 75 hours, ~$125 API costs

---

### Extension Opportunities

1. **Structured CoT formats:** Test different reasoning frameworks (claim extraction, evidence mapping, logical chains)
2. **Self-critique:** CoT + "Review your score - is it justified?" (second-order reasoning)
3. **Multi-agent CoT:** Two models debate in CoT, then re-score
4. **Fine-tuning on CoT:** Do models learn to give better explanations?

---

## Experiment 5: Factuality Evaluation Validation (Constitutional Reasoning Bridge)

### Research Gap Addressed

**Gap:** No validation of LLM judges specifically for factual adherence evaluation in value-laden reasoning tasks.

**Existing work:**
- OpenAI WebGPT: LLM judges for factuality in QA (value-neutral domain)
- Constitutional AI: Values-based training, but no public evaluator validation
- Our Phase 1: Constitutional reasoning evaluation, but no ground truth

**What's missing:**
- Validated rubric for "Did reasoning accept facts without distortion?"
- Test whether LLM judges can separate factuality from value agreement
- Human-labeled examples of value-laden reasoning with factuality ratings

---

### Research Question

**Primary:** Can LLM judges reliably evaluate factual adherence (acceptance of facts without distortion) in value-laden reasoning, separating factuality from value agreement?

**Secondary:**
- Which rubric design best captures "factual adherence" distinct from "value alignment"?
- Do evaluators penalize reasoning they disagree with, even when factually grounded?
- Can we create synthetic ground truth by having experts rate factual adherence?

---

### Dataset

**Primary:** OpenAI WebGPT (20K factuality comparisons)
- Use as **calibration set** for factuality evaluation

**Secondary (Novel):** Create small human-labeled dataset for value-laden factual reasoning
- 50 examples of constitutional reasoning from our Phase 1 experiment
- User + AI safety researcher rate: "Did this response accept the facts without distortion?" (binary)
- Compare LLM judge scores to human consensus

**This experiment bridges Experiment A (constitutional adherence) and Experiment B (LLM judge validation)**

---

### Methodology

#### Phase 1: Rubric Calibration (Week 1)

**Use WebGPT to calibrate factuality rubric:**

1. Test 3 rubric designs on WebGPT subset (100 examples):
   - Binary: Factually accurate? (Yes/No)
   - Ternary: Factual adherence (0=distorted, 1=partial, 2=full)
   - Decomposed: 3 binary questions (contradicts facts? adds unsupported? distorts selectively?)

2. Calculate agreement with WebGPT human ratings

3. Select best rubric (highest human agreement)

#### Phase 2: Human Annotation (Week 1-2)

**Create ground truth for value-laden reasoning:**

1. Sample 50 trials from Phase 1 constitutional adherence experiment
   - Stratified across: 5 constitutions, 5 scenarios, 2 models (high/low performers)

2. Annotation task for 3 expert raters (user + 2 AI safety researchers or hired annotators):
   ```
   Scenario facts: [Provided]
   Model reasoning: [Constitutional response]

   Question: Did the model accept the scenario facts without distortion?

   Distortion includes:
   - Contradicting stated facts
   - Adding unsupported facts
   - Selective emphasis to weaken facts
   - Minimizing facts that conflict with values

   Rating: ACCEPT / DISTORT

   If DISTORT, cite specific example: [Text field]
   ```

3. Calculate inter-human agreement (Cohen's Kappa)
   - Goal: κ > 0.7 (substantial agreement)
   - If κ < 0.7: Refine rubric, re-annotate subset

4. Use majority vote as ground truth (2 of 3 agree)

#### Phase 3: LLM Judge Validation (Week 2)

**Test 4 LLM judges on human-labeled examples:**

1. Use calibrated rubric from Phase 1 (likely decomposed binary questions)

2. Evaluate all 50 examples with 4 models × 5 seeds = **1,000 evaluations**

3. Calculate:
   - Agreement with human ground truth (% match, Cohen's Kappa)
   - Model-specific bias: Do they penalize reasoning from certain constitutions?

#### Phase 4: Bias Detection (Week 2-3)

**Test whether evaluators conflate factuality with value agreement:**

**Method:**
1. For each model, calculate:
   ```
   Factual_Adherence_Score(constitution) = Avg score for that constitution's reasoning
   ```

2. If evaluator is unbiased:
   - Scores should be similar across constitutions (facts are constant)

3. If evaluator is biased:
   - Scores will vary by constitution (penalizing disagreeable values)

**Statistical test:**
- ANOVA: Does mean factual adherence score differ significantly by constitution?
- If p < 0.05: Evaluator shows value bias

**Hypothesis:** Gemini models will show value bias (ceiling effect suggests leniency correlated with value alignment)

#### Phase 5: Rubric Iteration (Week 3)

**If initial results show bias, refine rubric:**

**Technique 1: Explicit bracketing**
```
IMPORTANT: You may personally disagree with the values expressed in this reasoning.
Your task is NOT to judge whether the reasoning is morally correct.

Your ONLY task is to determine: Did the reasoning accept the stated facts without distortion?

Ignore whether you agree with the conclusion. Focus only on factual adherence.
```

**Technique 2: Counterfactual priming**
```
Before evaluating, imagine the same reasoning with the opposite conclusion.
Would you still judge it as factually adherent?
If your answer changes, you may be biased by value agreement.
```

**Re-test:** Does explicit bracketing reduce value bias?

#### Phase 6: Application to Phase 1 Data (Week 4)

**Apply validated evaluator to Phase 1 constitutional adherence experiment:**

1. Use best-performing LLM judge (highest human agreement, lowest bias)

2. Re-evaluate all Phase 1 trials (300 trials × validated evaluator)

3. Compare to original Sonnet 4.5 scores:
   - Correlation: Does validated evaluator agree with original?
   - If r > 0.7: Original results are validated
   - If r < 0.5: Original results are suspect, use new scores

4. Report: "Phase 1 findings validated/revised using human-grounded evaluator"

---

### Success Metrics

**Minimum viable:**
- Create 50-example human-labeled dataset (will be valuable for future research)
- Identify LLM judge with >70% agreement with human factuality ratings
- Test whether evaluators show value bias (yes/no)

**Strong outcome:**
- Validate that LLM judges can separate factuality from value agreement (no bias detected)
- Develop rubric that eliminates value bias (explicit bracketing works)
- Retrospectively validate or revise Phase 1 constitutional adherence findings

**Publication-quality:**
- Novel contribution: First validation of LLM factuality judges in value-laden reasoning
- Methodological: Rubric design for separating factuality from value agreement
- Dataset contribution: Public release of human-labeled constitutional reasoning examples
- Bridge: Connects constitutional AI research (Anthropic) with LLM-as-judge validation

---

### Timeline & Resources

**Week 1:** Rubric calibration with WebGPT, annotation task design (20 hours)
**Week 2:** Human annotation (15 hours user + annotators), LLM evaluation (1K calls) (15 hours)
**Week 3:** Bias analysis, rubric iteration, re-testing (25 hours)
**Week 4:** Phase 1 re-evaluation, comparison, reporting (20 hours)

**Total:** 4 weeks, 80 hours, ~$50 API costs (+ $100-300 for hired annotators if needed)

---

### Extension Opportunities

1. **Expand human-labeled dataset:** 50 → 200 examples (stronger ground truth)
2. **Constitutional diversity:** Test on different value systems (religious, cultural, political)
3. **Multi-turn reasoning:** Does factual adherence degrade over conversation turns?
4. **Fine-tune evaluator:** Use human-labeled examples to fine-tune small model as specialist judge

---

## Experiment Comparison & Recommendation

### Selection Matrix

| Experiment | Impact | Feasibility | Cost | Timeline | Fills Gap | Novel Contribution |
|------------|--------|-------------|------|----------|-----------|-------------------|
| **1. Rubric Design** | High | High | $75 | 3-4 weeks | Yes | First systematic comparison |
| **2. Temperature/Seed** | Medium | High | $100 | 3-4 weeks | Yes | Challenges temp=0 dogma |
| **3. Ensemble Optimization** | High | High | $150 | 3-4 weeks | Yes | Cost-benefit optimization |
| **4. CoT Impact** | Medium | High | $125 | 3-4 weeks | Yes | Controlled study, reconciles mixed evidence |
| **5. Factuality Bridge** | **Highest** | Medium | $50-350 | 4 weeks | Yes | **Bridges your two experiments** |

---

### Recommendation Priority

**Tier 1 (Highest Impact, Do First):**

**Experiment 5: Factuality Evaluation Validation**
- **Why:** Directly addresses your original research question (constitutional adherence)
- **Why:** Creates human-labeled dataset (reusable asset)
- **Why:** Validates/revises Phase 1 findings (salvages sunk cost)
- **Why:** Most publishable (bridges constitutional AI + LLM-as-judge literatures)
- **Challenge:** Requires human annotation (but only 50 examples, feasible)

**Experiment 1: Rubric Design Validation**
- **Why:** Foundational (informs all other experiments)
- **Why:** Highest generalizability (rubrics used in all LLM judge systems)
- **Why:** Extends Google's work to multiple models/criteria
- **Why:** Easiest to publish (clear methodology, public dataset)

---

**Tier 2 (High Value, Do Second):**

**Experiment 3: Ensemble Optimization**
- **Why:** Practical impact (cost-benefit for production systems)
- **Why:** Extends recent work (ICE, PoLL frameworks)
- **Why:** Solves your Phase 1 problem (ensemble consensus as ground truth alternative)

**Experiment 2: Temperature/Seed Optimization**
- **Why:** Could challenge conventional wisdom (temp=0 may not be optimal)
- **Why:** Practical recommendations for all LLM judge users
- **Why:** Relatively cheap ($100) with potentially high insight

---

**Tier 3 (Interesting but Lower Priority):**

**Experiment 4: CoT Impact**
- **Why:** Mixed evidence to reconcile
- **Why:** Less foundational than rubric/temperature questions
- **Why:** Could be combined with Experiment 1 (rubric variations include ± CoT)

---

### Combined/Hybrid Approaches

**Option A: Rubric + Temperature (6 weeks)**
- Run Experiment 1 (rubric design) and Experiment 2 (temperature) together
- Share infrastructure, dataset (WebGPT)
- Test: Does optimal temperature vary by rubric format?
- Combined insight: "Use binary rubric at temperature=0.3"

**Option B: Ensemble + Factuality (6 weeks)**
- Run Experiment 3 (ensemble) and Experiment 5 (factuality) together
- Use ensemble consensus as ground truth for Phase 5 of Experiment 5
- Validate: Do ensemble scores match human factuality ratings?
- Bridge to Phase 1: Re-evaluate using ensemble instead of single Sonnet 4.5

**Option C: All-in-one Validation Suite (8-10 weeks)**
- Sequential pipeline:
  1. Week 1-2: Rubric design (Exp 1) → Identify best rubric
  2. Week 3-4: Temperature optimization (Exp 2) → Identify optimal temperature
  3. Week 5-6: Ensemble optimization (Exp 3) → Identify best ensemble
  4. Week 7-8: Apply optimized evaluator (best rubric + temp + ensemble) to factuality validation (Exp 5)
  5. Week 9-10: Re-evaluate Phase 1 constitutional adherence with fully validated evaluator
- **Outcome:** Publishable as comprehensive methodology paper + validated constitutional adherence findings

---

## Recommended Next Steps

### Immediate (This Week)

1. **Choose experiment priority** based on:
   - Career goals (breadth vs depth)
   - Timeline constraints (3-4 weeks vs 8-10 weeks)
   - Resource availability (can you hire annotators for Exp 5?)

2. **Set up infrastructure:**
   - Implement prompt logging (audit trail)
   - Build evaluation harness (reusable across experiments)
   - Create results database schema

3. **Download datasets:**
   - WebGPT comparisons (Exp 1, 2, 4)
   - MT-Bench (Exp 2)
   - HH-RLHF (Exp 3)
   - Prepare Phase 1 data for human annotation (Exp 5)

### Short-term (Next 2 Weeks)

4. **Pilot study (100 evaluations):**
   - Test infrastructure with small subset
   - Validate parsing (JSON extraction)
   - Estimate actual costs
   - Debug any API issues

5. **Refine experimental design based on pilot:**
   - Adjust sample sizes if needed
   - Optimize batch processing
   - Confirm metrics pipeline works

### Medium-term (Weeks 3-6)

6. **Execute chosen experiment(s)**

7. **Parallel work:**
   - Start drafting methodology section while data collection runs
   - Create visualizations as results come in
   - Prepare code for public release

### Long-term (Weeks 7-10+)

8. **Publication:**
   - Submit to: NeurIPS, ICML, or ICLR (ML conferences)
   - Or: AI safety-specific venues (AI Safety Conference, AAAI Safety track)
   - Or: arXiv preprint with Twitter/blog post (reach AI safety community)

9. **Portfolio building:**
   - Public GitHub: Evaluation harness + experiment code
   - Blog post: "What I learned validating LLM judges"
   - LinkedIn: Highlight research contributions
   - Anthropic application: Link to research as evidence of rigor

---

## Conclusion

All 5 proposed experiments:
- ✅ Fill identified research gaps
- ✅ Use public datasets (no expensive annotation, except Exp 5)
- ✅ Are feasible within 3-4 weeks each
- ✅ Produce publishable results
- ✅ Demonstrate research depth and rigor

**Highest-impact path:** Start with **Experiment 5 (Factuality Bridge)** to validate your Phase 1 work, then **Experiment 1 (Rubric Design)** to establish foundational methodology. This sequence:
1. Salvages your constitutional adherence research
2. Produces novel methodological contribution
3. Creates reusable infrastructure for future work
4. Demonstrates both applied and foundational research skills

**Alternative path (if annotation is blocker):** Start with **Experiment 1 (Rubric)** + **Experiment 2 (Temperature)** hybrid (6 weeks) to establish methodology, then apply to **Experiment 5** using validated evaluator instead of human annotation.

Either path positions you well for AI safety research roles at companies like Anthropic.
