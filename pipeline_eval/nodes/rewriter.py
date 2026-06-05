from pipeline_eval.core.schema import ConversationState
from pipeline_eval.services.llm import get_llm, REWRITE_PROMPT
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

def controlled_rewrite(query: str, state: ConversationState, memos: list, retrieved_empty: bool) -> str:
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
    constraints_str = ", ".join(state.constraints) if state.constraints else "None"
    memos_str = json_format([m.get("content", str(m)) for m in memos]) if memos else "None"
    
    chain = prompt | llm | StrOutputParser()
    try:
        res = chain.invoke({
            "query": query, 
            "entities": entities_str, 
            "attributes": attributes_str, 
            "constraints": constraints_str,
            "memos": memos_str
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
