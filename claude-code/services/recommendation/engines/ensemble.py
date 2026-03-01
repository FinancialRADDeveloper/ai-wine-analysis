"""
Ensemble scorer -- combines signals from all recommendation engines.

    final_score = w_content * content_score
                + w_collab  * collab_score
                + w_rag     * rag_similarity_score

Weights are tracked in MLflow as experiments.

Finance analogy:
- This is portfolio construction / alpha combination
- Each engine produces a signal; the ensemble weights them
- MLflow = backtesting framework for tracking weight experiments

TODO: Implement once individual engines are working.
"""
