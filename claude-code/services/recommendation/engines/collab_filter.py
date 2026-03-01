"""
Collaborative filtering engine -- the "peer analysis" of wine recommendation.

Uses the user-wine rating matrix (from X-Wines 21M ratings) and decomposes
it via SVD to find latent taste factors.

Finance analogy:
- User-item matrix = position/returns matrix
- SVD decomposition = PCA on the covariance matrix
- Latent factors = hidden risk factors
- "Users who liked this also liked..." = "Funds with similar positioning"

TODO: Implement with surprise library once X-Wines data is ingested.
"""
