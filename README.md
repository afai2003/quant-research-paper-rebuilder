# Quant Research Paper Rebuilder Agent

A LangGraph-based research workflow that helps turn a quantitative finance idea into a reproducible GitHub-style Jupyter Notebook.

The workflow reads quantitative finance papers, builds a paper knowledge graph, analyzes the methodology, generates a notebook, and reviews the notebook with a strict quant researcher agent.

> This project is for research and education only. It is not financial advice.

## Workflow

The workflow:

1. Clarifies the user's research scope with a Business Analyst agent.
2. Searches and ranks relevant arXiv quantitative finance papers.
3. Downloads and reads the selected paper PDF.
4. Splits the paper into text chunks.
5. Builds a paper knowledge graph from the chunks.
6. Merges chunk-level graph fragments into one paper-level graph.
7. Creates a graph-based paper analysis and rebuild plan.
8. Generates a Jupyter-style Python notebook.
9. Reviews the notebook as a strict quant researcher.
10. Revises the notebook until it passes or reaches the revision limit.

High-level flow:

```text
research query
    ↓
Business Analyst clarification
    ↓
paper search and selection
    ↓
PDF reading
    ↓
paper knowledge graph construction
    ↓
graph-based paper analysis
    ↓
notebook generation
    ↓
reviewer
    ↓
revise or finish
```

## Project structure

```text
quant_research_paper_rebuilder/
├── quant_research_agent/
│   ├── agents.py              # BA, paper selector, graph builder, analyst, writer, reviewer nodes
│   ├── graph.py               # LangGraph notebook workflow
│   ├── llm.py                 # LLM client setup
│   ├── main.py                # CLI entrypoint
│   ├── monitor.py             # streaming node logs
│   ├── notebook_writer.py     # Jupyter code -> .ipynb conversion
│   ├── paper_kg.py            # paper knowledge graph utilities
│   ├── prompts.py             # agent prompts
│   ├── state.py               # TypedDict workflow state
│   └── tools.py               # arXiv/PDF/data-source utilities
├── tests/
├── .env.example
├── .gitignore
├── pyproject.toml
└── requirements.txt
```

## Key components

### Paper reading

The paper reader extracts text from the selected PDF and stores it in the workflow state.

### Paper knowledge graph

The paper graph builder splits the paper into chunks and extracts structured graph fragments from each chunk.

Each graph fragment may contain:

```text
nodes
edges
implementation steps
missing or unclear details
```

Example relationship:

```text
Random Forest Classifier → USED_FOR → Relative Return Prediction
```

### Graph-based paper analysis

The graph-based analyst turns the paper knowledge graph into a structured rebuild plan.

The analysis includes:

```text
methodology
main results
data needed
features and variables
models and methods
formulas to implement
parameters to match
backtest or experiment design
performance metrics
rebuild steps
notebook plan
limitations
```

### Notebook generation

The notebook writer uses the graph-based paper analysis to generate a reproducible Python notebook.

The generated notebook is intended to include:

```text
research objective
data preparation
feature engineering
model or signal construction
backtest or experiment design
performance evaluation
limitations
```

### Reviewer and revision loop

The reviewer checks whether the generated notebook is close enough to the paper methodology.

If the notebook is incomplete or not faithful enough to the paper, the reviewer requests revisions.

## Setup

Create and activate a virtual environment:

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS / Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create your environment file:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
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

## Outputs

Outputs are saved under:

```text
outputs/
notebooks/output/
papers/pdf/
data/papers/
```

Typical output files include:

```text
paper analysis JSON
paper knowledge graph JSON
generated notebook
reviewer feedback
revised notebook
```

Example output structure:

```text
outputs/
├── paper_read/
│   └── selected_paper_analysis_from_graph.json
├── paper_graph/
│   └── selected_paper_graph.json
└── reviews/
    └── reviewer_feedback.json

notebooks/output/
└── generated_research_notebook.ipynb

papers/pdf/
└── selected_paper.pdf
```

## What makes this GitHub-ready

- Clean package filenames and import paths.
- No hard-coded local desktop paths.
- `.env.example` instead of committed API keys.
- `.gitignore` excludes generated PDFs, notebooks, local data, cache files, and secrets.
- CLI can run as `python -m quant_research_agent`.
- LangGraph workflow has clear node separation.
- The graph stops safely when paper reading, graph building, or notebook writing fails.
- Paper analysis and reviewer output use stable JSON structures.
- Basic test coverage can be added for notebook conversion and graph utilities.

## Limitations

- arXiv search quality depends on the generated query terms.
- Exact paper reproduction may require paid or manually downloaded data.
- The current paper graph builder may limit the number of chunks to avoid excessive LLM calls.
- The current evidence pack may use only a subset of paper chunks.
- Some papers may include important details in appendices, tables, or figures that are difficult to extract from raw text.
- The generated notebook should still be reviewed by a human before being presented as serious research.

## Future improvements

Planned improvements include:

```text
better graph retrieval
edge evidence merging
important chunk selection
formula extraction
table and figure extraction
stronger paper-to-notebook validation
data-source recommendation
notebook execution checking
unit tests for graph utilities
```

## Suggested GitHub repo description

> LangGraph multi-agent workflow that searches quant finance papers, builds paper knowledge graphs, generates reproducible research notebooks, and self-reviews them with a quant-researcher agent.

## Suggested README demo section

Add screenshots or GIFs showing:

1. Scope clarification.
2. Paper ranking output.
3. Streaming LangGraph logs.
4. Paper knowledge graph construction.
5. Graph-based paper analysis JSON.
6. Generated notebook sections.
7. Reviewer feedback and revision loop.

## Disclaimer

This project is for research, education, and workflow experimentation only.

It does not provide investment advice, trading advice, or financial recommendations.

