"""
LLM Agent orchestrator -- Claude with tool use for wine recommendation.

Uses the orchestrator-worker pattern (not LangChain/LangGraph) to keep
the implementation clean and transparent. A hedge fund interviewer will
appreciate seeing the mechanics rather than a framework import.

The agent has 5 tools:
1. search_wines_by_attributes  -- SQL query builder
2. semantic_search_tasting_notes -- pgvector + BM25 hybrid
3. get_similar_users_wines -- collaborative filtering (surprise SVD)
4. score_wine -- structured output via Pydantic
5. compare_prices -- cross-provider price lookup

Finance analogy:
- This is the "quant research assistant" that queries multiple signal
  sources and produces a ranked, explainable recommendation.

TODO: Implement once pgvector and embeddings are in place.
"""
