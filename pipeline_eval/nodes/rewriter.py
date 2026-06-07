from pipeline_eval.core.schema import ConversationState
from pipeline_eval.services.llm import get_llm, REWRITE_PROMPT
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

def controlled_rewrite(query: str, state: ConversationState, memos: list, retrieved_empty: bool, active_chat: list = None) -> str:
    """
    Reformulate the raw query into a standalone, context-complete query.
    If the context is missing (retrieved_empty=True) and there are no entities -> Ask a clarification question.
    """
    llm = get_llm(temperature=0.2)
    
    # Graceful Fallback: If retrieval is empty and we have no entities
    if retrieved_empty and not state.entities:
        ref_hint = state.unresolved_references[0] if state.unresolved_references else "the object"
        print(f"[Rewriter Node] Missing context. Generating Clarification Request (ref: '{ref_hint}').")
        return (
            f"Your question is unclear because it refers to '{ref_hint}' but the conversation context is missing. "
            f"Could you please specify the exact subject, person, or topic you are referring to?"
        )

    prompt = ChatPromptTemplate.from_template(REWRITE_PROMPT)
    
    entities_str = json_format(state.entities)
    attributes_str = json_format(state.attributes)
    
    # Format memos including their histories
    formatted_memos = []
    if memos:
        for idx, memo in enumerate(memos):
            metadata = memo.get("metadata", {})
            topic = metadata.get("topic", "")
            summary = memo.get("summary", "")
            entities = metadata.get("entities", [])
            attributes = metadata.get("attributes", [])
            
            # Format memo history
            memo_history = memo.get("history", [])
            history_lines = []
            for turn in memo_history:
                speaker = turn.get("speaker", "Speaker")
                text = turn.get("content", turn.get("text", ""))
                dia_id = turn.get("dia_id", "")
                id_str = f" [{dia_id}]" if dia_id else ""
                history_lines.append(f"{speaker}{id_str}: {text}")
            history_str = "\n".join(history_lines) if history_lines else "No history details."
            
            formatted_memo = (
                f"Memo #{idx+1}:\n"
                f"- Topic: {topic}\n"
                f"- Summary: {summary}\n"
                f"- Entities: {', '.join(entities) if entities else 'None'}\n"
                f"- Attributes: {', '.join(attributes) if attributes else 'None'}\n"
                f"- Chat History:\n{history_str}"
            )
            formatted_memos.append(formatted_memo)
            
    memos_str = "\n\n".join(formatted_memos) if formatted_memos else "None"
    
    # Format active chat history
    formatted_active_chat = []
    if active_chat:
        for turn in active_chat:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            formatted_active_chat.append(f"{role.capitalize()}: {content}")
    active_chat_str = "\n".join(formatted_active_chat) if formatted_active_chat else "None (First turn of the session)"
    
    chain = prompt | llm | StrOutputParser()
    try:
        res = chain.invoke({
            "query": query, 
            "entities": entities_str, 
            "attributes": attributes_str, 
            "memos": memos_str,
            "active_chat": active_chat_str
        })
        q_final = res.strip()
        return q_final
    except Exception as e:
        print(f"[Rewriter Node] Rewrite error: {e}. Fallback to raw query.")
        return query

def json_format(d) -> str:
    if not d:
        return "None"
    try:
        import json
        return json.dumps(d, ensure_ascii=False)
    except Exception:
        return str(d)
