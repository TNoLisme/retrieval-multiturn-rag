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

        # Extract named entities (people) and their events from the block
        entities_extracted = {}
        summary_parts = []
        if event_block:
            date_str = event_block.get("date", "")
            if date_str:
                summary_parts.append(f"Date: {date_str}.")
            for person, events in event_block.items():
                if person == "date":
                    continue
                if isinstance(events, list) and events:
                    entities_extracted["person"] = person   # use last person as primary entity
                    events_str = " ".join(events)
                    summary_parts.append(f"{person}: {events_str}")
        summary_text = " ".join(summary_parts)

        # Fallback: concatenate first 3 turns if event_summary is empty
        if not summary_text:
            summary_text = " | ".join([t["content"] for t in history[:3]])

        # Inject into in-memory Memo DB
        add_memo_to_db(
            session_id=session_id,
            summary=summary_text,
            topic=f"Session {session_num}",
            entities=entities_extracted,
            attributes={},
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
def phase2_batch_ambiguate(qa_list: List[Dict], batch_size: int = 60) -> List[str]:
    """
    Send all QA questions to Qwen 2.5 3B in batches, get ambiguous (pronoun-replaced) queries.
    Returns a list of ambiguous queries in the same order as qa_list.
    """
    print("\n" + "=" * 60)
    print("PHASE 2: Batch Ambiguous Query Generation (Qwen 2.5 3B)")
    print("=" * 60)

    questions = [qa["question"] for qa in qa_list]
    total = len(questions)
    ambiguous_queries = []

    llm = get_llm(temperature=0.0)
    prompt_tpl = ChatPromptTemplate.from_template(AMBIGUATOR_PROMPT)
    chain = prompt_tpl | llm | StrOutputParser()

    num_batches = math.ceil(total / batch_size)
    for batch_idx in range(num_batches):
        batch = questions[batch_idx * batch_size:(batch_idx + 1) * batch_size]
        print(f"  Batch {batch_idx + 1}/{num_batches}: {len(batch)} questions...")

        questions_json = json.dumps(batch, ensure_ascii=False)
        try:
            raw = chain.invoke({"questions_json": questions_json}).strip()
            # Strip markdown fences if present
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw).strip()
            # Fix trailing comma before ] (common Qwen quirk)
            raw = re.sub(r",\s*]", "]", raw)
            # Fix trailing comma before }
            raw = re.sub(r",\s*}", "}", raw)
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                if len(parsed) == len(batch):
                    ambiguous_queries.extend(parsed)
                    print(f"    [OK] Generated {len(parsed)} ambiguous queries.")
                elif len(parsed) > 0:
                    # Partial results - pad with originals if short
                    print(f"    [WARN] Got {len(parsed)} results for {len(batch)} questions. Padding with originals.")
                    padded = parsed + batch[len(parsed):]
                    ambiguous_queries.extend(padded)
                else:
                    print(f"    [WARN] Empty list returned. Using original questions.")
                    ambiguous_queries.extend(batch)
            else:
                print(f"    [WARN] Unexpected output type. Falling back to original questions.")
                ambiguous_queries.extend(batch)
        except Exception as e:
            print(f"    [FAIL] Batch {batch_idx + 1} failed: {e}. Using original questions.")
            ambiguous_queries.extend(batch)

    print(f"  [OK] Total ambiguous queries ready: {len(ambiguous_queries)}")
    return ambiguous_queries


# ──────────────────────────── BM25 HELPER ─────────────────────────────
def bm25_search(query: str, corpus: List[Dict], top_k: int = 3) -> List[str]:
    """
    Simple BM25 search over corpus. Returns list of top_k dia_ids.
    Uses pure Python BM25 (no external lib required - falls back to TF-IDF).
    """
    try:
        from rank_bm25 import BM25Okapi
        tokenized_corpus = [doc["text"].lower().split() for doc in corpus]
        bm25 = BM25Okapi(tokenized_corpus)
        tokenized_query = query.lower().split()
        scores = bm25.get_scores(tokenized_query)
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        return [corpus[i]["dia_id"] for i in top_indices]
    except ImportError:
        # Fallback: simple keyword overlap scoring
        query_words = set(query.lower().split())
        scored = []
        for doc in corpus:
            doc_words = set(doc["text"].lower().split())
            score = len(query_words & doc_words)
            scored.append((doc["dia_id"], score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [d[0] for d in scored[:top_k]]


def check_hit(retrieved_dia_ids: List[str], evidence: List[str]) -> bool:
    """Check if any evidence dia_id is in the top-k retrieved dia_ids."""
    return any(ev in retrieved_dia_ids for ev in evidence)


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
def run_evaluation(conversation_index: int, limit: Optional[int] = None, single_qa_index: Optional[int] = None):
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

    conv_data = data[conversation_index]
    sample_id = conv_data.get("sample_id", f"conv_{conversation_index}")
    session_id = f"locomo_eval_{conversation_index}"
    qa_list = conv_data.get("qa", [])

    # Handle single QA test mode
    if single_qa_index is not None:
        if single_qa_index >= len(qa_list):
            print(f"ERROR: single_qa_index {single_qa_index} out of range (max: {len(qa_list) - 1})")
            return
        qa_list = [qa_list[single_qa_index]]
        print(f"Single QA test mode: testing QA index {single_qa_index}")

    # Apply limit
    if limit is not None:
        qa_list = qa_list[:limit]

    print(f"  Sample ID   : {sample_id}")
    print(f"  Total QA    : {len(qa_list)}")

    # ── Phase 1: Memo Injection ──
    clear_session_cache(session_id)
    corpus = phase1_inject_memos(conv_data, session_id)

    # ── Phase 2: Batch Ambiguation ──
    ambiguous_queries = phase2_batch_ambiguate(qa_list)

    # ── Phase 3 + 4: Pipeline Run & Scoring ──
    print("\n" + "=" * 60)
    print("PHASE 3 & 4: Pipeline Execution + Metric Scoring")
    print("=" * 60)

    judge_llm = get_llm(temperature=0.0)
    results = []
    hit_count = 0
    judge_pass_count = 0

    for idx, (qa, amb_query) in enumerate(zip(qa_list, ambiguous_queries)):
        original_q = qa["question"]
        evidence = qa.get("evidence", [])
        category = qa.get("category", -1)

        print(f"\n[{idx + 1}/{len(qa_list)}] QA Category: {category}")
        print(f"  Original Q    : {original_q}")
        print(f"  Ambiguous Q   : {amb_query}")
        print(f"  Evidence IDs  : {evidence}")

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

        # Phase 4a: BM25 Hit Rate
        top_k_ids = bm25_search(q_final, corpus, top_k=3)
        hit = check_hit(top_k_ids, evidence)
        if hit:
            hit_count += 1

        # Phase 4b: LLM Judge
        judge_score = llm_judge(original_q, q_final, judge_llm)
        if judge_score == 1:
            judge_pass_count += 1

        print(f"  Q_final       : {q_final}")
        print(f"  BM25 Top-3    : {top_k_ids}  ->  Hit: {'[OK]' if hit else '[FAIL]'}")
        print(f"  LLM Judge     : {'[OK] PASS' if judge_score else '[FAIL] FAIL'}")

        results.append({
            "qa_index": idx,
            "category": category,
            "original_question": original_q,
            "ambiguous_query": amb_query,
            "q_final": q_final,
            "evidence": evidence,
            "bm25_top3_ids": top_k_ids,
            "bm25_hit": hit,
            "llm_judge_pass": bool(judge_score)
        })

    # ── Summary ──
    total = len(results)
    hit_rate = hit_count / total if total else 0
    judge_accuracy = judge_pass_count / total if total else 0

    summary = {
        "conversation_index": conversation_index,
        "sample_id": sample_id,
        "total_qa": total,
        "bm25_hit_rate": round(hit_rate, 4),
        "llm_judge_accuracy": round(judge_accuracy, 4),
        "bm25_hits": hit_count,
        "llm_judge_passes": judge_pass_count
    }

    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)
    print(f"  Total QA Pairs     : {total}")
    print(f"  BM25 Hit-Rate @3   : {hit_rate:.2%}  ({hit_count}/{total})")
    print(f"  LLM Judge Accuracy : {judge_accuracy:.2%}  ({judge_pass_count}/{total})")

    # Save results
    out_file = os.path.join(EVAL_RESULTS_DIR, f"eval_conv_{conversation_index}.json")
    output = {"summary": summary, "results": results}
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n  [OK] Results saved -> {out_file}")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LoCoMo Rewrite Evaluation")
    parser.add_argument("--conversation_index", type=int, default=0,
                        help="Index of the conversation to evaluate (0-9)")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit number of QA pairs to evaluate")
    parser.add_argument("--single_qa", type=int, default=None,
                        help="Test only a single QA pair at this index")
    args = parser.parse_args()

    run_evaluation(
        conversation_index=args.conversation_index,
        limit=args.limit,
        single_qa_index=args.single_qa
    )
