"""
Semantic search engine -- RAG over tasting notes and descriptions.

Embeds tasting notes with text-embedding-3-small, stores in pgvector,
and retrieves via hybrid search (vector similarity + BM25 keyword).

Finance analogy:
- Tasting notes = research reports / analyst commentary
- Embedding = document representation for NLP signal
- Hybrid retrieval = combining semantic and keyword signals

TODO: Implement once pgvector schema and embedding pipeline are ready.
"""
