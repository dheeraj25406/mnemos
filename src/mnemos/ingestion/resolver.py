import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from mnemos.db.models import Entity, EntityAlias, Fact, Relationship


class EntityResolver:
    """
    Resolves entity mentions to canonical entities, manages aliases,
    and handles entity deduplication and merging.
    """

    @classmethod
    async def resolve_or_create(
        cls,
        session: AsyncSession,
        tenant_id: str,
        name: str,
        entity_type: str = "concept",
        description: str | None = None,
        confidence: float = 1.0,
    ) -> Entity:
        """
        Resolves entity name against canonical names and aliases.
        Creates a new entity and registers the alias if not found.
        """
        clean_name = name.strip()
        lower_name = clean_name.lower()

        # 1. Check direct name match
        direct_stmt = (
            select(Entity)
            .where(
                Entity.tenant_id == tenant_id,
                func.lower(Entity.name) == lower_name,
                Entity.is_active == True,
            )
            .limit(1)
        )
        result = await session.execute(direct_stmt)
        entity = result.scalars().first()

        if entity:
            if entity.canonical_id:
                canonical = await session.get(Entity, entity.canonical_id)
                if canonical and canonical.is_active:
                    return canonical
            return entity

        # 2. Check alias table
        alias_stmt = (
            select(Entity)
            .join(EntityAlias, EntityAlias.entity_id == Entity.id)
            .where(
                EntityAlias.tenant_id == tenant_id,
                func.lower(EntityAlias.alias) == lower_name,
                Entity.is_active == True,
            )
            .limit(1)
        )
        alias_result = await session.execute(alias_stmt)
        entity_from_alias = alias_result.scalars().first()

        if entity_from_alias:
            if entity_from_alias.canonical_id:
                canonical = await session.get(Entity, entity_from_alias.canonical_id)
                if canonical and canonical.is_active:
                    return canonical
            return entity_from_alias

        # 3. Create new entity
        new_id = f"ent_{uuid.uuid4().hex[:12]}"
        new_entity = Entity(
            id=new_id,
            tenant_id=tenant_id,
            name=clean_name,
            entity_type=entity_type,
            description=description,
            confidence=confidence,
            is_active=True,
        )
        session.add(new_entity)

        # Register canonical name as an alias
        alias = EntityAlias(
            tenant_id=tenant_id,
            entity_id=new_id,
            alias=clean_name,
        )
        session.add(alias)
        await session.flush()

        return new_entity

    @classmethod
    async def add_alias(
        cls,
        session: AsyncSession,
        tenant_id: str,
        entity_id: str,
        alias_name: str,
    ) -> None:
        """Register an alternative name for an existing entity."""
        clean_alias = alias_name.strip()
        alias_stmt = select(EntityAlias).where(
            EntityAlias.tenant_id == tenant_id,
            func.lower(EntityAlias.alias) == clean_alias.lower(),
        )
        existing = (await session.execute(alias_stmt)).scalars().first()
        if not existing:
            alias = EntityAlias(
                tenant_id=tenant_id,
                entity_id=entity_id,
                alias=clean_alias,
            )
            session.add(alias)
            await session.flush()

    @classmethod
    async def merge_entities(
        cls,
        session: AsyncSession,
        tenant_id: str,
        primary_id: str,
        secondary_id: str,
    ) -> Entity:
        """
        Merges secondary entity into primary entity:
        - Points secondary.canonical_id = primary_id
        - Re-points all facts and relationships to primary_id
        - Transfers aliases to primary_id
        """
        primary = await session.get(Entity, primary_id)
        secondary = await session.get(Entity, secondary_id)

        if not primary or not secondary:
            raise ValueError(f"Entities not found: {primary_id}, {secondary_id}")

        secondary.canonical_id = primary_id
        secondary.is_active = False

        # Transfer aliases
        alias_stmt = select(EntityAlias).where(
            EntityAlias.tenant_id == tenant_id,
            EntityAlias.entity_id == secondary_id,
        )
        aliases = (await session.execute(alias_stmt)).scalars().all()
        for a in aliases:
            a.entity_id = primary_id

        # Re-point facts where secondary is subject
        subj_facts = (
            await session.execute(
                select(Fact).where(Fact.tenant_id == tenant_id, Fact.subject_id == secondary_id)
            )
        ).scalars().all()
        for f in subj_facts:
            f.subject_id = primary_id

        # Re-point facts where secondary is object
        obj_facts = (
            await session.execute(
                select(Fact).where(Fact.tenant_id == tenant_id, Fact.object_id == secondary_id)
            )
        ).scalars().all()
        for f in obj_facts:
            f.object_id = primary_id

        # Re-point relationships
        src_rels = (
            await session.execute(
                select(Relationship).where(
                    Relationship.tenant_id == tenant_id,
                    Relationship.source_entity_id == secondary_id,
                )
            )
        ).scalars().all()
        for r in src_rels:
            r.source_entity_id = primary_id

        tgt_rels = (
            await session.execute(
                select(Relationship).where(
                    Relationship.tenant_id == tenant_id,
                    Relationship.target_entity_id == secondary_id,
                )
            )
        ).scalars().all()
        for r in tgt_rels:
            r.target_entity_id = primary_id

        await session.flush()
        return primary
