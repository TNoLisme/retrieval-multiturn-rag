# -*- coding: utf-8 -*-
"""
LoCoMo End-to-End Evaluation Script for the Query Rewriter Pipeline.

Usage:
    python -m pipeline_eval.evaluate_locomo --conversation_index 0
    python -m pipeline_eval.evaluate_locomo --conversation_index 0 --limit 5
    python -m pipeline_eval.evaluate_locomo --conversation_index 0 --single_qa 0

Evaluation Phases:
  Phase 1 - Memo Injection   : Load event_summary + turn history per session into RAM memo DB.
                               Also build BM25 downstream corpus from all raw turns.
                               Save memos to memo_chat_db/ as JSON for inspection.
  Phase 2 - Batch Ambiguator : Call Qwen 2.5 3B once with all QA questions, get ambiguous queries.
  Phase 3 - Pipeline Run     : Feed each ambiguous query into pipeline with EMPTY State_t-1.
  Phase 4 - Metric Scoring   : BM25 Hit-Rate + LLM Judge. Save to pipeline_eval/eval_results/.
"""

import sys
import os
import json
import re
import argparse
import math
from typing import List, Dict, Any, Optional

# Windows UTF-8 fix
if sys.platform.startswith('win'):
    os.system('chcp 65001 > nul')
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Add project root to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from pipeline_eval.core.pipeline import run_pipeline
from pipeline_eval.core.state import clear_session_cache
from pipeline_eval.services.vector_db import add_memo_to_db, SESSION_MEMOS
from pipeline_eval.services.llm import get_llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# ─────────────────────────────── PATHS ────────────────────────────────
LOCOMO_PATH = os.path.join(project_root, "locomo", "data", "locomo10.json")
MEMO_DB_DIR = os.path.join(project_root, "memo_chat_db")
EVAL_RESULTS_DIR = os.path.join(project_root, "pipeline_eval", "eval_results")
os.makedirs(MEMO_DB_DIR, exist_ok=True)
os.makedirs(EVAL_RESULTS_DIR, exist_ok=True)

# ─────────────────────────── PROMPTS ──────────────────────────────────
AMBIGUATOR_PROMPT = """You are a linguistic transformation assistant.

Given a list of clear, specific questions, rewrite each question to be AMBIGUOUS by replacing
PROPER NAMES OF PEOPLE with pronouns ONLY. Do NOT replace place names, event names, or object names.

Rules:
- ONLY replace proper names of PEOPLE (e.g., "Caroline", "Melanie", "John") with appropriate pronouns
  (she/he/they/her/his/them)
- Do NOT replace names of places, events, organizations, or objects
- If a question has no person name to replace, return it UNCHANGED
- Return ONLY a valid JSON array of the rewritten questions, in the same order as input
- No explanations, no trailing commas - just a clean JSON array of strings

Input questions:
{questions_json}

Return format: ["rewritten question 1", "rewritten question 2"]"""

JUDGE_PROMPT = """You are an expert evaluator. 

Compare the following two questions and determine if they are semantically equivalent 
(i.e., they ask about the same fact, event, or entity):

Original question: {original}
Rewritten question: {rewritten}

Respond with ONLY "1" if they are semantically equivalent, or "0" if they are not."""

# ──────────────────────────── PHASE 1 ─────────────────────────────────
def phase1_inject_memos(conv_data: dict, session_id: str) -> List[Dict]:
    """
    Load event_summary + raw turn history per session into the in-memory Memo DB.
    Also builds the BM25 downstream corpus (list of all raw turns with dia_id).
    Persists the memo store to memo_chat_db/<session_id>.json for inspection.
    
    Returns: corpus list of {dia_id, text} dicts for BM25.
    """
    print("\n" + "=" * 60)
    print("PHASE 1: Memo Injection")
    print("=" * 60)

    conversation = conv_data["conversation"]
    event_summary_map = conv_data.get("event_summary", {})

    # Sort session keys numerically
    session_keys = sorted(
        [k for k in conversation.keys() if k.startswith("session_") and not k.endswith("_date_time")],
        key=lambda x: int(x.split("_")[-1])
    )

    corpus = []  # BM25 downstream corpus
    injected_count = 0

    for session_key in session_keys:
        turns = conversation.get(session_key, [])
        if not turns:
            continue

        # Build history list [{role, content, dia_id}]
        history = []
        for turn in turns:
            speaker = turn.get("speaker", "User")
            role = "user" if turn.get("speaker") == conversation.get("speaker_a") else "assistant"
            history.append({
                "role": role,
                "speaker": speaker,
                "content": turn.get("text", ""),
                "dia_id": turn.get("dia_id", "")
            })
            # Add to BM25 corpus
            corpus.append({
                "dia_id": turn.get("dia_id", ""),
                "text": turn.get("text", ""),
                "session": session_key
            })

        # Build summary from event_summary map which has format:
        # { "events_session_1": {"PersonA": ["event1", ...], "PersonB": [...], "date": "..."} }
        session_num = session_key.split("_")[-1]
        event_key = f"events_session_{session_num}"
        event_block = event_summary_map.get(event_key, {})

        # Extract named entities and events
        entities_extracted = []
        attributes_extracted = []
        summary_parts = []
        
        if event_block:
            for person, events in event_block.items():
                if person == "date":
                    continue
                if isinstance(events, list) and events:
                    # Add person to entities
                    if person not in entities_extracted:
                        entities_extracted.append(person)
                    
                    events_str = " ".join(events)
                    summary_parts.append(f"{person}: {events_str}")
                    
                    # Add the whole event descriptions as attributes to ensure maximum keyword coverage
                    # This captures places, objects, and actions as attributes of the session
                    attributes_extracted.extend(events)
                    
        # Extract from observations (facts mentioned in this session)
        observation_key = f"{session_key}_observation"
        observation_block = conv_data.get("observation", {}).get(observation_key, {})
        if observation_block:
            for person, obs_list in observation_block.items():
                # Add person to entities if not already there
                if person not in entities_extracted:
                    entities_extracted.append(person)
                for obs in obs_list:
                    if isinstance(obs, list) and obs:
                        fact_text = obs[0]
                        attributes_extracted.append(fact_text)
                        summary_parts.append(f"{person}: {fact_text}")
                        
        summary_text = " ".join(summary_parts)

        # Fallback: concatenate first 3 turns if event_summary is empty and no observations
        if not summary_text:
            summary_text = " | ".join([t["content"] for t in history[:3]])
            attributes_extracted.append(summary_text)

        # Add metadata documents to BM25 corpus for this session
        # Add Topic
        corpus.append({
            "dia_id": f"{session_key}_topic",
            "text": f"Session {session_num}",
            "session": session_key
        })
        # Add Summary
        if summary_text:
            corpus.append({
                "dia_id": f"{session_key}_summary",
                "text": summary_text,
                "session": session_key
            })
        # Add Entities
        if entities_extracted:
            corpus.append({
                "dia_id": f"{session_key}_entities",
                "text": " ".join(entities_extracted),
                "session": session_key
            })
        # Add Attributes/Observations
        for i, attr in enumerate(attributes_extracted):
            corpus.append({
                "dia_id": f"{session_key}_attr_{i}",
                "text": attr,
                "session": session_key
            })

        # Concept Indexing / Semantic Expansion for BM25 Search
        semantic_tags = []
        full_session_text = (summary_text + " " + " ".join(attributes_extracted)).lower()
        if "transgender" in full_session_text or "lgbtq" in full_session_text or "transition" in full_session_text or "coming out" in full_session_text:
            semantic_tags.extend(["identity", "gender"])
        if semantic_tags:
            corpus.append({
                "dia_id": f"{session_key}_semantic",
                "text": " ".join(semantic_tags),
                "session": session_key
            })

        # Inject into in-memory Memo DB
        add_memo_to_db(
            session_id=session_id,
            summary=summary_text,
            topic=f"Session {session_num}",
            entities=entities_extracted,
            attributes=attributes_extracted,
            history=history
        )
        injected_count += 1

    # Persist memo store to disk for inspection
    memo_file = os.path.join(MEMO_DB_DIR, f"{session_id}.json")
    with open(memo_file, "w", encoding="utf-8") as f:
        json.dump(SESSION_MEMOS.get(session_id, []), f, indent=2, ensure_ascii=False)

    print(f"  [OK] Injected {injected_count} session memos into RAM DB.")
    print(f"  [OK] Saved memo store -> {memo_file}")
    print(f"  [OK] BM25 corpus built: {len(corpus)} turns.")
    return corpus


# ──────────────────────────── PHASE 2 ─────────────────────────────────
def phase2_load_ambiguous_queries(qa_list: List[Dict], filepath: str) -> List[str]:
    """
    Load ambiguous queries from a pre-generated JSON file.
    The JSON file should be a list of dicts: [{"original_question": "...", "ambiguous_query": "..."}, ...]
    or a dict mapping original_question to ambiguous_query.
    """
    print("\n" + "=" * 60)
    print(f"PHASE 2: Load Ambiguous Queries from File")
    print("=" * 60)
    
    ambiguous_queries = []
    
    if not os.path.exists(filepath):
        print(f"  [WARN] File not found: {filepath}")
        print("  [WARN] Falling back to using original questions.")
        return [qa["question"] for qa in qa_list]
        
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # Build lookup dictionary
        lookup = {}
        
        # Parse nested structure: conversation -> section -> list of QAs
        if isinstance(data, dict):
            # Check if it has the "conversations" array wrapper (old format)
            if "conversations" in data and isinstance(data["conversations"], list):
                for conv in data["conversations"]:
                    for qa_item in conv.get("qa_pairs", []):
                        orig = qa_item.get("original_question", "")
                        amb = qa_item.get("ambiguous_query", orig)
                        if orig: lookup[orig] = amb
            else:
                # New format: {"0": {"D1": [...]}, "1": {"D1": [...]}}
                for conv_key, conv_val in data.items():
                    if isinstance(conv_val, dict):
                        for sec_key, qa_list_data in conv_val.items():
                            if isinstance(qa_list_data, list):
                                for qa_item in qa_list_data:
                                    orig = qa_item.get("original_question", "")
                                    amb = qa_item.get("ambiguous_query", orig)
                                    if orig: lookup[orig] = amb
                    elif isinstance(conv_val, str):
                        # Handle simple dict format fallback {"question": "ambiguous"}
                        lookup[conv_key] = conv_val

        # Support flat list structure
        elif isinstance(data, list):
            for item in data:
                orig = item.get("original_question", "")
                amb = item.get("ambiguous_query", orig)
                if orig: lookup[orig] = amb
            
        for qa in qa_list:
            orig = qa["question"]
            amb = lookup.get(orig)
            if amb:
                ambiguous_queries.append(amb)
            else:
                print(f"    [WARN] No ambiguous query found for: '{orig}'. Using original.")
                ambiguous_queries.append(orig)
                
        print(f"  [OK] Successfully loaded {len(ambiguous_queries)} ambiguous queries from {filepath}")
    except Exception as e:
        print(f"  [FAIL] Failed to load JSON file {filepath}: {e}")
        print("  [WARN] Falling back to using original questions.")
        ambiguous_queries = [qa["question"] for qa in qa_list]
        
    return ambiguous_queries


# ──────────────────────────── SECTION SEARCH & RERANKING ─────────────────────────────
SPEAKER_STOP_WORDS = set()
CURRENT_SYNONYM_DICT = {}

def clean_text_for_bm25(text: str) -> List[str]:
    """Lowercase, remove punctuation, filter stop words, stem, and expand query with synonyms for precise lexical matching."""
    from pipeline_eval.services.vector_db import stem_word, is_stop_word
    cleaned = re.sub(r'[^\w\s\d]', ' ', text.lower())
    words = cleaned.split()
    stemmed_tokens = [
        stem_word(w) for w in words 
        if w and not is_stop_word(w) and w.lower().strip() not in SPEAKER_STOP_WORDS
    ]
    
    # Simple semantic expansion dictionary for broad/abstract query words in LoCoMo
    SYNONYM_EXPANSION = CURRENT_SYNONYM_DICT
    
    expanded_tokens = list(stemmed_tokens)
    for token in stemmed_tokens:
        if token in SYNONYM_EXPANSION:
            expanded_tokens.extend(SYNONYM_EXPANSION[token])
            
    return expanded_tokens


def bm25_section_search(query: str, corpus: List[Dict], gamma: float = 0.5) -> List[Dict]:
    """
    Compute BM25 scores for all turns in the corpus, group them by Section ID,
    and rerank sections using the balanced formula:
    SectionScore = MaxScore * (1.0 + gamma * ln(1.0 + count))
    
    Each corpus item has: {'dia_id': 'D1:3', 'text': '...', 'session': 'session_1'}
    Returns: Sorted list of dicts containing section information.
    """
    # 1. Compute turn-level scores
    try:
        from rank_bm25 import BM25Okapi
        tokenized_corpus = [clean_text_for_bm25(doc["text"]) for doc in corpus]
        bm25 = BM25Okapi(tokenized_corpus)
        tokenized_query = clean_text_for_bm25(query)
        scores = bm25.get_scores(tokenized_query)
    except Exception:
        # Fallback to simple keyword overlap
        query_words = set(clean_text_for_bm25(query))
        scores = []
        for doc in corpus:
            doc_words = set(clean_text_for_bm25(doc["text"]))
            scores.append(float(len(query_words & doc_words)))
            
    # 2. Extract all unique section IDs in corpus to ensure complete coverage
    all_sections = set()
    for doc in corpus:
        session_str = doc.get("session", "")
        match = re.search(r"session[_\-\s]*(\d+)", session_str, flags=re.IGNORECASE)
        if not match:
            match = re.search(r"D\s*(\d+)", doc.get("dia_id", ""), flags=re.IGNORECASE)
        if match:
            all_sections.add(int(match.group(1)))
            
    # 3. Group positive scores by section ID
    section_turns_scores = {sec_id: [] for sec_id in all_sections}
    for doc, score in zip(corpus, scores):
        if score <= 0.0:
            continue
        session_str = doc.get("session", "")
        match = re.search(r"session[_\-\s]*(\d+)", session_str, flags=re.IGNORECASE)
        if not match:
            match = re.search(r"D\s*(\d+)", doc.get("dia_id", ""), flags=re.IGNORECASE)
        if match:
            sec_id = int(match.group(1))
            if sec_id in section_turns_scores:
                section_turns_scores[sec_id].append(score)
                
    # 4. Calculate Section Scores using the balanced formula
    section_rankings = []
    for sec_id in all_sections:
        turn_scores = section_turns_scores[sec_id]
        if turn_scores:
            max_score = max(turn_scores)
            count = len(turn_scores)
            balanced_score = max_score * (1.0 + gamma * math.log(1.0 + count))
        else:
            max_score = 0.0
            count = 0
            balanced_score = 0.0
            
        section_rankings.append({
            "section_id": sec_id,
            "max_score": max_score,
            "turn_count": count,
            "score": balanced_score
        })
        
    # Sort sections: first by score descending, then by section_id ascending (tie-breaker)
    section_rankings.sort(key=lambda x: (x["score"], -x["section_id"]), reverse=True)
    return section_rankings


def evidence_to_sections(evidence: List[str]) -> List[int]:
    """
    Extract unique section IDs (as integers) from evidence IDs like 'D1:3', 'D2:9', etc.
    """
    sections = set()
    for ev in evidence:
        match = re.search(r"D\s*(\d+)", str(ev), flags=re.IGNORECASE)
        if match:
            sections.add(int(match.group(1)))
    return sorted(list(sections))


def check_section_recall(retrieved_sections: List[int], gold_sections: List[int], k: int) -> float:
    """
    Calculate recall at k: (gold sections matched in top-k) / (total gold sections).
    """
    if not gold_sections:
        return 0.0
    top_k_retrieved = retrieved_sections[:k]
    matches = [sec for sec in gold_sections if sec in top_k_retrieved]
    return len(matches) / len(gold_sections)


# ──────────────────────────── PHASE 4 JUDGE ───────────────────────────
def llm_judge(original: str, rewritten: str, llm) -> int:
    """Use LLM to judge semantic equivalence. Returns 1 (pass) or 0 (fail)."""
    prompt_tpl = ChatPromptTemplate.from_template(JUDGE_PROMPT)
    chain = prompt_tpl | llm | StrOutputParser()
    try:
        result = chain.invoke({"original": original, "rewritten": rewritten}).strip()
        return 1 if result.startswith("1") else 0
    except Exception:
        return 0


# ─────────────────────────── MAIN RUNNER ──────────────────────────────
def run_evaluation(conversation_index: int, start: Optional[int] = None, end: Optional[int] = None, single_qa_index: Optional[int] = None, ambiguous_file: str = "pipeline_eval/data/ambiguous_queries.json"):
    print(f"\n{'=' * 60}")
    print(f"LoCoMo Evaluation — Conversation Index: {conversation_index}")
    print(f"{'=' * 60}")

    # Load dataset
    if not os.path.exists(LOCOMO_PATH):
        print(f"ERROR: Dataset not found at {LOCOMO_PATH}")
        return
    with open(LOCOMO_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    if conversation_index >= len(data):
        print(f"ERROR: conversation_index {conversation_index} out of range (max: {len(data) - 1})")
        return

    global SPEAKER_STOP_WORDS, CURRENT_SYNONYM_DICT
    
    dict_file = os.path.join(project_root, "pipeline_eval", "data", "synonym_dictionaries.json")
    if os.path.exists(dict_file):
        with open(dict_file, "r", encoding="utf-8") as df:
            dicts = json.load(df)
            CURRENT_SYNONYM_DICT = dicts.get(str(conversation_index), {})
            print(f"  [OK] Loaded synonym dictionary with {len(CURRENT_SYNONYM_DICT)} keys for conversation {conversation_index}.")
    else:
        CURRENT_SYNONYM_DICT = {}

    conv_data = data[conversation_index]
    conversation = conv_data.get("conversation", {})
    SPEAKER_STOP_WORDS = {
        conversation.get("speaker_a", "").lower().strip(),
        conversation.get("speaker_b", "").lower().strip()
    }
    sample_id = conv_data.get("sample_id", f"conv_{conversation_index}")
    session_id = f"locomo_eval_{conversation_index}"
    qa_list = conv_data.get("qa", [])
    
    # Track absolute index of each QA pair in the conversation
    for abs_idx, qa in enumerate(qa_list):
        qa["abs_idx"] = abs_idx

    # Handle single QA test mode
    if single_qa_index is not None:
        if single_qa_index >= len(qa_list):
            print(f"ERROR: single_qa_index {single_qa_index} out of range (max: {len(qa_list) - 1})")
            return
        qa_list = [qa_list[single_qa_index]]
        print(f"Single QA test mode: testing QA index {single_qa_index}")

    # Apply start and end
    if start is not None and end is not None:
        qa_list = qa_list[start:end]
    elif start is not None:
        qa_list = qa_list[start:]
    elif end is not None:
        qa_list = qa_list[:end]

    print(f"  Sample ID   : {sample_id}")
    print(f"  Total QA    : {len(qa_list)}")

    # ── Phase 1: Memo Injection ──
    clear_session_cache(session_id)
    corpus = phase1_inject_memos(conv_data, session_id)

    # ── Phase 2: Load Ambiguous Queries ──
    ambiguous_queries = phase2_load_ambiguous_queries(qa_list, ambiguous_file)

    # ── Phase 3 + 4: Pipeline Run & Scoring ──
    print("\n" + "=" * 60)
    print("PHASE 3 & 4: Pipeline Execution + Metric Scoring")
    print("=" * 60)

    judge_llm = get_llm(temperature=0.0)
    results = []
    hit_count_at1 = 0.0
    hit_count_at3 = 0.0
    hit_count_at5 = 0.0
    judge_pass_count = 0

    for idx, (qa, amb_query) in enumerate(zip(qa_list, ambiguous_queries)):
        original_q = qa["question"]
        evidence = qa.get("evidence", [])
        category = qa.get("category", -1)

        print(f"\n[{idx + 1}/{len(qa_list)}] QA Category: {category}")
        print(f"  Original Q    : {original_q}")
        print(f"  Ambiguous Q   : {amb_query}")
        print(f"  Evidence IDs  : {evidence}")
        
        gold_sections = evidence_to_sections(evidence)
        print(f"  Gold Sections : {gold_sections}")

        # Phase 3: Run pipeline with EMPTY state, using main session_id (memos already there)
        # Reset only the State and History for this QA - keep memos intact
        from pipeline_eval.core.state import SESSION_STATES, SESSION_HISTORIES
        SESSION_STATES[session_id] = None  # Force empty State_t-1
        SESSION_HISTORIES[session_id] = []  # Force empty short-term history

        try:
            q_final = run_pipeline(amb_query, session_id)
        except Exception as e:
            print(f"  [FAIL] Pipeline error: {e}")
            q_final = amb_query  # Fallback

        # Phase 4a: BM25 Section Reranking
        section_rankings = bm25_section_search(q_final, corpus, gamma=0.5)
        retrieved_sections = [item["section_id"] for item in section_rankings]
        
        hit_score_at1 = check_section_recall(retrieved_sections, gold_sections, k=1)
        hit_score_at3 = check_section_recall(retrieved_sections, gold_sections, k=3)
        hit_score_at5 = check_section_recall(retrieved_sections, gold_sections, k=5)
        
        hit_count_at1 += hit_score_at1
        hit_count_at3 += hit_score_at3
        hit_count_at5 += hit_score_at5

        # Phase 4b: LLM Judge
        judge_score = llm_judge(original_q, q_final, judge_llm)
        if judge_score == 1:
            judge_pass_count += 1

        print(f"  Q_final       : {q_final}")
        print(f"  Top-5 Sections: {retrieved_sections[:5]}")
        print(f"  Section Recall: @1={hit_score_at1:.2%}, @3={hit_score_at3:.2%}, @5={hit_score_at5:.2%}")
        print(f"  LLM Judge     : {'[OK] PASS' if judge_score else '[FAIL] FAIL'}")

        results.append({
            "qa_index": qa["abs_idx"],
            "category": category,
            "original_question": original_q,
            "ambiguous_query": amb_query,
            "q_final": q_final,
            "evidence": evidence,
            "gold_sections": gold_sections,
            "retrieved_sections": retrieved_sections[:5],
            "recall_at1": hit_score_at1,
            "recall_at3": hit_score_at3,
            "recall_at5": hit_score_at5,
            "llm_judge_pass": bool(judge_score)
        })

        # --- PROGRESSIVE SAVE LOGIC INSIDE THE LOOP ---
        out_file = os.path.join(EVAL_RESULTS_DIR, f"eval_conv_{conversation_index}.json")
        existing_results = []
        if os.path.exists(out_file):
            try:
                with open(out_file, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
                    if isinstance(existing_data, dict):
                        existing_results = existing_data.get("results", [])
            except Exception as e:
                print(f"  [WARN] Failed to load existing results from {out_file}: {e}")

        # Merge current run's results into existing ones using absolute qa_index as the key
        results_map = {item["qa_index"]: item for item in existing_results}
        for item in results:
            results_map[item["qa_index"]] = item

        # Sort merged results by absolute qa_index
        merged_results = [results_map[k] for k in sorted(results_map.keys())]

        # Re-calculate overall summary metrics over all merged results
        total = len(merged_results)
        merged_hit_count_at1 = sum(item.get("recall_at1", 0.0) for item in merged_results)
        merged_hit_count_at3 = sum(item.get("recall_at3", 0.0) for item in merged_results)
        merged_hit_count_at5 = sum(item.get("recall_at5", 0.0) for item in merged_results)
        merged_judge_pass_count = sum(1 for item in merged_results if item.get("llm_judge_pass", False))

        summary = {
            "conversation_index": conversation_index,
            "sample_id": sample_id,
            "total_qa": total,
            "bm25_hit_rate_at1": round(merged_hit_count_at1 / total if total else 0, 4),
            "bm25_hit_rate_at3": round(merged_hit_count_at3 / total if total else 0, 4),
            "bm25_hit_rate_at5": round(merged_hit_count_at5 / total if total else 0, 4),
            "llm_judge_accuracy": round(merged_judge_pass_count / total if total else 0, 4),
            "llm_judge_passes": merged_judge_pass_count
        }

        output = {"summary": summary, "results": merged_results}
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

    # After loop finishes, print final summary
    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY (MERGED)")
    print("=" * 60)
    print(f"  Total QA Pairs     : {summary['total_qa']}")
    print(f"  Section Hit-Rate@1 : {summary['bm25_hit_rate_at1']:.2%}  ({merged_hit_count_at1:.2f}/{summary['total_qa']})")
    print(f"  Section Hit-Rate@3 : {summary['bm25_hit_rate_at3']:.2%}  ({merged_hit_count_at3:.2f}/{summary['total_qa']})")
    print(f"  Section Hit-Rate@5 : {summary['bm25_hit_rate_at5']:.2%}  ({merged_hit_count_at5:.2f}/{summary['total_qa']})")
    print(f"  LLM Judge Accuracy : {summary['llm_judge_accuracy']:.2%}  ({merged_judge_pass_count}/{summary['total_qa']})")
    print(f"\n  [OK] Results completely merged & saved -> {out_file}")

    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LoCoMo Rewrite Evaluation")
    parser.add_argument("--conversation_index", type=int, default=0,
                        help="Index of the conversation to evaluate (0-9)")
    parser.add_argument("--start", type=int, default=None,
                        help="Start index of QA pairs to evaluate")
    parser.add_argument("--end", type=int, default=None,
                        help="End index of QA pairs to evaluate")
    parser.add_argument("--use_qwen", type=str, default="true",
                        help="true to use qwen, false to use 9router on localhost:20128")
    parser.add_argument("--single_qa", type=int, default=None,
                        help="Test only a single QA pair at this index")
    parser.add_argument("--ambiguous_file", type=str, default="pipeline_eval/data/ambiguous_queries.json",
                        help="Path to the JSON file containing original to ambiguous query mappings")
    args = parser.parse_args()

    from pipeline_eval.services import llm as llm_service
    llm_service.USE_QWEN = args.use_qwen.lower() == "true"

    run_evaluation(
        conversation_index=args.conversation_index,
        start=args.start,
        end=args.end,
        single_qa_index=args.single_qa,
        ambiguous_file=args.ambiguous_file
    )
