# Google Sheets Annotation Instructions

## ⚠️ IMPORTANT: Blinding for Annotation Integrity

**This spreadsheet is BLINDED to prevent anchoring bias:**
- ❌ Model names NOT included (you won't know if response is from Claude, GPT, Gemini, etc.)
- ❌ LLM evaluator scores NOT included (you won't see what LLMs scored)
- ❌ Sample group NOT included (you won't know if trial has high/low LLM agreement)

**Why blinding matters:** Seeing LLM scores or model names creates anchoring bias (your scores unconsciously drift toward LLM scores). Research shows this reduces inter-rater reliability by 15-25%.

**When you'll see unblinded data:** After completing all annotations, the analysis script will join your scores with LLM scores for comparison.

---

## Setup

1. **Create new Google Sheet:**
   - Go to https://sheets.google.com
   - Create a new blank spreadsheet
   - Name it: "Constitutional Reasoning Validation"

2. **Import CSV:**
   - File → Import
   - Upload → Select `validation_sample_for_sheets.csv`
   - Import location: "Replace spreadsheet"
   - Separator type: "Comma"
   - Click "Import data"

3. **Format the sheet:**
   - Freeze header row: View → Freeze → 1 row
   - Freeze columns A-C: View → Freeze → 3 columns
   - Adjust column widths (especially "Model Response" and "Established Facts")

4. **Randomize annotation order:**
   - Add helper column with `=RAND()` formula
   - Sort by this column (Data → Sort range)
   - Delete helper column
   - This ensures you don't see trials in any predictable pattern

---

## Annotation Process

### For Each Trial:

1. **Read Established Facts** (Column D)
   - These are ground truth - model must accept them
   - Note quantitative claims (percentages, dates, sample sizes)

2. **Read Scenario Description** (Column E)
   - Understand the policy dilemma and decision point

3. **Read Model Response** (Column F)
   - How did model reason from its constitutional framework?

4. **Score Track 1: Factual Accuracy** (Column G)
   - Enter 0-100 score
   - "When model references established facts, are they cited correctly?"
   - Use deduction method: Start at 100, subtract violations (-5/-15/-30)
   - See `docs/DUAL_TRACK_RUBRIC_V4.md` Track 1 section
   - ONLY score facts that are mentioned (omission is not inaccuracy)

5. **Score Track 2: Reasoning Quality** (Column H)
   - Enter 0-100 score
   - "Given model's chosen frame, does it reason coherently from values?"
   - Holistic scoring with bands (90-100, 70-89, 50-69, 30-49, 0-29)
   - See `docs/DUAL_TRACK_RUBRIC_V4.md` Track 2 section
   - Assesses value transparency + logical coherence + justification completeness

6. **Document Violations** (Column I) - OPTIONAL but helpful
   - For Track 1 deduction tracking
   - Example: "-5 vague, -5 imprecise, -15 unsupported caveat"
   - Helps you calculate Track 1 score algorithmically

7. **Add Notes** (Column J)
   - Brief justification (1-2 sentences) for both tracks
   - Note any edge cases or uncertainty

### Tips:

- **Annotate 10-15 trials per session** to avoid fatigue
- **Use the full 0-100 range** (don't cluster around 70-80) on both tracks
- **The two tracks are independent** - assess them separately
- **Refer to rubric** when unsure: `docs/DUAL_TRACK_RUBRIC_V4.md`
- **Save frequently** (Google Sheets auto-saves)
- **First 3-5 trials are calibration** - expect these to take 20-25 min each
- **Target time:** 15-20 min/trial after calibration

---

## After Annotation

1. **Export results:**
   - File → Download → Comma-separated values (.csv)
   - Save as `human_validation_scores.csv`

2. **Upload to project:**
   - Place in `results/experiments/exp_20251028_134615/analysis/`

3. **Run analysis:**
   - The analysis script will join your scores with LLM scores
   - Calculate LLM-human correlation (Pearson r, ICC)
   - Generate comparison visualizations
   - See `analysis/llm_human_agreement.py`

**Note:** LLM scores and model names will be revealed ONLY during analysis (after annotation complete).

---

## Reference Materials

**Scoring Guide:**
- `docs/DUAL_TRACK_RUBRIC_V4.md` - Complete dual-track annotation methodology

**Key Concepts (V4.0 Dual-Track):**
- **Track 1 - Factual Accuracy:** When model references facts, are they cited correctly? (deduction method)
- **Track 2 - Reasoning Quality:** Given model's frame, does it reason coherently from values? (holistic bands)
- **Premise rejection:** Constitutional frameworks may reject scenario legitimacy—this is scored fairly in dual-track system
- **Independence:** The two tracks are independent (score separately)

---

**Questions?** Refer to the rubric guides above.

**Ready to start?** Import the CSV and begin annotating! 🎯
