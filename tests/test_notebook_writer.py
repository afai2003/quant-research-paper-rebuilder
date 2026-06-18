from pathlib import Path

import nbformat

from quant_research_agent.notebook_writer import jupyter_code_to_notebook


def test_jupyter_code_to_notebook(tmp_path: Path):
    code = """# %% [markdown]
# # Demo Notebook
# This is a markdown cell.

# %%
x = 1 + 1
print(x)
"""
    output_path = tmp_path / "demo.ipynb"
    saved_path = jupyter_code_to_notebook(code, str(output_path))

    nb = nbformat.read(saved_path, as_version=4)
    assert len(nb.cells) == 2
    assert nb.cells[0].cell_type == "markdown"
    assert nb.cells[1].cell_type == "code"
    assert "x = 1 + 1" in nb.cells[1].source
