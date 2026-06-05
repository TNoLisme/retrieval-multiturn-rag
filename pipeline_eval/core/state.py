import json
from typing import Dict, List, Any, Union
from pipeline_eval.core.schema import ConversationState
from pipeline_eval.services.llm import get_llm
from pipeline_eval.services.vector_db import add_memo_to_db, clear_memos_for_session
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# In-Memory Cache (Redis mock)
SESSION_STATES: Dict[str, ConversationState] = {}
SESSION_HISTORIES: Dict[str, List[Dict[str, str]]] = {}

def load_state_from_redis(session_id: str) -> ConversationState:
    """
    Load the conversation state for the session.
    """
    return SESSION_STATES.get(session_id)

def save_state_to_redis(session_id: str, state: ConversationState):
    """
    Save the conversation state for the session.
    """
    SESSION_STATES[session_id] = state

def load_history(session_id: str) -> List[Dict[str, str]]:
    """
    Load the active chat history.
    """
    return SESSION_HISTORIES.get(session_id, [])

def save_history(session_id: str, query: str, response: str = None):
    """
    Save the query and optional response to chat history.
    """
    if session_id not in SESSION_HISTORIES:
        SESSION_HISTORIES[session_id] = []
    
    SESSION_HISTORIES[session_id].append({"role": "user", "content": query})
    if response:
        SESSION_HISTORIES[session_id].append({"role": "assistant", "content": response})

def clear_session_cache(session_id: str):
    """
    Reset and clear the cache and memos for the specified session.
    """
    if session_id in SESSION_STATES:
        SESSION_STATES[session_id] = ConversationState()
    if session_id in SESSION_HISTORIES:
        SESSION_HISTORIES[session_id] = []
    
    clear_memos_for_session(session_id)


MEMO_SUMMARIZATION_PROMPT = """
You are a conversation summarizer.
Your task is to read the dialogue history below and compress it into a short topic name (Topic, under 10 words) and a brief main summary (Summary, under 50 words).

Dialogue history:
{chat_history}

You MUST return a valid JSON block with this format:
{{
  "topic": "Short Topic Name",
  "summary": "Main summary of the discussion"
}}
"""

def archive_to_memo(session_id: str, active_chat: List[Union[str, Dict[str, str]]], old_state: ConversationState):
    """
    Compress active chat history into a Memo and save it to Vector DB (RAM).
    """
    if not active_chat:
        return
    
    formatted_lines = []
    for turn in active_chat:
        if isinstance(turn, dict):
            role = "User" if turn.get("role") == "user" else "Assistant"
            content = turn.get("content", "")
            formatted_lines.append(f"{role}: {content}")
        else:
            formatted_lines.append(str(turn))
            
    chat_str = "\n".join(formatted_lines)
    
    llm = get_llm(temperature=0.0)
    prompt = ChatPromptTemplate.from_template(MEMO_SUMMARIZATION_PROMPT)
    chain = prompt | llm | StrOutputParser()
    
    try:
        res_str = chain.invoke({"chat_history": chat_str}).strip()
        
        if res_str.startswith("```json"):
            res_str = res_str[7:]
        if res_str.endswith("```"):
            res_str = res_str[:-3]
        res_str = res_str.strip()
        
        data = json.loads(res_str)
        topic = data.get("topic", "Old Conversation")
        summary = data.get("summary", "")
        
        add_memo_to_db(
            session_id=session_id,
            summary=summary,
            topic=topic,
            entities=old_state.entities,
            attributes=old_state.attributes
        )
        print(f"[State Service] Archived conversation into memo: Topic='{topic}'")
    except Exception as e:
        print(f"[State Service] Summarization error: {e}. Fallback to generic summary.")
        try:
            add_memo_to_db(
                session_id=session_id,
                summary=f"Raw history spanning {len(formatted_lines)} turns.",
                topic="Previous discussion",
                entities=old_state.entities,
                attributes=old_state.attributes
            )
        except Exception as add_err:
            print(f"[State Service] Critical memo archival failure: {add_err}")
