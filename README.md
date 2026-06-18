# Quant Research Paper Rebuilder Agent

A LangGraph-based research workflow that helps turn a quantitative finance idea into a reproducible GitHub-style Jupyter Notebook.

The workflow:

1. Clarifies the user's research scope with a Business Analyst agent.
2. Searches and ranks relevant arXiv quantitative finance papers.
3. Downloads and reads the selected paper PDF.
4. Extracts the methodology and rebuild plan.
5. Generates a Jupyter-style Python notebook.
6. Reviews the notebook as a strict quant researcher.
7. Revises the notebook until it passes or reaches the revision limit.

> This project is for research and education only. It is not financial advice.

## Project structure

```text
quant_research_paper_rebuilder/
├── quant_research_agent/
│   ├── agents.py           # BA, paper selector, paper reader, notebook writer, reviewer nodes
│   ├── graph.py            # LangGraph notebook workflow
│   ├── llm.py              # LLM client setup
│   ├── main.py             # CLI entrypoint
│   ├── monitor.py          # streaming node logs
│   ├── notebook_writer.py  # Jupyter code -> .ipynb conversion
│   ├── prompts.py          # agent prompts
│   ├── state.py            # TypedDict workflow state
│   └── tools.py            # arXiv/PDF/data-source utilities
├── tests/
├── .env.example
├── .gitignore
├── pyproject.toml
└── requirements.txt
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:

```bash
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

## Run

Interactive mode is best for demos because it shows the BA clarification and paper-selection flow.

```bash
python -m quant_research_agent \
  --query "Monthly investing in a US index ETF; compare DCA versus lump-sum under different market regimes" \
  --interactive
```

Non-interactive paper filtering:

```bash
python -m quant_research_agent \
  --query "Crypto momentum strategy using daily data"
```

After paper filtering, re-run with the selected paper ID:

```bash
python -m quant_research_agent \
  --query "Crypto momentum strategy using daily data" \
  --selected-paper-id arxiv_1
```

Outputs are saved under:

```text
outputs/
notebooks/output/
papers/pdf/
data/papers/
```

## What makes this GitHub-ready

- Clean package filenames and import paths.
- No hard-coded local desktop paths.
- `.env.example` instead of committed API keys.
- `.gitignore` excludes generated PDFs, notebooks, local data, cache files, and secrets.
- CLI can run as `python -m quant_research_agent`.
- The graph stops safely when paper reading or notebook writing fails.
- Reviewer output has a stable JSON structure.
- Basic test included for notebook conversion.

## Limitations

- arXiv search quality depends on the generated query terms.
- Exact paper reproduction may require paid or manually downloaded data.
- The generated notebook should still be reviewed by a human before being presented as serious research.
- The fallback seed papers are only for keeping the demo runnable when online search fails.

## Suggested GitHub repo description

> LangGraph multi-agent workflow that searches quant finance papers, reads selected PDFs, generates reproducible research notebooks, and self-reviews them with a quant-researcher agent.

## Suggested README demo section

Add screenshots or GIFs showing:

1. Scope clarification.
2. Paper ranking output.
3. Streaming graph logs.
4. Generated notebook sections.
5. Reviewer feedback and revision loop.

## License

MIT License. See `LICENSE`.
