import json
from pipeline_eval.core.schema import ConversationState, TrackerOutput
from pipeline_eval.services.llm import get_llm, TRACKER_PROMPT
from langchain_core.prompts import ChatPromptTemplate
import re

# English referring pronouns for tracking
ENGLISH_PRONOUNS = {
    # Singular pronouns
    "it", "he", "she", "him", "her", "his", "its",
    # Plural pronouns
    "they", "them", "their", "theirs", "these", "those",
    # Demonstratives
    "this", "that", "there", "here", "then",
    # Reference phrases
    "that one", "this one", "those ones", "these ones",
    "that person", "this person", "that thing", "this thing",
    "the item", "the subject", "the object", "the topic"
}

def _clean_and_tokenize(text: str) -> list:
    cleaned = re.sub(r'[^\w\s\d]', ' ', text.lower())
    return cleaned.split()

def _sanitize_output(query: str, state: ConversationState, need_retrieval_from_llm: bool) -> TrackerOutput:
    """
    Post-processing output validation:
    1. Filter unresolved_references: keep only pronouns that ACTUALLY appear as independent tokens in the user query.
    2. Recalculate need_retrieval: need_retrieval = True if and only if state.entities is empty {}.
    """
    q_tokens = _clean_and_tokenize(query)
    q_str = " " + " ".join(q_tokens) + " " if q_tokens else ""
    
    validated_refs = []
    for ref in state.unresolved_references:
        ref_tokens = _clean_and_tokenize(ref)
        if not ref_tokens:
            continue
        ref_str = " " + " ".join(ref_tokens) + " "
        if ref_str in q_str:
            validated_refs.append(ref)
            
    state.unresolved_references = validated_refs
    
    # Recalculate need_retrieval based on empty entities
    actual_need_retrieval = len(state.entities) == 0
    
    return TrackerOutput(
        state=state,
        need_retrieval=actual_need_retrieval,
        confidence=1.0 if not actual_need_retrieval else 0.8
    )

def state_tracker_node(query: str, old_state: ConversationState) -> TrackerOutput:
    """
    Track conversational entities, attributes, and constraints.
    Applies post-processing sanitization on LLM output.
    """
    import os
    llm = get_llm(temperature=0.0)
    prompt = ChatPromptTemplate.from_template(TRACKER_PROMPT)
    
    openai_key = os.getenv("OPENAI_API_KEY")
    
    # 1. Use LangChain structured output if OpenAI API key is present
    if openai_key:
        try:
            structured_llm = llm.with_structured_output(TrackerOutput)
            chain = prompt | structured_llm
            output = chain.invoke({"query": query, "old_state": old_state.model_dump_json()})
            output = _sanitize_output(query, output.state, output.need_retrieval)
            print(f"[Tracker Node] Updated State (OpenAI). Need retrieval: {output.need_retrieval}")
            return output
        except Exception as e:
            print(f"[Tracker Node] OpenAI structured output failed: {e}. Falling back to JSON parsing...")
            
    # 2. Local JSON generation and parsing (for Ollama or fallback)
    from langchain_core.output_parsers import StrOutputParser
    chain = prompt | llm | StrOutputParser()
    res_str = chain.invoke({"query": query, "old_state": old_state.model_dump_json()}).strip()
    
    match = re.search(r'\{.*\}', res_str, re.DOTALL)
    if match:
        res_str = match.group(0)
    else:
        if res_str.startswith("```json"):
            res_str = res_str[7:]
        if res_str.endswith("```"):
            res_str = res_str[:-3]
        res_str = res_str.strip()
    
    try:
        data = json.loads(res_str)
        state_data = data.get("state", {})
        state = ConversationState(
            intent=state_data.get("intent", "inquiry"),
            entities=state_data.get("entities", {}),
            attributes=state_data.get("attributes", {}),
            constraints=state_data.get("constraints", []),
            unresolved_references=state_data.get("unresolved_references", [])
        )
        output = _sanitize_output(query, state, bool(data.get("need_retrieval", False)))
        print(f"[Tracker Node (Local/Fallback)] Successfully parsed JSON. Need retrieval: {output.need_retrieval}")
        return output
    except Exception as json_err:
        print(f"[Tracker Node] JSON parsing failed: {json_err}. Raw output: {res_str}")
        return TrackerOutput(
            state=old_state,
            need_retrieval=len(old_state.entities) == 0,
            confidence=0.5
        )
