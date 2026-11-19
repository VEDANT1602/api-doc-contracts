# API Documentation Contracts

A Python function can keep its name while changing which calls it accepts. Changing a keyword-only parameter, its default, or whether callers must await the result is enough to make a reference page stale.

The [checker](core.py) parses top-level definitions and explicit exports from source text. It compares the declared signatures and routes dynamic exports or decorators to manual review. A side-effect tripwire in the [tests](tests/test_contracts.py#L33) would create a file if its fixture module were executed. Extracting its signature leaves the file absent.

Across 14 authored interface changes and controls, signature checking produced the expected outcome in all 14 cases. Checking symbol names alone did so in seven. Two expected outcomes were requests for manual review. These are decisions about declared interfaces. They establish neither runtime behavior under arbitrary decorators nor the quality of the documentation prose. [Mutation-by-mutation decisions](results/decisions.json) · [Counts](results/metrics.json)

## Run the signature checks

Use Python 3.11 so that the AST parser matches the recorded experiment.

```bash
python -m unittest discover -s tests -v
python run.py --output runs/local
```

[Data card](docs/data-card.md) · [Run manifest](results/manifest.json) · [Source and contribution notes](docs/provenance.md)
