# API Documentation Contracts

**Documentation drift can start with one changed default.**

I separated documentation generation from a narrower CI decision: does the documented declared interface still match the source? A file or function name can remain unchanged while a required argument, keyword-only constraint, annotation or async contract changes. My framework is **parse without execution → resolve explicit exports → compare typed signatures → flag drift or require review**.

The implementation uses Python ASTs over original source fixtures. A symbol-only baseline shares the same export boundary so the comparison isolates signature checking. [The report](results/report.md) keeps every authored mutation and its outcome. Dynamic exports and decorators produce a manual-review result; this tool does not invent runtime certainty.


## Recorded result

Signature-aware checking meets **14/14 authored contracts**, versus **7/14** for symbol-only checking. **2** cases require review. Fixture modules executed: **0**. Extra boundary tests cover conditional export mutation and function-local export names. These pass counts do not measure documentation prose quality.

## Reproduce and inspect

Python 3.11, CPU only. No API keys, paid services, provider calls, customer records or external data download.

```bash
python -m venv .venv
# Activate the environment for your shell.
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python run.py --output runs/local
```

`core.py` contains the generator and actual comparison. `data/dataset.json` is the committed original input. `results/decisions.json` preserves the evaluated rows/traces. `results/metrics.json` and `results/report.md` state the measured outcomes. `results/manifest.json` binds core source, input, and output bytes with SHA-256. A fresh run writes to the requested directory and leaves committed results available for comparison.

This is a new independent portfolio experiment. Its results do not establish historical employer/client outcomes, production adoption, or service scale. Read the [data card](docs/data-card.md) and [provenance](docs/provenance.md) before interpreting the numbers.
