# Documentation as a checked interface

Topic: developer tooling. Decision: identify documentation that no longer matches a declared public function interface.

A symbol-presence check misses renamed parameters, changed defaults, argument kinds and async behavior. My static checker compares structured signatures from Python ASTs against a versioned documentation manifest. It parses fixture code without importing or executing it. Dynamic exports and decorators produce a manual-review outcome rather than an unjustified match.

Across 14 authored mutations, symbol-only checking meets 7 contracts and signature-aware checking meets 14. Two cases require manual review. decisions.json contains every actual and documented signature difference.

These are targeted regression contracts, not documentation quality or LLM accuracy. Module control flow that references exports, conditional public functions, and functions declaring global exports require review. Function-local variables named __all__ are not mistaken for module exports. AST declarations do not prove runtime behavior, side effects, semantic descriptions, API compatibility, or every Python export form. Next, I would integrate this narrow check into a repository that already maintains an explicit public-function documentation manifest and pair it with human semantic review.
