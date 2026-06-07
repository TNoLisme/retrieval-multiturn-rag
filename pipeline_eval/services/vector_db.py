import json
import math
import re
from typing import List, Dict, Any

# In-Memory RAM storage for old conversational memos to avoid disk I/O and SQL database locks
# Format: { session_id: [{"summary": str, "metadata": {"topic", "entities", "attributes"}, "history": [...]}] }
SESSION_MEMOS: Dict[str, List[Dict[str, Any]]] = {}

STOP_WORDS = {
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours", 
    "yourself", "yourselves", "he", "him", "his", "himself", "she", "her", "hers", 
    "herself", "it", "its", "itself", "they", "them", "their", "theirs", "themselves", 
    "what", "which", "who", "whom", "this", "that", "these", "those", "am", "is", "are", 
    "was", "were", "be", "been", "being", "have", "has", "had", "having", "do", "does", 
    "did", "doing", "a", "an", "the", "and", "but", "if", "or", "because", "as", "until", 
    "while", "of", "at", "by", "for", "with", "about", "against", "between", "into", 
    "through", "during", "before", "after", "above", "below", "to", "from", "up", "down", 
    "in", "out", "on", "off", "over", "under", "again", "further", "then", "once", "here", 
    "there", "when", "where", "why", "how", "all", "any", "both", "each", "few", "more", 
    "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so", 
    "than", "too", "very", "s", "t", "can", "will", "just", "don", "should", "now",
    "would", "should", "could", "did", "was", "were", "go", "went", "gone", "take", "took", "taken",
    "about", "would", "shall", "does", "do", "done", "make", "made", "makes"
}

def is_stop_word(word: str) -> bool:
    word = word.lower().strip()
    word = re.sub(r'[^\w]', '', word)
    return word in STOP_WORDS

def stem_word(word: str) -> str:
    """Very simple English stemmer for common suffixes (ing, ed, es, s)."""
    word = word.lower().strip()
    word = re.sub(r'[^\w]', '', word)
    if len(word) <= 3:
        return word
    if word.endswith("ing"):
        return word[:-3]
    if word.endswith("ed"):
        return word[:-2]
    if word.endswith("ies"):
        return word[:-3] + "y"
    if word.endswith("es"):
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word

def levenshtein_distance(s1: str, s2: str) -> int:
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
        
    return previous_row[-1]

def search_memo_db(query_text: str, session_id: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Search old conversation memos in RAM for the current session_id.
    Uses simple stemmed keyword matching with IDF weights and fuzzy matching.
    """
    memos = SESSION_MEMOS.get(session_id, [])
    if not memos:
        return []
        
    try:
        # 1. Compute IDFs for the memos in this session
        doc_count = len(memos)
        dfs = {}
        for memo in memos:
            meta = memo.get("metadata", {})
            ent_list = meta.get("entities", [])
            ent_text = " ".join(ent_list) if isinstance(ent_list, list) else ""
            
            attr_list = meta.get("attributes", [])
            attr_text = " ".join(attr_list) if isinstance(attr_list, list) else ""
            
            memo_text = f"{meta.get('topic', '')} {memo.get('summary', '')} {ent_text} {attr_text}"
            words = {stem_word(w) for w in memo_text.split() if w and not is_stop_word(w)}
            for w in words:
                dfs[w] = dfs.get(w, 0) + 1
                
        idfs = {}
        for w, df in dfs.items():
            idfs[w] = math.log(1.0 + (doc_count - df + 0.5) / (df + 0.5))
            
        # 2. Tokenize and filter stop words from query
        query_words = {stem_word(w) for w in query_text.split() if w and not is_stop_word(w)}
        query_words = {w for w in query_words if w}
        if not query_words:
            # Fallback to all words if query has only stop words
            query_words = {stem_word(w) for w in query_text.split() if w}
            query_words = {w for w in query_words if w}
            
        matched_memos = []
        for memo in memos:
            meta = memo.get("metadata", {})
            ent_list = meta.get("entities", [])
            ent_text = " ".join(ent_list) if isinstance(ent_list, list) else ""
            
            attr_list = meta.get("attributes", [])
            attr_text = " ".join(attr_list) if isinstance(attr_list, list) else ""
            
            memo_text = f"{meta.get('topic', '')} {memo.get('summary', '')} {ent_text} {attr_text}"
            memo_words = {stem_word(w) for w in memo_text.split() if w and not is_stop_word(w)}
            memo_words = {w for w in memo_words if w}
            
            # Exact matches score
            exact_matches = query_words.intersection(memo_words)
            score = sum(idfs.get(w, 1.0) for w in exact_matches)
            
            # Fuzzy matches for remaining words
            rem_query = query_words - exact_matches
            rem_memo = memo_words - exact_matches
            for qw in rem_query:
                for mw in rem_memo:
                    min_len = min(len(qw), len(mw))
                    if min_len >= 5:
                        max_dist = 2 if min_len >= 8 else 1
                        if levenshtein_distance(qw, mw) <= max_dist:
                            score += 0.8 * idfs.get(mw, 1.0)
                            break
                            
            matched_memos.append((memo, score))
            
        # Sort memos by score descending
        matched_memos.sort(key=lambda x: x[1], reverse=True)
        
        # Return top_k memos with at least 0.1 score
        results = [x[0] for x in matched_memos if x[1] > 0.1]
        print(f"[VectorDB Service (RAM)] Found {len(results)} matching memos in RAM for session {session_id}.")
        return results[:top_k]
    except Exception as e:
        print(f"[VectorDB Service (RAM)] Error querying memos: {e}")
        return []

def add_memo_to_db(
    session_id: str,
    summary: str,
    topic: str,
    entities: List[str],
    attributes: List[str] = None,
    history: List[Dict[str, str]] = None
):
    """
    Save conversational memo to RAM for the current session.
    Memo schema:
      - summary  : Text summary (used for keyword search)
      - metadata : Dict with topic, entities, attributes
      - history  : List of raw chat turns in chronological order [{role, content}]
    """
    try:
        if session_id not in SESSION_MEMOS:
            SESSION_MEMOS[session_id] = []
            
        SESSION_MEMOS[session_id].append({
            "summary": summary,
            "metadata": {
                "topic": topic,
                "entities": entities,
                "attributes": attributes or []
            },
            "history": history or []
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
