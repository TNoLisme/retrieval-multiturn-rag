from typing import List, Dict, Union
from pipeline_eval.services.llm import get_llm, FALLBACK_PROMPT
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import re

# English stop words - excluded from semantic Jaccard matching
ENGLISH_STOP_WORDS = {
    "is", "are", "was", "were", "be", "been", "being",
    "a", "an", "the", "and", "or", "but", "if", "then",
    "of", "at", "by", "for", "with", "about", "against",
    "between", "into", "through", "during", "before", "after",
    "above", "below", "to", "from", "up", "down", "in", "out",
    "on", "off", "over", "under", "again", "further", "then",
    "once", "here", "there", "when", "where", "why", "how",
    "all", "any", "both", "each", "few", "more", "most",
    "other", "some", "such", "no", "nor", "not", "only",
    "own", "same", "so", "than", "too", "very", "s", "t",
    "can", "will", "just", "don", "should", "now",
    "?", ".", ",", "!", ":", ";", "(", ")", "[", "]"
}

# English referring pronouns - ALWAYS trigger CONTINUE as they reference previous context
ENGLISH_REFERRING_PRONOUNS = {
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
    """Clean punctuation, lowercase and split text into tokens."""
    cleaned = re.sub(r'[^\w\s\d]', ' ', text.lower())
    return cleaned.split()

def _contains_referring_pronoun(query: str) -> str | None:
    """Check if the query contains referring pronouns as independent words/phrases."""
    q_tokens = _clean_and_tokenize(query)
    if not q_tokens:
        return None
    
    q_str = " " + " ".join(q_tokens) + " "
    
    for pronoun in ENGLISH_REFERRING_PRONOUNS:
        p_tokens = _clean_and_tokenize(pronoun)
        if not p_tokens:
            continue
        p_str = " " + " ".join(p_tokens) + " "
        if p_str in q_str:
            return pronoun
    return None

def _content_words(text: str) -> set:
    """Tokenize and filter stop words to extract meaningful content words."""
    words = set(text.lower().split())
    return words - ENGLISH_STOP_WORDS

def fallback_slm(query: str, active_chat: List[Union[str, Dict[str, str]]]) -> str:
    """
    Use SLM to evaluate if there is a topic shift when rule-based heuristic is uncertain.
    """
    llm = get_llm(temperature=0.0)
    prompt = ChatPromptTemplate.from_template(FALLBACK_PROMPT)
    chain = prompt | llm | StrOutputParser()
    
    formatted_lines = []
    for turn in active_chat[-4:]:
        if isinstance(turn, dict):
            role = "User" if turn.get("role") == "user" else "Assistant"
            content = turn.get("content", "")
            formatted_lines.append(f"{role}: {content}")
        else:
            formatted_lines.append(str(turn))
    context_str = "\n".join(formatted_lines)
    
    try:
        response = chain.invoke({"query": query, "context": context_str}).strip().lower()
        if "hard_shift" in response:
            print("[Boundary Node] SLM detected hard_shift.")
            return "hard_shift"
        print("[Boundary Node] SLM detected continue.")
        return "continue"
    except Exception as e:
        print(f"[Boundary Node] SLM error: {e}. Defaulting to continue.")
        return "continue"

def extract_entities(text: str) -> set:
    """Extract entities using LLM to calculate entity shift."""
    from pipeline_eval.services.llm import ENTITY_EXTRACTION_PROMPT
    if not text.strip():
        return set()
        
    llm = get_llm(temperature=0.0)
    prompt = ChatPromptTemplate.from_template(ENTITY_EXTRACTION_PROMPT)
    chain = prompt | llm | StrOutputParser()
    
    try:
        response = chain.invoke({"text": text}).strip()
        if response.lower() == "none" or not response:
            return set()
        return {e.strip().lower() for e in response.split(",")}
    except Exception as e:
        print(f"[Boundary Node] Entity extraction error: {e}")
        return set()

def hinge_mem_check(query: str, active_chat: List[Union[str, Dict[str, str]]], old_state) -> str:
    """
    Event Segmentation boundary check (HingeMem) using Heuristics.
    
    1. Token Limit (Hard Shift if history > 8000 chars roughly 2000 tokens)
    2. Soft Shift: Entity Shift > 0.5 AND Semantic Shift > 0.4
    """
    if not active_chat:
        return "continue"
        
    # --- [0] Token / Length Check ---
    # Estimate tokens: 1 token = 4 chars roughly
    history_chars = sum(len(str(turn.get("content", turn) if isinstance(turn, dict) else turn)) for turn in active_chat)
    if history_chars > 8000:
        print(f"[Boundary Node] Token limit exceeded (chars: {history_chars} > 8000). HARD SHIFT.")
        return "hard_shift"
    
    # --- [1] Pronoun Pre-check ---
    found_pronoun = _contains_referring_pronoun(query)
    if found_pronoun:
        print(f"[Boundary Node] Found referring pronoun '{found_pronoun}' -> CONTINUE.")
        return "continue"
        
    # --- [2] Heuristic Calculation ---
    # Extract query entities
    query_entities = extract_entities(query)
    # Get history entities from old_state
    history_entities = set()
    if old_state and hasattr(old_state, "entities") and old_state.entities:
        history_entities = {str(v).lower() for v in old_state.entities.values()}
        
    # Entity Shift: New entities / Total entities in history
    entity_shift = 0.0
    if history_entities:
        new_entities = query_entities - history_entities
        entity_shift = len(new_entities) / len(history_entities)
    elif query_entities:
        # If no history entities but we have new ones, that's a 100% shift
        entity_shift = 1.0
        
    # Semantic Shift (Jaccard Distance): 1 - (Intersection / Union)
    # Get last turn or full history text for semantic comparison
    last_turn = active_chat[-1]
    last_text = last_turn.get("content", "") if isinstance(last_turn, dict) else str(last_turn)
        
    content_q = _content_words(query)
    content_h = _content_words(last_text)
    
    semantic_shift = 0.0
    if content_q and content_h:
        intersection = len(content_q.intersection(content_h))
        union = len(content_q.union(content_h))
        semantic_shift = 1.0 - (intersection / union)
        
    print(f"[Boundary Node] Entity Shift: {entity_shift:.2f} | Semantic Shift: {semantic_shift:.2f}")
    
    # --- [3] Threshold Evaluation ---
    if entity_shift > 0.5 and semantic_shift > 0.4:
        print("[Boundary Node] Entity > 0.5 and Semantic > 0.4. SOFT SHIFT.")
        return "hard_shift" # We trigger hard_shift to archive memo
        
    return "continue"
