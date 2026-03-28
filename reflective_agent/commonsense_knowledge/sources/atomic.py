from __future__ import annotations

from reflective_agent.models import CommonsenseEntity, CommonsenseEvidenceRecord, CommonsenseQuery


class AtomicSource:
    """Reserved adapter slot. Not used as a primary evidence source in v0."""

    def query(
        self,
        query: CommonsenseQuery,
        entities: list[CommonsenseEntity],
    ) -> list[CommonsenseEvidenceRecord]:
        return []
