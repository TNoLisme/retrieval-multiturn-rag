from typing import List, Dict, Any
from pipeline_eval.core.schema import ConversationState

def safe_merge(current_state: ConversationState, retrieved_memos: List[Dict[str, Any]]) -> ConversationState:
    """
    Fill in missing information (Gap Filling) from old conversation memos into the current state.
    
    Principles:
    - ONLY fill in empty slots (do not overwrite entities/attributes set in the current turn).
    - After merge, if entities is not empty, clear unresolved_references.
    """
    if not retrieved_memos:
        return current_state
    
    # Use the top retrieved memo
    memo = retrieved_memos[0]
    
    # Gap-fill entities
    memo_entities = memo.get("entities", {})
    if isinstance(memo_entities, dict):
        for key, value in memo_entities.items():
            if key not in current_state.entities:
                current_state.entities[key] = value
                print(f"[Retriever Node] Gap-fill entities: '{key}' = '{value}' (from Memo).")
    
    # Gap-fill attributes
    memo_attributes = memo.get("attributes", {})
    if isinstance(memo_attributes, dict):
        for key, value in memo_attributes.items():
            if key not in current_state.attributes:
                current_state.attributes[key] = value
                print(f"[Retriever Node] Gap-fill attributes: '{key}' = '{value}' (from Memo).")

    # Clear unresolved references if entities are now resolved
    if current_state.entities:
        current_state.unresolved_references = []
        print(f"[Retriever Node] Safe Merge completed. Entities: {current_state.entities}")
        
    return current_state
