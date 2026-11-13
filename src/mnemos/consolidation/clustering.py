from typing import Any
import numpy as np


class MemoryClusterer:
    """Clusters memory items based on vector embedding cosine proximity."""

    @classmethod
    def cluster_by_similarity(
        cls,
        memories: list[dict[str, Any]],  # [{"id": str, "content": str, "vector": list[float]}]
        threshold: float = 0.85,
    ) -> list[list[dict[str, Any]]]:
        """
        Greedy single-linkage agglomerative clustering.
        Groups memories with cosine similarity >= threshold.
        """
        if not memories:
            return []

        clusters: list[list[dict[str, Any]]] = []
        assigned = set()

        for i, m1 in enumerate(memories):
            if m1["id"] in assigned:
                continue

            current_cluster = [m1]
            assigned.add(m1["id"])
            v1 = np.array(m1["vector"])
            norm1 = np.linalg.norm(v1)

            if norm1 == 0:
                clusters.append(current_cluster)
                continue

            for j, m2 in enumerate(memories):
                if m2["id"] in assigned:
                    continue

                v2 = np.array(m2["vector"])
                norm2 = np.linalg.norm(v2)
                if norm2 == 0:
                    continue

                cos_sim = float(np.dot(v1, v2) / (norm1 * norm2))
                if cos_sim >= threshold:
                    current_cluster.append(m2)
                    assigned.add(m2["id"])

            clusters.append(current_cluster)

        return clusters
