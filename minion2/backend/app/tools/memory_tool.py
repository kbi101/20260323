from typing import Dict, Any, List

async def remember_memory(db, sid: str, key: str, value: str) -> str:
    """Stores a piece of information in the session's memory bank."""
    try:
        from ..storage import Memory
        async with db.session_factory() as session:
            session.add(Memory(session_id=sid, key=key, value=value))
            await session.commit()
            return f"✅ Knowledge archived under key: /{key}"
    except Exception as e:
        return f"❌ Memory Fault: {str(e)}"


async def recall_memory(db, sid: str, key: str = None) -> str:
    """Retrieves specifically keyed information or all session memories."""
    try:
        memories = await db.get_memories(sid)
        if not memories:
            return "⚠️ No memories found for this session."

        if key:
            filtered = [m for m in memories if key.lower() in m['key'].lower() or key.lower() in m['value'].lower()]
            if filtered:
                lines = [f"/{m['key']}: {m['value']}" for m in filtered]
                return "🔍 Matching Memories:\n" + "\n".join(lines)
            return f"⚠️ No memory found matching: /{key}"

        lines = [f"/{m['key']}: {m['value']}" for m in memories]
        return "🧠 Active Memory Bank:\n" + "\n".join(lines)
    except Exception as e:
        return f"❌ Recall Fault: {str(e)}"


async def forget_memory(db, sid: str, key: str) -> str:
    """
    ✅ FIX P1: Ports the 'forget' tool from memory-server.ts.
    Deletes a specific memory entry by key so the agent can correct mistakes.
    """
    try:
        from sqlalchemy import delete
        from ..storage import Memory
        async with db.session_factory() as session:
            await session.execute(
                delete(Memory).where(Memory.session_id == sid, Memory.key == key)
            )
            await session.commit()
            return f"🗑️ Memory /{key} deleted successfully."
    except Exception as e:
        return f"❌ Forget Fault: {str(e)}"


async def list_memories(db, sid: str) -> str:
    """
    ✅ FIX P1: Ports the 'list_memories' tool from memory-server.ts.
    Lists all stored memories with keys and timestamps so the agent can audit them.
    """
    try:
        memories = await db.get_memories(sid)
        if not memories:
            return "⚠️ No memories stored for this session."
        lines = [f"  [{m.get('id', '?')}] /{m['key']} (saved: {str(m.get('timestamp', ''))[:16]})" for m in memories]
        return "📋 Memory Bank Inventory:\n" + "\n".join(lines)
    except Exception as e:
        return f"❌ List Fault: {str(e)}"
