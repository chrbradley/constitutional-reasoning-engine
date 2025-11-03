# Understanding the Statistics: A Beginner's Guide

**Document Purpose:** Plain-language explanations of statistical concepts used in our constitutional reasoning research

**Target Audience:**
- Beginners to research statistics
- Non-statisticians reading the formal report
- Future me when I forget what these numbers mean

**Date Created:** 2025-11-03

---

## Introduction: Why This Guide Exists

When I started this research project, I knew how to run experiments and analyze data, but interpreting statistical results was new territory. Terms like "ICC," "p-values," and "effect sizes" appeared everywhere in research papers, but what did they actually *mean*?

This guide documents what I learned. It's written for people like me - technically capable, but new to formal statistical analysis. If you're reading the formal research report and wondering "What does ICC 0.31 actually tell me?", this guide is for you.

**How to Use This Guide:**
- Read it cover-to-cover to understand all the statistics we used
- Or jump to specific sections when you encounter a statistic in the report
- Each section follows the same format:
  - What we measured
  - The statistic used
  - How to interpret the range
  - Our specific result
  - What it means in plain language
  - Real-world analogy
  - Why it matters

---

## Table of Contents

1. [Inter-Rater Reliability: ICC (Intraclass Correlation Coefficient)](#icc)
2. [Statistical Significance: p-values](#p-values)
3. [Correlation: Pearson r](#pearson-r)
4. [Effect Size: η² (Eta Squared)](#effect-size)
5. [Confidence Intervals: The ± Range](#confidence-intervals)
6. [Two-Way ANOVA: Testing Interactions](#two-way-anova)
7. [Principal Component Analysis (PCA): Dimensional Structure](#pca)
8. [Quick Reference Table](#quick-reference)

---

## <a name="icc"></a>1. Inter-Rater Reliability: ICC (Intraclass Correlation Coefficient)

### What We Measured

We had 5 different AI models (Claude, GPT-4o, Gemini, Grok, DeepSeek) evaluate the same 360 responses. The question: **Do they agree with each other, or do they all score things differently?**

If evaluators disagree wildly, your measurement system is broken - you can't trust the scores. If they mostly agree, you can be confident the scores reflect something real.

### The Statistic: ICC

**ICC (Intraclass Correlation Coefficient)** measures consistency among multiple raters evaluating the same things.

**Range:** 0.0 to 1.0

| ICC Value | Interpretation | What It Means |
|-----------|----------------|---------------|
| 0.00-0.20 | Poor | Evaluators basically guessing randomly - no agreement |
| 0.21-0.40 | Fair | Some consistency, but lots of disagreement |
| 0.41-0.60 | Moderate | Evaluators reasonably aligned |
| 0.61-0.80 | Good | Evaluators mostly agree |
| 0.81-1.00 | Excellent | Evaluators almost always agree |

**Why ICC instead of just average correlation?**
- Simple correlation only compares 2 raters at a time
- ICC considers all raters simultaneously
- ICC accounts for systematic biases (one rater always scores higher)

### Our Results

We tested 3 different rubric formats (ways of scoring):

| Rubric Format | ICC Value | Interpretation |
|---------------|-----------|----------------|
| **Likert (0-100 scale)** | 0.31 | Fair agreement |
| **Ternary (Pass/Partial/Fail)** | 0.19 | Poor agreement |
| **Binary (Pass/Fail)** | 0.10 | Poor agreement |

### What This Means

**Likert Scale (Winner):**
- ICC = 0.31 means evaluators showed "fair" agreement
- Not great, but workable - evaluators were somewhat consistent
- When 5 evaluators scored a response, they tended to be in the same ballpark (e.g., scores of 85, 88, 91, 87, 90)

**Binary Scale (Loser):**
- ICC = 0.10 means evaluators had almost no agreement
- Essentially random - one evaluator says "Pass," another says "Fail"
- The rubric didn't give them enough options to meaningfully distinguish quality

### Real-World Analogy: Olympic Gymnastics

Imagine 5 judges scoring Olympic gymnastics routines:

**ICC = 0.10 (Binary rubric):**
- Judge 1: "Good routine" (Pass)
- Judge 2: "Bad routine" (Fail)
- Judge 3: "Good routine" (Pass)
- Judge 4: "Bad routine" (Fail)
- Judge 5: "Good routine" (Pass)
- **Problem:** Judges can't even agree if the routine was good or bad!

**ICC = 0.31 (Likert rubric):**
- Judge 1: 8.5 points
- Judge 2: 9.0 points
- Judge 3: 8.8 points
- Judge 4: 9.2 points
- Judge 5: 8.6 points
- **Better:** Judges roughly agree (all scored 8.5-9.2), even if not perfectly aligned

**ICC = 0.80 (ideal):**
- All judges within 0.3 points of each other
- This level of agreement is rare without extensive training

### Why This Matters

**For our research:**
- Tells us which rubric format works best (Likert won)
- Confirms our measurement isn't completely random
- Explains why we need multiple evaluators (averaging 5 improves reliability)

**General principle:**
- Before trusting any evaluation, check ICC
- ICC < 0.40 is a red flag - your rubric may be flawed
- ICC > 0.60 is good - your measurement is reliable

### The Ensemble Effect

We also calculated two types of ICC:
- **ICC(2,1) = 0.31:** Agreement of a *single* evaluator (fair)
- **ICC(2,k) = 0.69:** Agreement when *averaging all 5* evaluators (moderate)

**Key insight:** Individual evaluators aren't that reliable, but averaging them together works much better. This is why we use an ensemble of 5 evaluators rather than trusting just one.

---

## <a name="p-values"></a>2. Statistical Significance: p-values

### What We Measured

Do models genuinely respond differently to different value systems (constitutions), or did we just see random noise in our data?

For example:
- Claude scored 87 under self-sovereignty constitution
- Claude scored 89 under harm-minimization constitution
- **Question:** Is this 2-point difference real, or just random variation?

### The Statistic: p-value

A **p-value** answers: "If there's actually NO real effect, what's the probability I'd see data like this by random chance?"

**Range:** 0.0 to 1.0

| p-value | Interpretation | Meaning |
|---------|----------------|---------|
| p < 0.05 | Statistically significant | Probably a real effect |
| p < 0.01 | Highly significant | Very likely a real effect |
| p < 0.001 | Extremely significant | Almost certainly a real effect |
| p > 0.05 | Not significant | Could just be random chance |

**The 0.05 threshold:**
- By convention, researchers use p < 0.05 as "significant"
- This means: "Less than 5% chance this is random"
- Equivalently: "More than 95% confident this is real"

### Our Result

**Model × Constitution interaction: p = 0.022**

### What This Means

**Plain language:**
- If models DON'T actually respond differently to constitutions...
- There's only a 2.2% chance we'd see this pattern by random chance
- Since 2.2% < 5%, we call this "statistically significant"
- **Translation:** We're 97.8% confident the interaction is real

**What "interaction" means:**
- Not just "some models are better than others" (main effect)
- Not just "some constitutions are harder" (main effect)
- But: "The relationship depends on BOTH model AND constitution"
- Example: Claude might struggle with self-sovereignty while GPT-4o handles it fine

### Real-World Analogy: Coin Flipping

You flip a coin 100 times and get 60 heads, 40 tails. Is the coin biased?

**Calculate p-value:**
- If coin is fair (50/50), what's the chance of getting 60+ heads by luck?
- p = 0.05: 5% chance (borderline suspicious)
- p = 0.022: 2.2% chance (probably biased)
- p = 0.001: 0.1% chance (almost certainly biased)

With p = 0.022, you'd conclude: "This coin is probably biased, not just unlucky."

### Common Misinterpretations

**WRONG:** "p = 0.022 means there's a 97.8% chance our hypothesis is correct"
- p-values don't tell you the probability your hypothesis is true
- They tell you the probability of seeing your data IF the null hypothesis (no effect) is true

**WRONG:** "p = 0.022 means the effect is large or important"
- p-values measure whether an effect exists, not how big it is
- You need effect size (see next section) to know if it matters

**CORRECT:** "p = 0.022 means if there's no real interaction, we'd only see this pattern 2.2% of the time"

### Why This Matters

**For our research:**
- Confirms the Model × Constitution interaction isn't just noise
- Justifies analyzing which models work best with which constitutions
- But p = 0.022 is close to the threshold - it's real but not overwhelming

**General principle:**
- p < 0.05 is the minimum bar for "probably real"
- p < 0.001 is much stronger evidence
- Always pair p-values with effect sizes (next section)

### Multiple Comparisons Problem

**Warning:** If you test 100 hypotheses with p < 0.05, you'd expect 5 false positives by chance!

**Solution:** Bonferroni correction
- If testing N hypotheses, use threshold p < 0.05/N
- Example: Testing 10 comparisons? Use p < 0.005 instead of 0.05
- We applied this when doing post-hoc tests (Tukey HSD)

---

## <a name="pearson-r"></a>3. Correlation: Pearson r

### What We Measured

We scored each response on two dimensions:
1. **Epistemic Integrity:** Did it handle facts accurately?
2. **Value Transparency:** Did it explicitly state its values?

**Question:** Are these dimensions independent, or do they move together?

If r = 1.0, they're measuring the same thing (redundant).
If r = 0.0, they're completely independent (ideal for a 2D rubric).

### The Statistic: Pearson r

**Pearson correlation coefficient (r)** measures how closely two variables move together.

**Range:** -1.0 to +1.0

| r Value | Interpretation | What It Means |
|---------|----------------|---------------|
| +0.9 to +1.0 | Very strong positive | X goes up → Y almost always goes up proportionally |
| +0.7 to +0.9 | Strong positive | X goes up → Y usually goes up |
| +0.4 to +0.6 | Moderate positive | X goes up → Y tends to go up (lots of exceptions) |
| +0.2 to +0.3 | Weak positive | Slight tendency to move together |
| -0.1 to +0.1 | No correlation | X and Y are unrelated |
| -0.3 to -0.1 | Weak negative | X goes up → Y slightly tends to go down |
| -0.6 to -0.4 | Moderate negative | X goes up → Y tends to go down |
| -0.9 to -0.7 | Strong negative | X goes up → Y usually goes down |
| -1.0 to -0.9 | Very strong negative | X goes up → Y almost always goes down |

### Our Result

**r = 0.406** between Epistemic Integrity and Value Transparency

### What This Means

**Moderate positive correlation:**
- Responses with high factual accuracy *tend to* also be transparent about values
- But correlation is only moderate - plenty of exceptions exist
- 16.5% of variance is shared (r² = 0.165)
- **83.5% of variance is unique to each dimension**

**Dimensional independence test:**
- We set threshold: r < 0.60 means "independent enough"
- Our r = 0.406 < 0.60 → **Dimensions are sufficiently independent ✓**
- Justifies using a 2D rubric (two separate scores)

### Visual Interpretation

Imagine plotting 360 responses on a scatter plot (X = Epistemic Integrity, Y = Value Transparency):

**r = 1.0:** Perfect diagonal line (all points on line)
```
Y |     ●
  |    ●
  |   ●
  |  ●
  | ●
  |______ X
```

**r = 0.0:** Random cloud (no pattern)
```
Y | ● ●  ●
  |  ●● ●
  | ●  ●●
  |● ●  ●
  |  ●● ●
  |______ X
```

**r = 0.406:** Loose diagonal cloud (trend visible, but lots of scatter)
```
Y |    ●●
  |   ●●●
  |  ●● ●
  | ●● ●
  |●●  ●
  |______ X
```

### Real-World Analogy: Height and Basketball Skill

**r = 0.90 (very strong):**
- Almost all tall people are skilled players
- Almost all short people struggle
- Height predicts skill very well

**r = 0.40 (moderate - like our result):**
- Tall people *tend to* be better
- But plenty of short skilled players exist (Muggsy Bogues, 5'3")
- And some tall players aren't that good
- Height matters, but lots of other factors matter too

**r = 0.0 (no correlation):**
- Height has nothing to do with skill
- Tall and short players equally distributed across skill levels

### Why This Matters

**For our research:**
- Confirms our 2D rubric measures two distinct constructs
- If r was 0.90, evaluators couldn't distinguish the dimensions (halo effect)
- If r was 0.0, dimensions would be completely unrelated (might be suspicious)
- r = 0.406 is the "Goldilocks zone" - related but distinct

**Identifies response types:**
Based on the scatter plot, we can categorize responses:
- **High-high:** Fact-accurate AND value-transparent (ideal)
- **High-low:** Fact-accurate but value-opaque (mysterious reasoning)
- **Low-high:** Fact-distorted but value-transparent (motivated reasoning)
- **Low-low:** Fact-distorted AND value-opaque (worst case)

If dimensions were perfectly correlated (r = 1.0), we couldn't make these distinctions.

### Per-Evaluator Correlations

We also checked if individual evaluators conflate the dimensions:

| Evaluator | r Value | Interpretation |
|-----------|---------|----------------|
| Gemini 2.5 Pro | 0.455 | Moderate (highest, but OK) |
| Claude Sonnet 4.5 | 0.251 | Weak |
| DeepSeek Chat | 0.173 | Very weak |
| Grok-3 | 0.160 | Very weak |
| GPT-4o | -0.237 | Weak *negative* |

**Key insight:** All evaluators show r < 0.70 (our conflation threshold), so none are systematically conflating the dimensions.

**GPT-4o anomaly:** Negative correlation is interesting - GPT-4o sees fact-handling and value-transparency as somewhat inverse. Hypothesis: GPT-4o might penalize responses that are "too preachy" about values?

---

## <a name="effect-size"></a>4. Effect Size: η² (Eta Squared)

### What We Measured

We found a statistically significant Model × Constitution interaction (p = 0.022). But is this a BIG effect or a tiny one?

**The problem with p-values alone:**
- p < 0.05 tells you an effect is *real*
- But doesn't tell you if it *matters*
- With huge sample sizes, even tiny effects become "significant"

**Effect size** tells you how much of the variance is explained.

### The Statistic: η² (Eta Squared)

**η² (eta squared)** measures what proportion of variance in the outcome is explained by your predictor.

**Range:** 0.0 to 1.0 (usually reported as percentage)

| η² Value | Interpretation | What It Means |
|----------|----------------|---------------|
| 0.01-0.05 | Small effect | Predictor explains 1-5% of variance |
| 0.06-0.13 | Medium effect | Predictor explains 6-13% of variance |
| 0.14+ | Large effect | Predictor explains 14%+ of variance |

### Our Results

From our two-way ANOVA (Model × Constitution → Overall Score):

| Effect | η² | Size | Variance Explained |
|--------|-----|------|-------------------|
| **Model main effect** | 0.484 | Large | 48.4% |
| **Constitution main effect** | 0.090 | Medium | 9.0% |
| **Model × Constitution interaction** | 0.042 | Small | 4.2% |

### What This Means

**Model main effect (η² = 0.484):**
- Which model you use explains 48.4% of score variance
- **This is huge!** Model choice matters a lot
- Example: Gemini (96.7 average) vs. Claude (87.3 average) = 9.4 point gap

**Constitution main effect (η² = 0.090):**
- Which constitution you use explains 9.0% of variance
- Medium effect - constitution matters, but less than model
- Example: Harm-min (92 average) vs. Self-sovereignty (87 average) = 5 point gap

**Model × Constitution interaction (η² = 0.042):**
- The interaction explains only 4.2% of variance
- Small effect, but statistically significant (p = 0.022)
- **Interpretation:** The interaction is real but modest

### The Complete Picture

**Total variance breakdown:**
- 48.4% from model (which model is better overall)
- 9.0% from constitution (which constitution is harder)
- 4.2% from interaction (model-constitution specific combinations)
- **38.4% from other factors** (random variation, scenario difficulty, etc.)

**Key insight:** Model choice is the dominant factor (48%), but constitution and interaction also matter (13% combined).

### Real-World Analogy: Coffee and Test Performance

Imagine studying factors affecting test scores:

**Large effect (η² = 0.40):**
- How much you studied explains 40% of score variance
- **This matters a lot** - studying is the main factor

**Medium effect (η² = 0.10):**
- How much sleep you got explains 10% of variance
- **This matters** - sleep is important but secondary

**Small effect (η² = 0.04):**
- Whether you drank coffee explains 4% of variance
- **This matters a little** - coffee has a real effect, but it's small compared to studying and sleep

All three effects can be statistically significant (p < 0.05), but their practical importance differs wildly.

### Why This Matters

**For our research:**
- Confirms model selection is the most important factor
- Constitution matters (9%), but not as much as model (48%)
- Interaction exists (4.2%) but is modest - not the main story

**General principle:**
- Always report effect sizes alongside p-values
- p-value: "Is it real?"
- Effect size: "Does it matter?"
- You need both to interpret findings correctly

### Common Pitfall

**Scenario:** You have 100,000 data points and find p < 0.001 for some effect.

**Mistake:** "p < 0.001 means this is super important!"

**Reality:** With 100,000 points, even η² = 0.001 (0.1% of variance) can be "significant."

**Check effect size:** If η² = 0.001, the effect is real but trivial - might not matter in practice.

---

## <a name="confidence-intervals"></a>5. Confidence Intervals: The ± Range

### What We Measured

When we calculate a statistic (like r = 0.406), that's our *point estimate* from our specific sample of 360 trials.

**Question:** If we ran the experiment again with different scenarios, would we get the same r value?

**Confidence intervals** tell you the range of plausible values.

### The Statistic: 95% Confidence Interval

A **95% CI** means: "If we repeated this experiment 100 times, 95 of those experiments would produce a result within this range."

**Common notation:**
- r = 0.406, 95% CI [0.367, 0.444]
- ICC = 0.31, 95% CI [0.26, 0.36]

### Our Results

| Statistic | Point Estimate | 95% CI | Interpretation |
|-----------|----------------|--------|----------------|
| **Dimensional correlation** | r = 0.406 | [0.367, 0.444] | Narrow (precise estimate) |
| **Likert ICC** | 0.31 | [0.26, 0.36] | Narrow (precise) |
| **Binary ICC** | 0.10 | [0.05, 0.15] | Narrow (precisely bad) |

### What This Means

**Dimensional correlation (r = 0.406, CI [0.367, 0.444]):**
- Our best estimate: r = 0.406
- We're 95% confident the true value is between 0.367 and 0.444
- Range width: 0.077 (narrow) → precise estimate
- **Both bounds < 0.60 threshold** → confidently below independence threshold ✓

**Likert ICC (0.31, CI [0.26, 0.36]):**
- True ICC is very likely between 0.26 and 0.36
- All values in this range are "fair agreement"
- Confidence: Our rubric comparison conclusion is robust

**Binary ICC (0.10, CI [0.05, 0.15]):**
- Even the upper bound (0.15) is still "poor agreement"
- We're confident binary rubric is genuinely bad, not just unlucky sampling

### Visual Interpretation

Imagine plotting confidence intervals as error bars:

```
Binary:    |----●----|           ICC = 0.10, CI [0.05, 0.15]
           Poor ↓

Ternary:        |----●----|      ICC = 0.19, CI [0.14, 0.24]
                Poor ↓

Likert:              |----●----|  ICC = 0.31, CI [0.26, 0.36]
                     Fair ↓

           0.0   0.1   0.2   0.3   0.4   0.5
```

**Key insight:** Even with uncertainty, Likert clearly beats Binary/Ternary.

### Real-World Analogy: Poll Margins

Election poll: "Candidate A leads with 52% support, margin of error ±3%"

**Translation:**
- Point estimate: 52%
- 95% CI: [49%, 55%]
- If election were held 100 times, 95 times support would fall in 49-55% range

**Implications:**
- If opponent has 48%, race is too close to call (CIs overlap)
- If opponent has 45%, candidate A is likely ahead (CIs don't overlap)

Same logic applies to our statistics - CIs tell you how confident to be in the point estimate.

### Why Wide CIs are Bad

**Scenario:** r = 0.50, but 95% CI is [0.10, 0.90]

**Problem:**
- Point estimate says "moderate correlation"
- But CI spans "weak" to "very strong"
- **Translation:** We have no idea what the true value is!

**Our results:** All CIs are narrow (width < 0.10), so our estimates are precise.

### Sample Size and CIs

**Small sample (n = 30):**
- CIs are wide (lots of uncertainty)
- Example: r = 0.50, CI [0.15, 0.75] (not useful)

**Large sample (n = 360, our study):**
- CIs are narrow (little uncertainty)
- Example: r = 0.41, CI [0.37, 0.44] (precise)

**Lesson:** Larger samples give more precise estimates (narrower CIs).

### Why This Matters

**For our research:**
- Narrow CIs confirm our findings are precise, not fluky
- Dimensional independence threshold test (r < 0.60) is robust - even upper bound of CI is 0.444
- Rubric comparison is decisive - even with uncertainty, Likert clearly wins

**General principle:**
- Always report CIs, not just point estimates
- Check CI width - narrow means precise, wide means uncertain
- If CIs overlap between conditions, you can't confidently say they differ

---

## <a name="two-way-anova"></a>6. Two-Way ANOVA: Testing Interactions

### What We Measured

We wanted to know: Do models respond differently to different constitutions?

**Three possible findings:**
1. **Main effect only (no interaction):** Some models are just better, regardless of constitution
2. **Interaction:** Model performance depends on which constitution is used

**Example of interaction:**
- Claude scores 87 with self-sovereignty, 89 with harm-min (2-point gap)
- GPT-4o scores 91 with both (no gap)
- **Interaction exists:** The effect of constitution differs by model

### The Statistic: Two-Way ANOVA

**ANOVA (Analysis of Variance)** tests whether group means differ significantly.

**Two-way** means we're testing two factors simultaneously:
- Factor 1: Model (5 levels: Claude, GPT, Gemini, Grok, DeepSeek)
- Factor 2: Constitution (6 levels: harm-min, liberty, utilitarian, deontological, virtue, self-sovereignty)

**ANOVA produces three F-tests:**
1. **Model main effect:** Do models differ overall?
2. **Constitution main effect:** Do constitutions differ overall?
3. **Model × Constitution interaction:** Does the model effect depend on constitution?

### Our Results

| Effect | F-statistic | p-value | η² | Interpretation |
|--------|-------------|---------|-----|----------------|
| **Model** | F(4,330) = 103.7 | p < 0.001 | 0.484 | Large effect - models differ substantially |
| **Constitution** | F(5,330) = 15.4 | p < 0.001 | 0.090 | Medium effect - constitutions matter |
| **Model × Constitution** | F(20,330) = 1.78 | p = 0.022 | 0.042 | Small but significant interaction |

### What This Means

**Model main effect (F = 103.7, p < 0.001, η² = 0.484):**
- **Highly significant and large effect**
- Models differ substantially in overall performance
- Example: Gemini (96.7) >> Claude (87.3), a 9.4-point gap

**Constitution main effect (F = 15.4, p < 0.001, η² = 0.090):**
- **Highly significant, medium effect**
- Constitutions produce different scores
- Example: Harm-min (92) > Self-sovereignty (87), a 5-point gap

**Model × Constitution interaction (F = 1.78, p = 0.022, η² = 0.042):**
- **Statistically significant but small effect**
- The relationship between model and score depends on constitution
- Not just "some models are better" - **which model is best depends on which constitution you use**

### Visual Interpretation: Interaction Plot

**No interaction (parallel lines):**
```
Score
  |     Gemini ●————————●————————● (always best)
  |     GPT    ●————————●————————● (always middle)
  |     Claude ●————————●————————● (always worst)
  |___________
      Self-sov  Harm-min  Liberty
               Constitution
```
Lines are parallel → model rankings don't change across constitutions

**Interaction (non-parallel lines):**
```
Score
  |     Gemini ●————————●————————●
  |     GPT    ●————●————————————●
  |     Claude ●————————————————●
  |___________
      Self-sov  Harm-min  Liberty
               Constitution
```
Lines cross or converge → model rankings change depending on constitution

**Our data:** Lines aren't perfectly parallel (interaction exists), but gaps remain consistent (main effects dominate).

### Real-World Analogy: Fertilizer and Sunlight

You're testing whether fertilizer helps plant growth. But does the effect depend on sunlight?

**No interaction:**
- Fertilizer adds 10cm growth in both sunny and shady conditions
- Effect is additive: More sun = taller, more fertilizer = taller, both = tallest

**Interaction:**
- Fertilizer adds 20cm growth in sunny conditions
- Fertilizer adds 2cm growth in shady conditions
- **Interaction:** Fertilizer's effect depends on sunlight (they work synergistically)

Same logic: Does model performance depend on constitution? Yes (p = 0.022), but effect is small (η² = 0.042).

### Post-Hoc Tests: Which Specific Differences?

ANOVA tells you "some groups differ," but not which specific pairs.

**Tukey HSD (Honestly Significant Difference):** Tests all pairwise comparisons with correction for multiple testing.

**Our findings:**
- All 5 models differ significantly from each other (Gemini > Grok > GPT > DeepSeek > Claude)
- 4 of 6 constitutions form distinct groups
- Self-sovereignty scores significantly lower than harm-min, utilitarian, liberty

### Why This Matters

**For our research:**
- Confirms model × constitution interaction exists (answering research question #3)
- But main effects (model, constitution) are much larger than interaction
- **Practical implication:** Model choice matters most (48% variance), constitution second (9%), interaction third (4%)

**General principle:**
- ANOVA is the standard way to test multiple groups
- Always check effect sizes (η²), not just p-values
- Interactions mean "one size doesn't fit all" - need tailored approaches

---

## <a name="pca"></a>7. Principal Component Analysis (PCA): Dimensional Structure

### What We Measured

We designed a 2D rubric (Epistemic Integrity + Value Transparency). But do these dimensions actually capture distinct aspects, or are we just measuring the same thing twice?

**PCA (Principal Component Analysis)** is a technique that:
1. Finds the "true" underlying dimensions in your data
2. Tells you how much variance each dimension explains
3. Reveals whether your designed dimensions align with the data structure

### The Statistic: Variance Explained

**PCA output:**
- **Principal Components (PCs):** New axes that explain maximum variance
- **Variance explained:** What % of total variance does each PC capture?
- **Loadings:** How much does each original variable contribute to each PC?

**For 2D rubric:**
- If 2 PCs explain 100% of variance → 2D structure is perfect
- If 1 PC explains 95% → really just 1D (dimensions are redundant)
- If need 3+ PCs → dimensions don't capture full structure

### Our Results

| Component | Variance Explained | Cumulative | Interpretation |
|-----------|-------------------|------------|----------------|
| **PC1** | 58.4% | 58.4% | General quality factor |
| **PC2** | 41.6% | 100.0% | Dimension separation |

**Loadings:**
```
                         PC1      PC2
Epistemic Integrity     +0.707   -0.707
Value Transparency      +0.707   +0.707
```

### What This Means

**2 PCs explain 100% of variance:**
- Perfect! Our 2D rubric captures all the structure in the data
- No hidden third dimension we're missing

**PC1 (58.4% variance) - "General Quality":**
- Both dimensions load positively (+0.707 each)
- Interpretation: "Overall response quality"
- Responses high on PC1 score high on both dimensions
- This is the "halo effect" component

**PC2 (41.6% variance) - "Dimension Separation":**
- Epistemic loads negatively (-0.707), Value loads positively (+0.707)
- Interpretation: "Tradeoff between fact-focus and value-focus"
- Responses high on PC2: Value-explicit but fact-light
- Responses low on PC2: Fact-heavy but value-opaque

**Equal loadings (±0.707):**
- Both dimensions contribute equally to both PCs
- Confirms dimensions are balanced (neither dominates)

### Visual Interpretation: PCA Biplot

```
        Value Transparency
              ↑
              |
         ●    |    ●
       ●   ●  |  ●   ●
     ●     ● ●|● ●     ●
   ←—————————●|●—————————→ Epistemic Integrity
     ●     ● ●|● ●     ●
       ●   ●  |  ●   ●
         ●    |    ●
              |
```

**PC1 (diagonal, lower-left to upper-right):**
- Separates low-quality (bottom-left) from high-quality (top-right)

**PC2 (diagonal, upper-left to lower-right):**
- Separates value-explicit (top-left) from fact-explicit (bottom-right)

### Real-World Analogy: Restaurant Reviews

You rate restaurants on two scales: Food Quality and Service Quality.

**PCA Result 1: 1 PC explains 95%**
- Food and service are almost perfectly correlated
- Really just measuring "overall restaurant quality"
- Might as well use 1D rating

**PCA Result 2: 2 PCs explain 100% (our result)**
- PC1: Overall quality (good restaurants have both)
- PC2: Type of restaurant (some focus on food, others on service)
- Both dimensions provide unique information

**PCA Result 3: Need 3 PCs**
- Something else matters (ambiance? price?)
- Your 2D rating system is incomplete

### Why This Matters

**For our research:**
- Validates our 2D rubric design empirically
- 2 PCs with 100% variance → no missing dimensions
- Equal loadings → dimensions are balanced, not redundant

**Confirms Pearson r finding:**
- r = 0.406 showed dimensions are correlated but distinct
- PCA shows the same: PC1 (shared variance), PC2 (unique variance)
- Two complementary ways of saying: "2D rubric is justified"

**Identifies response types:**
- High PC1, High PC2: Value-explicit, good quality
- High PC1, Low PC2: Fact-focused, good quality
- Low PC1, High PC2: Value-explicit, poor quality (motivated reasoning?)
- Low PC1, Low PC2: Fact-distorted, value-opaque (worst case)

### General Principle

**Use PCA to validate rubric structure:**
- Design 2D rubric → Run PCA → Check if 2 PCs explain most variance
- If yes: Rubric design is good
- If no: Redesign rubric or accept you're measuring fewer/more dimensions

---

## <a name="quick-reference"></a>8. Quick Reference Table

| Statistic | What It Measures | Our Result | Interpretation |
|-----------|------------------|------------|----------------|
| **ICC** | Inter-rater reliability | Likert: 0.31<br>Binary: 0.10 | Fair vs. Poor agreement<br>Likert 3× better |
| **p-value** | Statistical significance | 0.022 | 97.8% confident interaction is real |
| **Pearson r** | Correlation | 0.406 | Moderate correlation<br>Dimensions independent enough |
| **η² (eta squared)** | Effect size | Model: 0.484<br>Constitution: 0.090<br>Interaction: 0.042 | Large effect (model)<br>Medium effect (constitution)<br>Small effect (interaction) |
| **95% CI** | Estimate precision | r: [0.367, 0.444]<br>ICC: [0.26, 0.36] | Narrow CIs = precise estimates |
| **F-statistic** | Group differences | Model: 103.7<br>Constitution: 15.4<br>Interaction: 1.78 | All significant (p < 0.05) |
| **PCA variance** | Dimensional structure | PC1: 58.4%<br>PC2: 41.6% | 2D rubric validated (100% variance) |

---

## Key Takeaways

### 1. Always Pair p-values with Effect Sizes
- **p-value:** Tells you if an effect is real
- **Effect size:** Tells you if it matters
- You need both!

### 2. Confidence Intervals Beat Point Estimates
- Don't just say "r = 0.406"
- Say "r = 0.406, 95% CI [0.367, 0.444]"
- Shows how confident you should be

### 3. Sample Size Matters
- Small samples → wide CIs, low power
- Large samples → narrow CIs, high power
- Our n = 360 (trials) × 5 (evaluators) = 1,800 data points → good power

### 4. Check Assumptions
- ANOVA assumes normal distribution and equal variance (we checked ✓)
- Pearson r assumes linear relationship (we checked ✓)
- ICC assumes random sampling (we checked ✓)

### 5. Multiple Comparisons Require Correction
- Testing many hypotheses increases false positive risk
- Use Bonferroni or Tukey HSD corrections
- We did this for post-hoc tests ✓

---

## Further Learning

### If You Want to Dive Deeper:

**Books:**
- *Statistics for People Who (Think They) Hate Statistics* by Salkind (very accessible)
- *The Art of Statistics* by Spiegelhalter (conceptual, minimal math)
- *An Introduction to Statistical Learning* by James et al. (free online, more advanced)

**Online Resources:**
- Khan Academy Statistics course (free, interactive)
- StatQuest YouTube channel (Josh Starmer - amazing visual explanations)
- Coursera: "Statistics with R" or "Statistics with Python"

**Practice:**
- Work through our analysis notebooks (`notebooks/01_rubric_comparison.ipynb`, etc.)
- Re-run analyses with different parameters
- Try analyzing your own data

---

## Conclusion

Statistics can seem intimidating at first, but the core concepts are intuitive:

- **ICC:** Do evaluators agree?
- **p-value:** Is the effect real or just noise?
- **Pearson r:** Do two things move together?
- **η²:** How much does it matter?
- **CI:** How confident should we be?
- **ANOVA:** Do groups differ?
- **PCA:** What's the underlying structure?

These are just tools for quantifying common-sense questions. Once you understand what each measures, interpreting research becomes much easier.

**Most important lesson:** Always ask "What is this statistic telling me?" before diving into the numbers. Context matters more than formulas.

---

**Document Status:** Living guide - will update as we add new analyses

**Last Updated:** 2025-11-03

**Questions or Suggestions?** This guide is meant to be useful. If anything is unclear or you'd like additional explanations, let me know!
