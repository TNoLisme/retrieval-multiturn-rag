from pipeline_eval.core.schema import ConversationState
from pipeline_eval.nodes.boundary import hinge_mem_check
from pipeline_eval.nodes.tracker import state_tracker_node
from pipeline_eval.nodes.retriever import safe_merge
from pipeline_eval.nodes.rewriter import controlled_rewrite
from pipeline_eval.core.state import (
    load_state_from_redis, 
    save_state_to_redis, 
    load_history, 
    save_history, 
    archive_to_memo,
    clear_session_cache
)
from pipeline_eval.services.vector_db import search_memo_db

def vector_db_search(state: ConversationState, session_id: str, query: str = ""):
    """
    Search old memos in the RAM database.
    """
    # Combine lists into strings
    ent_str = " ".join(state.entities) if state.entities else ""
    attr_str = " ".join(state.attributes) if state.attributes else ""
    
    # Merge all available keywords
    parts = []
    if ent_str: parts.append(ent_str)
    if attr_str: parts.append(attr_str)
    if query: parts.append(query)
    
    if parts:
        query_term = " ".join(parts)
    else:
        query_term = "conversation"
        
    print(f"[3. Retrieval & Fusion (Retrieve Memo)] Querying Memo DB for keywords: '{query_term}'...")
    return search_memo_db(query_term, session_id, top_k=5)

def run_pipeline(user_query: str, session_id: str) -> str:
    """
    Orchestrate the State-Centric Query Rewriting Pipeline.
    Input: raw query, session ID
    Output: standalone query (or clarification request)
    """
    print(f"\n⚡ [Pipeline Eval] Starting State-Centric Pipeline for Session '{session_id}'")
    
    # 1. Load old state and active chat history
    old_state = load_state_from_redis(session_id) or ConversationState()
    active_chat = load_history(session_id)
    
    print(f"   ├─ Query_t (Raw Query): '{user_query}'")
    print(f"   ├─ Active Chat (Short History): {len(active_chat)} turns")
    print(f"   └─ State_t-1 (Old State): Entities={old_state.entities}, Unresolved={old_state.unresolved_references}")

    # 2. Boundary Detection Layer (HingeMem)
    print("[1. Boundary Detection (HingeMem)] Checking boundary...")
    boundary = hinge_mem_check(user_query, active_chat, old_state)
    print(f"[1. Boundary Detection (HingeMem)] Result: {boundary.upper()}")
    
    if boundary == "hard_shift":
        print("[1. Boundary Detection (HingeMem / Reset)] HARD SHIFT detected. Archiving old history and resetting state...")
        archive_to_memo(session_id, active_chat, old_state)
        old_state = ConversationState()  # Reset state
        active_chat = []  # Clear short-term history
        clear_session_cache(session_id)

    # 3. State Management Layer (State Tracker + Checker)
    print("[2. State Management (State Tracker + Checker)] Tracking state...")
    tracker_out = state_tracker_node(user_query, old_state)
    new_state = tracker_out.state
    print(f"[2. State Management (State Tracker + Checker)] New State (State_t): Entities={new_state.entities}, Unresolved={new_state.unresolved_references}")
    print(f"[2. State Management (State Tracker + Checker)] Need Retrieval: {tracker_out.need_retrieval}")
    
    # 4. Retrieval & Fusion Layer
    retrieved_empty = False
    print("[3. Retrieval (Fetch Memos)] Retrieving memos for rewrite...")
    memos = vector_db_search(new_state, session_id, query=user_query)
    
    if not memos:
        print("[3. Retrieval] No matching memos found in DB.")
        retrieved_empty = True
    else:
        print(f"[3. Retrieval] Found {len(memos)} matching memos.")
        
    if tracker_out.need_retrieval and memos:
        print("[3. Memory Fusion (Safe Merge)] State incomplete. Safe Merging memo information...")
        new_state = safe_merge(new_state, memos)
        print(f"[3. Memory Fusion] State after Safe Merge: Entities={new_state.entities}")

    # 5. Generation Layer (Controlled Rewrite)
    print("[4. Generation Layer (Controlled Rewrite)] Generating standalone query...")
    q_final = controlled_rewrite(user_query, new_state, memos, retrieved_empty, active_chat=active_chat)
    print(f"[4. Generation Layer (Controlled Rewrite)] Rewritten: '{user_query}' ➔ '{q_final}'")
    
    # 6. Save state and history for next turn
    save_state_to_redis(session_id, new_state)
    save_history(session_id, user_query, q_final)
    
    return q_final
