# Analysis and Publication Plan

**Document Purpose:** Strategic roadmap for analyzing exp_20251028_134615 data and publishing findings

**Date Created:** 2025-10-31
**Status:** Active
**Timeline:** 3-4 weeks to first publication

---

## Executive Summary

**What We Have:** A complete methodology validation experiment with 360 trials × 5 evaluators × 3 rubric formats = 5,400 evaluations testing constitutional reasoning across 5 models, 6 value frameworks, and 12 polarizing scenarios.

**What We're Publishing:** "Constitutional Reasoning in Frontier AI: Do Models Maintain Factual Integrity When Reasoning From Different Value Systems?" - a single comprehensive publication with preliminary human validation.

**Timeline:** 3-4 weeks to first draft with preliminary validation
**Cost:** $0 (self-validation + volunteer recruitment)
**Differentiation:** Research rigor + tool building + pragmatic validation approach

---

## Strategic Context

### Research Audit Findings

**Planned:** Phase 0.5 validation test (10-20 trials)
**Actual:** Full-scale experiment (360 trials × 3 rubric formats)
**Implication:** Accidentally ran an excellent methodology validation experiment

**What We Can Answer NOW:**
- ✅ Q3: Model × Constitution interaction (full factorial design)
- ✅ Q4: Rubric design optimization (3 formats tested)
- ⚠️ Q1/Q2: Constitutional adherence (requires human validation)

**What's Blocked:**
- ❌ Q1/Q2 require human ground truth for confident claims
- ❌ Q6 (evaluator bias) requires human validation

### Strategic Priorities (User-Defined)

**Primary:** Job applications / career (Anthropic, AI safety roles)
**Secondary:** Personal learning + Intellectual curiosity (Story B: constitutional reasoning)
**Tertiary:** Research contribution (nice-to-have, not required)

**Timeline Constraint:** Need portfolio pieces ASAP for job applications

**Budget Constraint:** $0 (no paid annotators)

---

## Publication Strategy

### Chosen Approach: Story B with Preliminary Validation

**Publication Title:** "Constitutional Reasoning in Frontier AI: Measuring Factual Integrity Across Value Systems"

**Core Research Question:** Can AI models maintain factual integrity when reasoning from different constitutional frameworks (value systems)?

**Why This Story:**
1. **User motivation:** This was the original research intent
2. **Intellectual depth:** Tests fundamental AI alignment question
3. **Novel contribution:** First systematic test of value-driven reasoning vs fact-handling
4. **Differentiation:** More interesting than "Binary rubrics beat Likert" (already known)

**Why Preliminary Validation:**
1. **Credibility:** "Validated findings" >> "Unvalidated findings" for job applications
2. **Risk mitigation:** Confirm LLM evaluators aren't completely wrong before publishing
3. **Thoroughness signal:** Shows understanding of research rigor
4. **Feasible:** 30-50 trials, solo annotation, 5-10 hours

### Publication Structure

**1. Introduction (2 hours)**
- Motivation: AI alignment question (can values coexist with epistemic integrity?)
- Research gap: No systematic test of constitutional reasoning across models
- Our contribution: 360 trials, 5 models, 6 constitutions, human-validated

**2. Methods (3 hours)**
- **Experimental Design:** 12 scenarios × 6 constitutions × 5 models = 360 trials
- **Layer 2:** Constitutional reasoning (5 frontier models)
- **Layer 3:** Integrity evaluation (5 LLM judges × 3 rubric formats)
- **Rubric Validation:** Tested Likert/Binary/Ternary, selected [winner] (brief)
- **Human Validation:** Preliminary validation (n=30-50, k=1, author), LLM-human r=0.XX
- **Metrics:** Epistemic Integrity, Value Transparency, overall scores

**3. Results (4 hours)**
- **3.1 Rubric Comparison (Q4 - brief):** Binary/Ternary achieves r=0.XX vs Likert r=0.YY
- **3.2 Model Performance (Q1):** Mean Epistemic Integrity by model (do models maintain facts?)
- **3.3 Constitution Effects (Q2):** Mean Epistemic Integrity by constitution (which values lead to distortion?)
- **3.4 Model × Constitution Interaction (Q3):** Do certain models struggle with certain values?
- **3.5 Human Validation:** LLM-human correlation, agreement patterns

**4. Discussion (2 hours)**
- **Interpretation:** What do findings mean for AI alignment?
- **Implications:** Can AI systems be steered by values without fact distortion?
- **Limitations:** Preliminary validation (k=1), LLM-evaluated (bias risks), domain-specific
- **Future Work:** Expanded validation (community crowdsourcing), causal mechanisms

**5. Open Science & Community Validation (1 hour)**
- **Validation Tool:** Simple web interface for community annotation
- **Call to Action:** Invite community to expand validation dataset
- **Living Research:** Results will be updated as validation expands
- **Data/Code Release:** Full replication package on GitHub

**6. Conclusion (30 minutes)**
- Summary: Models [do/don't] maintain factual integrity, [constitution X] causes most distortion
- Contribution: First systematic test of constitutional reasoning
- Next steps: Expanded validation, causal analysis, deployment implications

**Total Writing Time:** 12-15 hours

---

## Execution Timeline

### Week 1: Tier 1 Analyses (8-11 hours)

**Goal:** Understand what the data shows, identify best rubric for validation

**Tasks:**

1. **Analysis 1.1: Rubric Comparison** (~3 hours)
   - Script: `scripts/compare_rubric_strategies.py`
   - Load: layer3/, layer3_binary/, layer3_ternary/ (360 trials each)
   - Calculate: Pairwise correlations (Pearson r) for all 10 evaluator pairs per rubric
   - Metrics: Mean inter-rater reliability (r̄), ICC, 95% CI
   - Output: "Binary r̄=0.XX vs Ternary r̄=0.YY vs Likert r̄=0.ZZ"
   - **Decision:** Which rubric to use for human validation (expected: Binary or Ternary)

2. **Analysis 1.3: Evaluator Agreement Patterns** (~2 hours)
   - Calculate: Pairwise correlations for 5 evaluators using best rubric
   - Identify: Outlier evaluator (if any) - test if Gemini still outlier at n=360
   - Create: Consensus scores (mean/median across evaluators, with/without outlier)
   - Stratified reliability: By constitution, scenario, dimension
   - Output: "Use all 5 evaluators" OR "Exclude Gemini (outlier)"
   - **Decision:** Which evaluator scores to trust for Q1/Q2/Q3

3. **Analysis 1.2: Model × Constitution Interaction** (~3 hours)
   - Calculate: Mean Epistemic Integrity per Model × Constitution cell (5×6=30 cells)
   - Two-way ANOVA: Test Model × Constitution interaction
   - Post-hoc: Tukey HSD if interaction significant
   - Visualize: Interaction plot (Model on X-axis, 6 lines for constitutions)
   - Output: "Model A excels with Constitution X but struggles with Y"
   - **Answers Q3 directly**

4. **Analysis 1.4: Dimensional Structure Validation** (~2 hours)
   - Calculate: r(Epistemic Integrity, Value Transparency) per evaluator
   - Test: Are dimensions independent (target: r < 0.60)
   - PCA: Do 2 dimensions capture >90% variance?
   - Evaluator patterns: Which evaluators conflate dimensions?
   - Output: "Dimensions are [independent/correlated], 2D rubric [justified/redundant]"
   - **Supports Q6 (bias detection)**

**Deliverables:**
- 4 analysis reports (Jupyter notebooks or markdown)
- Best rubric identified (for validation)
- Consensus evaluator scores (for Q1/Q2/Q3)
- Preliminary findings for Q3 (Model × Constitution)

**Status at End of Week 1:** Ready to design validation rubric, know which rubric to use, have preliminary constitutional adherence findings

---

### Week 2: Validation Design (3-5 hours)

**Goal:** Create clear rubric and tooling for self-validation

**Tasks:**

1. **Design Validation Instructions** (~2 hours)
   - Use winning rubric from Week 1 (Binary or Ternary expected)
   - Write evaluation criteria with concrete examples:
     - What counts as "fact distortion"?
     - What counts as "value transparency"?
     - Edge cases and how to handle them
   - Test on 2-3 trials yourself, refine wording based on confusion points
   - Output: 1-2 page rubric guide with examples

2. **Build Simple Validation Tool** (~1-3 hours)
   - **Option A: Google Sheets** (recommended for Week 2 - 1 hour)
     - Template columns: Trial ID, Scenario, Constitution, Model, Layer 2 Response
     - Evaluation columns: Epistemic Integrity score, Value Transparency score, Notes
     - Randomization: Use RAND() to shuffle trial order
     - Simple, no coding required

   - **Option B: Simple Web Form** (if time permits - 3 hours)
     - HTML/JavaScript single-page app
     - Load trials from JSON
     - Randomize presentation order
     - Export responses to CSV
     - Advantage: Looks more polished for portfolio

   **Recommendation:** Start with Google Sheets (fastest), build web version Week 4+ if recruiting volunteers

3. **Sample Selection for Validation** (~30 minutes)
   - Use Analysis 1.3 results (evaluator agreement patterns)
   - Stratified sample:
     - 6 constitutions × 5 trials each = 30 trials (minimal)
     - OR 6 constitutions × 8 trials = 48 trials (better)
   - Include: High-agreement trials (consensus) + High-disagreement trials (outliers)
   - Include: Range of scenarios (avoid all vaccine mandates)
   - Export: Selected trials to validation tool

**Deliverables:**
- Validation rubric guide (1-2 pages with examples)
- Validation tool (Google Sheets or web form)
- 30-50 trials selected for validation

**Status at End of Week 2:** Ready to start self-validation

---

### Week 3: Self-Validation (5-10 hours)

**Goal:** Validate 30-50 trials, calculate LLM-human correlation

**Process:**

1. **Calibration** (~30 minutes)
   - Validate 3-5 trials
   - Check: Are instructions clear? Any ambiguities?
   - Refine rubric if needed
   - Re-validate calibration trials after refinement (test consistency)

2. **Validation Sprint** (~5-8 hours)
   - Target: 30-50 trials
   - Time per trial: 10-15 minutes (read facts, read reasoning, score 2 dimensions, note reasoning)
   - Schedule: 1-2 hour blocks over 3-5 days (avoid fatigue)
   - Track: Trials where you're uncertain (edge cases for discussion section)

3. **Quality Check** (~30 minutes)
   - Self-consistency: Re-validate 5 random trials without looking at original scores
   - Calculate: Intra-rater reliability (do you agree with yourself?)
   - Target: >80% agreement with self (if lower, rubric may be ambiguous)

**Deliverables:**
- 30-50 human-validated trials (k=1 rater)
- Notes on edge cases and rubric challenges

**Status at End of Week 3:** Preliminary validation complete

---

### Week 3-4: Validation Analysis + Writing (11-16 hours)

**Goal:** Calculate LLM-human correlation, write publication draft

**Tasks:**

1. **Validation Analysis** (~1-2 hours)
   - Calculate: Pearson r between each LLM evaluator and your scores
   - For each evaluator: r(Epistemic Integrity), r(Value Transparency), r(Overall)
   - Identify: Which LLM evaluator is most human-aligned?
   - Test: Does ensemble (mean of 5 evaluators) improve alignment?
   - **Decision Criteria:**
     - r > 0.70: Excellent, publish with high confidence
     - r = 0.50-0.70: Moderate, publish with caveats
     - r < 0.50: Poor, investigate before publishing (may need rubric redesign)

2. **Write Publication Draft** (~10-15 hours)
   - Section 1: Introduction (2 hours)
   - Section 2: Methods (3 hours)
   - Section 3: Results (4 hours) - integrate all Tier 1 analyses + validation
   - Section 4: Discussion (2 hours)
   - Section 5: Validation + Community (1 hour)
   - Section 6: Conclusion (30 minutes)
   - Abstract + References (1 hour)

3. **Create Visualizations** (~2-3 hours)
   - Figure 1: Rubric comparison (mean r with 95% CI error bars)
   - Figure 2: Model × Constitution interaction plot
   - Figure 3: LLM-human correlation scatter plots
   - Figure 4: Score distributions by constitution
   - Table 1: Summary statistics (mean scores per model, per constitution)
   - Table 2: LLM-human correlation matrix

**Deliverables:**
- LLM-human correlation analysis
- Publication first draft (5,000-7,000 words)
- Visualizations (4 figures, 2 tables)

**Status at End of Week 4:** First draft ready for feedback/revision

---

### Week 4+ (Optional): Community Validation Tool

**Goal:** Build polished tool for crowdsourced validation expansion

**Tasks:**

1. **Web Interface Development** (~5-8 hours)
   - Frontend: React/Next.js or simple HTML/JS
   - Backend: Firebase or Supabase (free tier)
   - Features:
     - User authentication (track annotator IDs)
     - Randomized trial presentation
     - Progress tracking
     - Export responses to database
     - Leaderboard (optional: gamification)

2. **Deployment** (~1-2 hours)
   - Host on Vercel/Netlify (free)
   - Domain: validation.constitution-reasoning.com (or GitHub Pages)
   - Documentation: Clear instructions for validators

3. **Recruitment** (~2-3 hours)
   - Write recruitment post (AI safety Discord, Reddit, Twitter)
   - Emphasize: Contributing to open AI safety research
   - Incentive: Co-authorship for significant contributions (>50 trials)

**Deliverable:** Public validation tool, ongoing data collection

**Status:** Living research - update findings as validation expands

---

## Success Criteria

### Minimum Viable Success (Week 4)
- ✅ Tier 1 analyses complete (all 4 analyses)
- ✅ Best rubric identified
- ✅ 30 trials validated (k=1)
- ✅ LLM-human r > 0.50 (moderate alignment)
- ✅ Publication first draft complete

### Strong Success (Week 4-6)
- ✅ 50 trials validated (k=1)
- ✅ LLM-human r > 0.70 (excellent alignment)
- ✅ Publication draft polished and ready to submit
- ✅ Validation tool built (web interface)
- ✅ Recruited 2-3 volunteers for expanded validation

### Exceptional Success (Week 8+)
- ✅ 100+ trials validated (k=3+ raters)
- ✅ Inter-human reliability κ > 0.70
- ✅ Publication submitted to arXiv + AI safety venue
- ✅ Community validation ongoing (10+ volunteers)
- ✅ Code/data released on GitHub
- ✅ Blog post or tweet thread driving traffic to validation tool

---

## Risk Mitigation

### Risk 1: LLM-human correlation is low (r < 0.50)

**Likelihood:** Low (literature shows r=0.60-0.80 typical)
**Impact:** HIGH - undermines all findings

**Mitigation:**
- Validate 10 trials FIRST before committing to full 50
- If r < 0.50 on first 10: STOP, investigate
- Possible causes: Rubric ambiguity, evaluator bias, domain mismatch
- Solution: Refine rubric, re-validate subset, analyze discrepancies

**Contingency:** If validation fails, pivot to Publication Story A (rubric comparison only)

---

### Risk 2: Self-validation takes longer than 10 hours

**Likelihood:** Medium (first time validating, learning curve)
**Impact:** Low - delays by 1 week

**Mitigation:**
- Start with 30 trials (minimum), expand to 50 if time permits
- Use Google Sheets (fastest tool)
- Schedule 1-2 hour blocks (avoid fatigue)

**Contingency:** 30 trials is sufficient for preliminary validation (n=30 meets minimum per CLAUDE.md)

---

### Risk 3: Volunteer recruitment fails

**Likelihood:** Medium (no network, limited time)
**Impact:** Low - k=1 validation is still valuable

**Mitigation:**
- Self-validation is sufficient for preliminary findings
- Frame as "preliminary validation (k=1, n=50)" in publication
- Invite community expansion in Discussion section
- Build tool later if needed (not blocking)

**Contingency:** Publish with k=1 validation, clearly state limitation, invite collaboration

---

### Risk 4: Analysis reveals unexpected patterns (findings not interesting)

**Likelihood:** Low (data already collected, unlikely to be empty)
**Impact:** Medium - less compelling publication

**Mitigation:**
- ANY finding is publishable (null results are results)
- Frame unexpected findings as surprising discoveries
- Negative results: "Models maintain factual integrity" is also interesting

**Contingency:** Pivot to Story A (rubric comparison) if constitutional findings are weak

---

## Resource Requirements

### Time Investment

| Phase | Tasks | Hours |
|-------|-------|-------|
| Week 1 | Tier 1 Analyses | 8-11 |
| Week 2 | Validation Design | 3-5 |
| Week 3 | Self-Validation | 5-10 |
| Week 3-4 | Analysis + Writing | 11-16 |
| **TOTAL** | **3-4 weeks** | **27-42 hours** |

**Weekly commitment:** ~7-14 hours/week (manageable alongside job search)

---

### Financial Cost

**Total:** $0

**Breakdown:**
- Analysis: $0 (local computation)
- Validation: $0 (self-validation, volunteer recruitment)
- Tool development: $0 (Google Sheets or free web hosting)
- Publication: $0 (arXiv preprint, blog post)

**Optional future costs:**
- Professional annotators: $100-300 (if scaling validation)
- Domain name: $12/year (if building public tool)
- Cloud hosting: $0-5/month (free tier sufficient)

---

### Technical Requirements

**Software:**
- Python 3.12 (already installed)
- Analysis libraries: scipy, pandas, numpy, matplotlib (already installed)
- Optional: Jupyter notebooks (for iterative analysis)

**Data:**
- ✅ Already have: 360 trials × 3 rubrics × 5 evaluators
- ✅ No additional API calls needed (analysis only)

**Tools:**
- Week 1-3: Local Python scripts
- Week 2: Google Sheets (free, no coding)
- Week 4+: Web development (optional - HTML/JS/React)

---

## Portfolio Value Proposition

### What This Demonstrates for Job Applications

**Research Rigor:**
- ✅ Experimental design (full factorial, controlled variables)
- ✅ Statistical analysis (ANOVA, correlations, effect sizes)
- ✅ Validation methodology (human ground truth)
- ✅ Honest limitation acknowledgment (k=1 preliminary)

**Technical Breadth:**
- ✅ Python/data analysis (Tier 1 analyses)
- ✅ Statistical methods (scipy, statsmodels)
- ✅ Visualization (matplotlib, publication-quality figures)
- ✅ Optional: Web development (validation tool)

**Research Pragmatism:**
- ✅ Turned constraint ($0 budget) into opportunity (crowdsourced validation)
- ✅ Iterative approach (preliminary validation → community expansion)
- ✅ Open science mindset (public tool, data/code release)

**AI Safety Relevance:**
- ✅ Tests core alignment question (values vs facts)
- ✅ LLM-as-judge methodology (critical for AI safety research)
- ✅ Constitutional AI application (Anthropic-relevant)

**Communication:**
- ✅ Clear writing (5,000-7,000 word publication)
- ✅ Data visualization (publication-quality figures)
- ✅ Community engagement (crowdsourced validation)

### Differentiation from Typical Applicants

**Most applicants show:** Analysis skills, coding projects
**You'll show:** Analysis + validation + tool-building + research pragmatism + open science

**Talking points for interviews:**
- "I validated my LLM evaluators with 50 human-annotated trials"
- "I built a crowdsourced validation tool to expand ground truth"
- "I tested 3 rubric designs empirically before choosing one"
- "I published findings with honest preliminary validation, inviting community expansion"

---

## Next Actions

### Immediate (This Session)
1. ✅ Document created: `docs/ANALYSIS_AND_PUBLICATION_PLAN.md`
2. ⏭️ Start Tier 1 Analysis: Rubric comparison
3. ⏭️ Create analysis script: `scripts/compare_rubric_strategies.py`

### Week 1 (Next 7 Days)
1. Complete all 4 Tier 1 analyses
2. Document findings in Jupyter notebooks or markdown reports
3. Identify best rubric for validation
4. Create consensus evaluator scores

### Week 2 (Days 8-14)
1. Design validation rubric and instructions
2. Build validation tool (Google Sheets recommended)
3. Select 30-50 trials for validation (stratified sample)

### Week 3 (Days 15-21)
1. Self-validate 30-50 trials
2. Calculate LLM-human correlation
3. Start writing publication draft

### Week 4 (Days 22-28)
1. Complete publication draft
2. Create visualizations
3. Prepare for submission (arXiv, blog, conference)

---

## References

### Internal Documents
- `docs/RESEARCH_ROADMAP.md` - Original phased research plan
- `docs/DECISION_LOG.md` - Major research decisions
- `docs/RESEARCH_LLM_AS_JUDGE.md` - Literature review and validation frameworks
- `docs/EXPERIMENT_PROPOSALS.md` - 5 proposed experiments (we're doing #1)
- `PROJECT_JOURNAL.md` - Development log with implementation details

### Key Datasets
- `results/experiments/exp_20251028_134615/data/layer2/` - Constitutional reasoning (360 trials)
- `results/experiments/exp_20251028_134615/data/layer3/` - Likert evaluations (360 trials)
- `results/experiments/exp_20251028_134615/data/layer3_binary/` - Binary evaluations (360 trials)
- `results/experiments/exp_20251028_134615/data/layer3_ternary/` - Ternary evaluations (360 trials)

### Analysis Tools (Already Built)
- `analysis/data_loader.py` - Load trial data with evaluator ensemble
- `analysis/stratified_analysis.py` - Inter-evaluator correlation by subgroups
- `analysis/outlier_detection.py` - High-disagreement trial identification
- `analysis/dimensionality.py` - PCA and dimension independence testing
- `analysis/compare_evaluators.py` - Pairwise correlation and bias detection

---

**Document Status:** Living document - will be updated as analyses complete and findings emerge.

**Last Updated:** 2025-10-31
**Next Review:** End of Week 1 (after Tier 1 analyses complete)
