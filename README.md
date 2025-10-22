# Constitutional Reasoning Engine

An AI system that tests how different value frameworks maintain factual integrity when reasoning from identical facts to different conclusions.

## Overview

This project demonstrates how AI systems can maintain epistemic integrity while reasoning from different constitutional frameworks. It tests 6 frontier models across 5 different value systems using 10 everyday ethical dilemmas.

## Project Structure

```
constitutional-reasoning-engine/
├── experiments/                 # Python backend
│   ├── src/
│   │   ├── types.py            # Data models and type definitions
│   │   ├── models.py           # LLM API wrappers via LiteLLM
│   │   ├── constitutions.py    # Constitutional frameworks
│   │   └── ...                 # (more modules to be added)
│   ├── data/                   # Scenario definitions
│   └── notebooks/              # Analysis notebooks
├── results/                    # Generated outputs
│   ├── raw/                   # Full test results
│   ├── processed/             # Aggregated data
│   └── charts/                # Generated visualizations
├── pyproject.toml             # Poetry dependencies
└── test_connectivity.py       # API connectivity test
```

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
poetry run python test_connectivity.py
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

## Development Status

- [x] Project structure setup
- [x] Core type definitions
- [x] LLM API integration via LiteLLM
- [x] Constitutional frameworks
- [x] API connectivity testing
- [ ] Scenario loading system
- [ ] Prompt templates
- [ ] Integrity evaluation system
- [ ] Main experiment runner
- [ ] Data analysis tools
- [ ] Web viewer (Next.js)

## Next Steps

1. Add scenario definitions and loading system
2. Create prompt templates for fact establishment and constitutional reasoning  
3. Implement integrity evaluation system
4. Build main experiment runner
5. Run initial test with subset of scenarios

## Contributing

This is a research project demonstrating AI safety concepts. Contributions welcome via issues and pull requests.

## License

MIT License - see LICENSE file for details.