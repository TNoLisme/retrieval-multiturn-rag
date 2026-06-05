import json
from typing import List, Dict, Any

# In-Memory RAM storage for old conversational memos to avoid disk I/O and SQL database locks
# Format: { session_id: [{"summary": str, "topic": str, "entities": dict, "attributes": dict}] }
SESSION_MEMOS: Dict[str, List[Dict[str, Any]]] = {}

def search_memo_db(query_text: str, session_id: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Search old conversation memos in RAM for the current session_id.
    Uses simple keyword matching for zero-dependency local execution.
    """
    memos = SESSION_MEMOS.get(session_id, [])
    if not memos:
        return []
        
    try:
        # Tokenize query words to calculate keyword overlap with topic, summary, and attributes
        query_words = set(query_text.lower().split())
        matched_memos = []
        
        for memo in memos:
            attr_text = " ".join(memo.get("attributes", {}).values()) if isinstance(memo.get("attributes"), dict) else ""
            memo_text = f"{memo.get('topic', '')} {memo.get('summary', '')} {attr_text}"
            memo_words = set(memo_text.lower().split())
            intersection = query_words.intersection(memo_words)
            
            score = len(intersection)
            matched_memos.append((memo, score))
            
        # Sort memos by keyword overlap score descending
        matched_memos.sort(key=lambda x: x[1], reverse=True)
        
        # Return top_k memos with at least 1 keyword overlap
        results = [x[0] for x in matched_memos if x[1] > 0]
        print(f"[VectorDB Service (RAM)] Found {len(results)} matching memos in RAM for session {session_id}.")
        return results[:top_k]
    except Exception as e:
        print(f"[VectorDB Service (RAM)] Error querying memos: {e}")
        return []

def add_memo_to_db(session_id: str, summary: str, topic: str, entities: Dict[str, Any], attributes: Dict[str, Any] = None):
    """
    Save conversational memo to RAM for the current session.
    """
    try:
        if session_id not in SESSION_MEMOS:
            SESSION_MEMOS[session_id] = []
            
        SESSION_MEMOS[session_id].append({
            "summary": summary,
            "topic": topic,
            "entities": entities,
            "attributes": attributes or {}
        })
        print(f"[VectorDB Service (RAM)] Archived old conversation to memo: Topic='{topic}'")
    except Exception as e:
        print(f"[VectorDB Service (RAM)] Error adding memo: {e}")

def clear_memos_for_session(session_id: str):
    """
    Clear all memos in RAM for the specified session_id.
    """
    try:
        if session_id in SESSION_MEMOS:
            SESSION_MEMOS[session_id] = []
            print(f"[VectorDB Service (RAM)] Cleared all memos in RAM for session: {session_id}")
    except Exception as e:
        print(f"[VectorDB Service (RAM)] Error clearing memos: {e}")
