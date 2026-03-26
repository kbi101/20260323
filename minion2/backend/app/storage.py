import os
import hashlib
import json
import asyncio
from datetime import datetime
from typing import List, Optional, Dict
import time as _time
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, select, insert, update, delete, desc

class Base(DeclarativeBase):
    pass

class ModelPerformance(Base):
    __tablename__ = "model_performance"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    task_hash: Mapped[str] = mapped_column(String)
    task_content: Mapped[str] = mapped_column(Text)
    model_name: Mapped[str] = mapped_column(String)
    skill_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    feedback: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String, default="running")
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class ModelTurn(Base):
    __tablename__ = "model_turns"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String)
    model_name: Mapped[str] = mapped_column(String)
    prompt: Mapped[str] = mapped_column(Text)
    response: Mapped[str] = mapped_column(Text)
    latency_ms: Mapped[int] = mapped_column(Integer)
    feedback: Mapped[int] = mapped_column(Integer, default=0)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class ResearchReport(Base):
    __tablename__ = "research_reports"
    session_id: Mapped[str] = mapped_column(String, primary_key=True)
    task: Mapped[str] = mapped_column(Text)
    report_content: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Memory(Base):
    __tablename__ = "memories"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String)
    key: Mapped[str] = mapped_column(String)
    value: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class SearchCache(Base):
    __tablename__ = "search_cache"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    engine: Mapped[str] = mapped_column(String)
    query_hash: Mapped[str] = mapped_column(String, index=True)
    response: Mapped[str] = mapped_column(Text)
    hit_count: Mapped[int] = mapped_column(Integer, default=0)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class LLMCache(Base):
    __tablename__ = "llm_cache"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model: Mapped[str] = mapped_column(String)
    prompt_hash: Mapped[str] = mapped_column(String, index=True)
    response: Mapped[str] = mapped_column(Text)
    hit_count: Mapped[int] = mapped_column(Integer, default=0)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Storage:
    def __init__(self, db_url: str):
        if db_url.startswith("sqlite"):
            self.engine = create_async_engine(db_url)
        else:
            self.engine = create_async_engine(db_url, pool_size=10, max_overflow=20)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)

    async def init(self):
        try:
            from sqlalchemy import text
            async with self.engine.begin() as conn:
                # Create tables that don't yet exist (won't touch existing ones)
                await conn.run_sync(Base.metadata.create_all)
                # Safe schema migration: add columns introduced after initial deploy
                # 🏛️ Neural Sync: Handle SQLite vs Postgres schema prefixes
                is_sqlite = "sqlite" in str(self.engine.url)
                prefix = "" if is_sqlite else "minion."
                
                migrations = [
                    f"ALTER TABLE {prefix}model_performance ADD COLUMN skill_name TEXT",
                    f"ALTER TABLE {prefix}model_performance ADD COLUMN feedback INTEGER DEFAULT 0",
                    f"ALTER TABLE {prefix}model_performance ADD COLUMN duration_ms INTEGER DEFAULT 0",
                    f"ALTER TABLE {prefix}model_turns     ADD COLUMN feedback INTEGER DEFAULT 0",
                    f"ALTER TABLE {prefix}search_cache    ADD COLUMN hit_count INTEGER DEFAULT 0",
                    f"ALTER TABLE {prefix}llm_cache       ADD COLUMN hit_count INTEGER DEFAULT 0",
                ]
                # Note: ADD COLUMN IF NOT EXISTS isn't standard in older Postgres/SQLite.
                # We catch exceptions for 'already exists' instead for maximum cross-dialect fidelity.
                for sql in migrations:
                    try:
                        await conn.execute(text(sql))
                    except Exception:
                        pass  # column already exists — ignore
            print("🏛️ Persistence Core: Synched with Intelligence Hub Successfully.")
        except Exception as e:
            print(f"⚠️ Persistence Warning: Could not reach Remote Host at this moment ({str(e)}). Proceeding in Standby Mode.")

    async def record_start(self, id: str, task: str, model: str, skill: str):
        try:
            async with self.session_factory() as session:
                h = hashlib.md5(task.encode()).hexdigest()
                # Intelligent Guard: Check if this mission ID already manifested
                res = await session.execute(select(ModelPerformance).where(ModelPerformance.id == id))
                existing = res.scalar_one_or_none()
                
                if existing:
                    existing.task_content = task
                    existing.task_hash = h
                    existing.model_name = model
                    existing.skill_name = skill
                    existing.timestamp = datetime.utcnow()
                    existing.status = "running"
                else:
                    session.add(ModelPerformance(id=id, task_hash=h, task_content=task, model_name=model, skill_name=skill))
                
                await session.commit()
        except Exception as e:
            print(f"⚠️ Persistence Error (record_start): {str(e)}")

    async def record_end(self, sid: str, duration_ms: int, status: str = "success"):
        """Marks a mission as complete with final duration and outcome."""
        try:
            async with self.session_factory() as session:
                res = await session.execute(select(ModelPerformance).where(ModelPerformance.id == sid))
                existing = res.scalar_one_or_none()
                if existing:
                    existing.duration_ms = duration_ms
                    existing.status = status
                    await session.commit()
        except Exception as e:
            print(f"⚠️ Persistence Error (record_end): {str(e)}")

    async def record_feedback(self, sid: str, feedback: int):
        """Applies a user feedback score (thumbs up/down) to a session for learning."""
        try:
            async with self.session_factory() as session:
                res = await session.execute(select(ModelPerformance).where(ModelPerformance.id == sid))
                perf = res.scalar_one_or_none()
                if perf:
                    perf.feedback = feedback
                    await session.commit()
                # Also stamp all turns in this session
                from sqlalchemy import update as sql_update
                await session.execute(
                    sql_update(ModelTurn).where(ModelTurn.session_id == sid).values(feedback=feedback)
                )
                await session.commit()
                print(f"⭐ Feedback {feedback} applied to session {sid}")
        except Exception as e:
            print(f"⚠️ Persistence Error (record_feedback): {str(e)}")

    async def get_best_model_for_task(self, task_hash: str) -> Optional[str]:
        """DB-driven routing: returns the highest-feedback, lowest-latency model for a task."""
        try:
            from sqlalchemy import text
            async with self.session_factory() as session:
                result = await session.execute(text("""
                    SELECT mt.model_name,
                           AVG(mt.latency_ms) as avg_latency,
                           SUM(mt.feedback)   as total_score
                    FROM model_turns mt
                    JOIN model_performance mp ON mt.session_id = mp.id
                    WHERE mp.task_hash = :hash
                    GROUP BY mt.model_name
                    HAVING SUM(mt.feedback) > 0
                    ORDER BY SUM(mt.feedback) DESC, AVG(mt.latency_ms) ASC
                    LIMIT 1
                """), {"hash": task_hash})
                row = result.fetchone()
                if row:
                    return row[0]
        except Exception as e:
            print(f"⚠️ Router DB Error: {str(e)}")
        return None

    async def record_turn(self, sid: str, model: str, prompt: str, response: str, latency: int):
        try:
            async with self.session_factory() as session:
                session.add(ModelTurn(session_id=sid, model_name=model, prompt=prompt, response=response, latency_ms=latency))
                await session.commit()
        except Exception as e:
            print(f"⚠️ Persistence Error (record_turn): {str(e)}")

    async def record_report(self, sid: str, task: str, content: str):
        try:
            async with self.session_factory() as session:
                # Check if exists
                res = await session.execute(select(ResearchReport).where(ResearchReport.session_id == sid))
                existing = res.scalar_one_or_none()
                if existing:
                    existing.report_content = content
                else:
                    session.add(ResearchReport(session_id=sid, task=task, report_content=content))
                await session.commit()
        except Exception as e:
            print(f"⚠️ Persistence Error (record_report): {str(e)}")

    async def list_memories(self, session_id: str) -> List[Dict]:
        try:
            async with self.session_factory() as session:
                res = await session.execute(
                    select(Memory.id, Memory.key, Memory.value).where(Memory.session_id == session_id)
                )
                return [{"id": row.id, "key": row.key, "value": row.value} for row in res]
        except Exception as e:
            print(f"❌ List Memory Fault: {str(e)}")
            return []

    # ── LLM Response Caching ──────────────────────────────────────────────────
    # ── Search Engine Caching (24h Window) ────────────────────────────────────
    async def get_search_cache(self, engine: str, query: str) -> Optional[str]:
        q_hash = hashlib.md5(query.lower().strip().encode()).hexdigest()
        try:
            async with self.session_factory() as session:
                # 🏛️ Neural Retrieval: Using session directly to allow for hit_count updates within the transaction
                res = await session.execute(
                    select(SearchCache).where(
                        SearchCache.engine == engine, SearchCache.query_hash == q_hash
                    ).order_by(desc(SearchCache.timestamp))
                )
                cache_entry = res.scalars().first()
                if cache_entry:
                    # 🏛️ Synaptic Freshness: Verify 24-hour validity
                    from datetime import datetime
                    age = datetime.utcnow() - cache_entry.timestamp
                    if age.total_seconds() < 24 * 3600:
                        # Increment hit counter for telemetry
                        cache_entry.hit_count += 1
                        await session.commit()
                        return cache_entry.response
        except Exception:
            pass
        return None

    async def set_search_cache(self, engine: str, query: str, response: str):
        q_hash = hashlib.md5(query.lower().strip().encode()).hexdigest()
        try:
            async with self.session_factory() as session:
                session.add(SearchCache(engine=engine, query_hash=q_hash, response=response))
                await session.commit()
        except Exception:
            pass

    async def get_llm_cache(self, model: str, prompt_hash: str) -> Optional[str]:
        try:
            async with self.session_factory() as session:
                res = await session.execute(
                    select(LLMCache).where(LLMCache.model == model, LLMCache.prompt_hash == prompt_hash)
                    .order_by(desc(LLMCache.timestamp))
                )
                cache_entry = res.scalars().first()
                if cache_entry:
                    cache_entry.hit_count += 1
                    await session.commit()
                    return cache_entry.response
        except Exception:
            return None

    async def set_llm_cache(self, model: str, prompt_hash: str, response: str):
        try:
            async with self.session_factory() as session:
                new_cache = LLMCache(model=model, prompt_hash=prompt_hash, response=response)
                session.add(new_cache)
                await session.commit()
        except Exception as e:
            print(f"⚠️ Cache Write Warning: {str(e)}")

    async def get_memories(self, sid: str = None):
        try:
            async with self.session_factory() as session:
                stmt = select(Memory)
                if sid:
                    stmt = stmt.where(Memory.session_id == sid)
                stmt = stmt.order_by(desc(Memory.timestamp))
                res = await session.execute(stmt)
                return [{k: v for k, v in m.__dict__.items() if k != "_sa_instance_state"} for m in res.scalars().all()]
        except Exception:
            return []

    async def get_history(self):
        try:
            async with self.session_factory() as session:
                stmt = select(ModelPerformance).order_by(desc(ModelPerformance.timestamp)).limit(50)
                res = await session.execute(stmt)
                return [{k: v for k, v in m.__dict__.items() if k != "_sa_instance_state"} for m in res.scalars().all()]
        except Exception:
            return []

    async def get_turns(self, sid: str):
        try:
            async with self.session_factory() as session:
                stmt = select(ModelTurn).where(ModelTurn.session_id == sid).order_by(ModelTurn.timestamp)
                res = await session.execute(stmt)
                return [{k: v for k, v in t.__dict__.items() if k != "_sa_instance_state"} for t in res.scalars().all()]
        except Exception:
            return []

    async def get_report(self, sid: str):
        async with self.session_factory() as session:
            stmt = select(ResearchReport).where(ResearchReport.session_id == sid)
            res = await session.execute(stmt)
            rep = res.scalar_one_or_none()
            if not rep: return None
            return {k: v for k, v in rep.__dict__.items() if k != "_sa_instance_state"}

    async def get_all_reports(self) -> List[Dict]:
        try:
            async with self.session_factory() as session:
                stmt = select(ResearchReport.session_id, ResearchReport.task, ResearchReport.timestamp, ResearchReport.report_content).order_by(desc(ResearchReport.timestamp))
                res = await session.execute(stmt)
                return [{"session_id": row.session_id, "task": row.task, "timestamp": row.timestamp, "report_content": row.report_content} for row in res]
        except Exception as e:
            print(f"❌ List Reports Fault: {str(e)}")
            return []

    async def delete_session(self, sid: str):
        async with self.session_factory() as session:
            await session.execute(delete(ModelPerformance).where(ModelPerformance.id == sid))
            await session.execute(delete(ModelTurn).where(ModelTurn.session_id == sid))
            await session.execute(delete(ResearchReport).where(ResearchReport.session_id == sid))
            await session.execute(delete(Memory).where(Memory.session_id == sid))
            await session.commit()
            # 🏛️ Neural Sync: Also clear the reasoning cache on deletion to ensure a clean slate for the next run
            await self.clear_cache()

    async def clear_cache(self):
        async with self.session_factory() as session:
            await session.execute(delete(LLMCache))
            await session.execute(delete(SearchCache))
            await session.commit()
