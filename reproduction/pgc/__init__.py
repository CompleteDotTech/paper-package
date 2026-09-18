"""
Typed Probabilistic Graph Compiler (PGC)

A system architecture for autonomous graph synthesis via typed decisions.

Core modules:
  - pgc.ir: Intermediate representations (Evidence, Candidates, Decisions, Constraints, Mutations)
  - pgc.decision: Pluggable decision backends (Jev, LLM, specialist classifiers)
  - pgc.compiler: Graph compilation orchestrator
  - pgc.experiments: Example walkthroughs and benchmarks
"""

__version__ = "0.1-prototype"
__author__ = "Claude Code"
