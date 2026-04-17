"""AI-FEA multi-agent layer.

Each agent is a LangGraph node that receives a shared SimState
and returns tool-call actions or an updated state fragment.
Agents are wired together in ``graph.py``.
"""
