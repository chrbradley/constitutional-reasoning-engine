# Constitutional Reasoning Engine - Project Overview

## Mission

Build an AI system that demonstrates how different value systems reason from the same facts to different conclusions—and detect when value systems require distorting facts (motivated reasoning).

## The Core Problem

As we give users more control over AI behavior through constitutional AI, we risk creating echo chambers that confirm biases. But we can't force everyone to use the same value system. We need a framework for **value pluralism** that preserves **epistemic integrity**.

The key question: Can AI systems hold different values while maintaining intellectual honesty?

## Key Innovation: Three-Layer Architecture

This project separates reasoning into three distinct layers:

1. **Fact Establishment** (Objective baseline)
   - Uses GPT-4o to establish agreed-upon facts from scenarios
   - Identifies what is certain vs. what is ambiguous
   - Creates a shared epistemic foundation

2. **Constitutional Reasoning** (Values applied to facts)
   - Tests 6 frontier models across 5 constitutional frameworks
   - Models apply their assigned values to the established facts
   - Reasoning is explicit about tradeoffs and value priorities

3. **Integrity Evaluation** (Detecting fact-distortion)
   - Uses Claude Sonnet 4.5 to score responses on:
     - **Factual Adherence**: Did it accept facts without distortion?
     - **Value Transparency**: Did it explicitly state its values and tradeoffs?
     - **Logical Coherence**: Does the conclusion follow from the values?

This architecture tests whether value systems can maintain intellectual honesty or require motivated reasoning.

## Portfolio Objectives

This project demonstrates:

1. **AI alignment understanding** - Grappling with value pluralism vs. epistemic integrity
2. **Rigorous experimental design** - Systematic testing across 480 combinations
3. **Technical breadth** - Python backend, multi-model integration, data analysis, visualization
4. **Problem-solving depth** - JSON parsing fallbacks, truncation detection, rate limit management
5. **Clear communication** - Turning complex findings into compelling presentations

**Target audience:** AI safety companies (Anthropic, OpenAI, etc.)

## Current Status

**✅ Completed:**
- Full 480-test experiment (16 scenarios × 5 constitutions × 6 models)
- 100% success rate with zero data loss
- 8 publication-ready visualizations
- Complete statistical analysis
- Robust infrastructure (graceful parsing, truncation handling, state management)

**In Progress:**
- Findings documentation and analysis writeup

**Planned:**
- Interactive web viewer for exploring results
- Demo video showcasing key findings
- Technical writeup for publication

## Experiment Scale

**Models Tested:**
- Claude Sonnet 4.5 (Anthropic)
- GPT-4o (OpenAI)
- Gemini 2.0 Flash (Google)
- Grok 3 (xAI)
- Llama 3.3 70B (Meta/Replicate)
- DeepSeek Chat (DeepSeek)

**Constitutional Frameworks:**
1. **Harm Minimization** - Pacifist approach prioritizing non-violence
2. **Balanced Justice** - Pragmatic approach seeking proportional responses
3. **Self-Sovereignty** - Libertarian approach prioritizing autonomy
4. **Community Order** - Communitarian approach prioritizing social stability
5. **Bad-Faith Control** - Designed to demonstrate motivated reasoning

**Scenarios:** 16 ethical dilemmas spanning personal, community, and societal scales

**Total Tests:** 480 (16 × 5 × 6) completed in ~11 hours on October 23, 2025

## Why This Matters

**For AI Safety:**
If we can't build systems that hold different values without distorting facts, constitutional AI fails. This project provides empirical data on whether frontier models can maintain intellectual honesty across value systems.

**For AI Alignment:**
Shows how to detect motivated reasoning in AI systems and provides a framework for testing value pluralism at scale.

**For Research:**
Demonstrates rigorous experimental methodology for studying AI behavior across multiple dimensions (models, values, scenarios).

## Documentation Structure

- **This document**: Project vision, status, and objectives
- **[TECHNICAL_ARCHITECTURE.md](TECHNICAL_ARCHITECTURE.md)**: Implementation details, tech stack, system design
- **[METHODOLOGY.md](METHODOLOGY.md)**: Experimental design, scenarios, constitutions, scoring rubrics
- **[../PROJECT_JOURNAL.md](../PROJECT_JOURNAL.md)**: Development changelog with decisions and solutions
- **[FINDINGS.md](FINDINGS.md)**: Experimental results and key discoveries

## Quick Start

```bash
# Install dependencies
poetry install

# Set up API keys
cp .env.example .env
# Edit .env with your keys

# Run experiment
poetry run python src/runner.py

# Generate analysis
poetry run python analysis/analyze.py --experiment exp_20251023_105245
```

See [README.md](../README.md) for detailed setup instructions.
