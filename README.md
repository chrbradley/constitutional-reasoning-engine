# Constitutional Reasoning Engine

An AI system that tests how different value frameworks maintain factual integrity when reasoning from identical facts to different conclusions.

## Overview

This project demonstrates how AI systems can maintain epistemic integrity while reasoning from different constitutional frameworks. It tests 6 frontier models across 5 different value systems using 10 everyday ethical dilemmas.

## Project Structure

```
constitutional-reasoning-engine/
├── src/                        # Core experiment engine - runs experiments
│   ├── core/                   # Core modules (imported as src.core.*)
│   │   ├── data_types.py       # Pydantic models for Scenario, Constitution, etc.
│   │   ├── models.py           # LLM API wrappers via LiteLLM (all 6 models)
│   │   ├── constitutions.py    # 5 constitutional frameworks definitions
│   │   ├── scenarios.py        # Scenario loading from JSON
│   │   ├── prompts.py          # 3-layer prompt templates (facts/reasoning/integrity)
│   │   ├── experiment_state.py # State management, checkpointing, resumption
│   │   ├── graceful_parser.py  # Robust JSON parsing with fallback strategies
│   │   ├── truncation_detector.py # Detects truncated responses, retries with higher limits
│   │   └── manifest_generator.py  # Generates human-readable experiment manifests
│   ├── data/                   # Input data for experiments
│   │   ├── scenarios.json      # 16 ethical scenarios (personal/community/societal)
│   │   ├── scenarios_16.json   # Alternative 16-scenario set
│   │   └── SCENARIOS.md        # Scenario documentation
│   ├── runner.py               # Main experiment runner (batch processing, rate limiting)
│   └── inspector.py            # Experiment state inspector (progress tracking)
│
├── analysis/                   # Post-experiment analysis tools
│   ├── analyze.py              # Statistical analysis (aggregation, variance, distributions)
│   ├── visualize.py            # Chart generation (matplotlib/seaborn)
│   └── export.py               # Web-friendly JSON export for viewers
│
├── results/                    # Generated experiment data (gitignored)
│   ├── experiments/            # Individual experiment runs (self-contained)
│   │   └── exp_YYYYMMDD_HHMMSS/  # Each experiment is a complete package
│   │       ├── data/
│   │       │   ├── tests/      # 480 test result JSONs (one per test)
│   │       │   └── debug/      # Manual review logs for parsing edge cases
│   │       ├── analysis/       # Experiment-specific analysis outputs
│   │       │   └── statistics.json
│   │       ├── visualizations/ # Experiment-specific charts (PNGs)
│   │       ├── exports/        # Web-friendly exports
│   │       └── metadata.json   # Experiment configuration and summary
│   ├── aggregate/              # Cross-experiment aggregated data
│   │   ├── analysis/           # Multi-experiment statistics
│   │   ├── visualizations/     # Comparative charts
│   │   └── exports/            # Combined exports
│   └── state/                  # Active experiment state (for resumption)
│       ├── experiment_state.json  # Current experiment metadata
│       └── test_registry.json     # Test status tracking (pending/completed/failed)
│
├── tests/                      # Test and debug scripts
│   ├── unit/                   # Unit tests for individual components
│   ├── integration/            # Integration tests (batching, state management)
│   ├── model_tests/            # Model connectivity and API tests
│   └── debug/                  # Debug scripts for troubleshooting
│
├── notebooks/                  # Jupyter notebooks for exploratory analysis
│   ├── 01_exploratory_analysis.ipynb
│   └── 02_statistical_analysis.ipynb
│
├── docs/                       # Project documentation
│   ├── PROJECT_OVERVIEW.md     # Project vision, mission, and status
│   ├── TECHNICAL_ARCHITECTURE.md # Implementation details and infrastructure
│   └── METHODOLOGY.md          # Experimental design and evaluation
│
├── pyproject.toml              # Poetry dependencies and project metadata
├── PROJECT_JOURNAL.md          # Development changelog with decisions and solutions
├── FINDINGS.md                 # Experimental results (coming soon)
├── .env                        # API keys (gitignored, use .env.example as template)
└── README.md                   # This file
```

### Directory Design Philosophy

**Separation of Concerns:**
- `src/` = Code that **runs** experiments (produces data)
- `analysis/` = Code that **analyzes** experiment results (processes data)
- `results/` = Generated data (organized by experiment)
- `tests/` = Validation and debugging code

**Self-Contained Experiments:**
Each experiment in `results/experiments/exp_*/` contains everything related to that run:
- Raw test data
- Analysis outputs
- Visualizations
- Exports
- Metadata

This makes experiments portable, archivable, and easy to compare.

## Setup Instructions

### 1. Install Poetry (if not already installed)
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### 2. Install Dependencies
```bash
poetry install
```

### 3. Set up API Keys
```bash
cp .env.example .env
# Edit .env and add your API keys
```

Required API keys:
- `ANTHROPIC_API_KEY` - For Claude models
- `OPENAI_API_KEY` - For GPT models  
- `GOOGLE_API_KEY` - For Gemini models
- `XAI_API_KEY` - For Grok models
- `REPLICATE_API_TOKEN` - For Llama models
- `DEEPSEEK_API_KEY` - For DeepSeek models

### 4. Test API Connectivity
```bash
poetry run python tests/model_tests/test_connectivity.py
```

## Constitutional Frameworks

The system tests 5 different value frameworks:

1. **Harm Minimization** - Pacifist approach prioritizing non-violence
2. **Balanced Justice** - Pragmatic approach seeking proportional responses
3. **Self-Sovereignty** - Libertarian approach prioritizing individual autonomy
4. **Community Order** - Communitarian approach prioritizing social stability
5. **Bad-Faith** - Control framework designed to demonstrate motivated reasoning

## Models Tested

- Claude Sonnet 4.5 (Anthropic)
- GPT-4o (OpenAI)
- Gemini 2.0 Pro (Google)
- Grok 2 (xAI)
- Llama 3.2 3B (Meta/Replicate)
- DeepSeek V3 (DeepSeek)

## Documentation

For comprehensive information about the project:

- **[docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md)** - Project vision, mission, current status, and objectives
- **[docs/TECHNICAL_ARCHITECTURE.md](docs/TECHNICAL_ARCHITECTURE.md)** - Technical implementation, architecture, and infrastructure
- **[docs/METHODOLOGY.md](docs/METHODOLOGY.md)** - Experimental design, scenarios, constitutions, and evaluation rubrics
- **[PROJECT_JOURNAL.md](PROJECT_JOURNAL.md)** - Development changelog with decisions and solutions
- **[docs/FINDINGS.md](docs/FINDINGS.md)** - Experimental results and key discoveries (coming soon)

## Development Status

- [x] Project structure setup
- [x] Core type definitions
- [x] LLM API integration via LiteLLM
- [x] Constitutional frameworks (5 value systems)
- [x] API connectivity testing
- [x] Scenario loading system (16 scenarios)
- [x] Prompt templates (3-layer architecture)
- [x] Integrity evaluation system
- [x] Main experiment runner with state management
- [x] Graceful JSON parsing with zero data loss
- [x] Response truncation detection and retry
- [x] Batch processing with rate limit management
- [x] Data analysis tools (statistics, visualizations, exports)
- [x] Jupyter notebooks for exploratory analysis
- [x] **Full experiment completed: 480/480 tests (100% success rate)**

## Running Experiments

### Run the full experiment:
```bash
poetry run python -m src.runner
```

### Check experiment status:
```bash
poetry run python -m src.inspector
```

### Generate analysis:
```bash
poetry run python -m analysis.analyze --experiment exp_20251023_105245
poetry run python -m analysis.visualize --experiment exp_20251023_105245
poetry run python -m analysis.export --experiment exp_20251023_105245
```

## Experiment Results

**Completed Experiment:** `exp_20251023_105245`
- **480 tests** (16 scenarios × 5 constitutions × 6 models)
- **100% success rate** (no permanent failures)
- **Duration:** ~11 hours (2025-10-23 10:52 - 22:02)
- **8 publication-ready visualizations** generated
- **Complete statistical analysis** available

## Next Steps

1. ~~Add web viewer for interactive exploration~~ (future enhancement)
2. Run additional experiments with new scenarios
3. Test additional frontier models as they become available
4. Publish findings and methodology

## Contributing

This is a research project demonstrating AI safety concepts. Contributions welcome via issues and pull requests.

## License

MIT License - see LICENSE file for details.