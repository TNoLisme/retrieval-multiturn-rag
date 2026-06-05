# -*- coding: utf-8 -*-
"""
LoCoMo Automated Evaluation Script for the Query Rewriter Pipeline
Runs within the isolated pipeline_eval folder environment.
"""
import sys
import os
import json
import io
import re

# Ensure terminal output supports UTF-8 for Vietnamese/general unicode logs
if sys.platform.startswith('win'):
    os.system('chcp 65001 > nul')
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from pipeline_eval.core.pipeline import run_pipeline
from pipeline_eval.core.state import save_history, clear_session_cache, save_state_to_redis
from pipeline_eval.core.schema import ConversationState

# List of pronouns to scan for to find interesting multi-turn evaluation cases
ENGLISH_REFERRING_PRONOUNS = {"it", "they", "them", "that", "this", "these", "those", "she", "he"}

def clean_text(text: str) -> str:
    return text.strip()

def contains_pronoun(text: str) -> bool:
    words = set(re.sub(r'[^\w\s]', ' ', text.lower()).split())
    return not words.isdisjoint(ENGLISH_REFERRING_PRONOUNS)

def run_locomo_evaluation(limit_cases=20):
    print("=" * 80)
    # Correct path to locomo10.json
    locomo_data_path = os.path.join(project_root, "locomo", "data", "locomo10.json")
    
    if not os.path.exists(locomo_data_path):
        print(f"ERROR: LoCoMo dataset not found at '{locomo_data_path}'")
        return
        
    print(f"Loading LoCoMo dataset from: {locomo_data_path}")
    with open(locomo_data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    print(f"Successfully loaded {len(data)} conversations from LoCoMo.")
    
    eval_cases = []
    cases_run = 0
    
    # Scan conversations for turns containing referring pronouns
    for conv_idx, conv_data in enumerate(data):
        if cases_run >= limit_cases:
            break
            
        sample_id = conv_data["sample_id"]
        conversation = conv_data["conversation"]
        
        # Get session keys in chronological order
        session_keys = sorted(
            [k for k in conversation.keys() if k.startswith("session_") and not k.endswith("_date_time")],
            key=lambda x: int(x.split("_")[-1])
        )
        
        for session_key in session_keys:
            if cases_run >= limit_cases:
                break
                
            turns = conversation[session_key]
            
            # We need at least 3 turns to have a context (2 preceding turns + 1 current turn)
            for i in range(2, len(turns)):
                if cases_run >= limit_cases:
                    break
                    
                current_turn = turns[i]
                current_text = current_turn["text"]
                
                # Check if current turn contains a referring pronoun
                if contains_pronoun(current_text) and len(current_text.split()) > 4:
                    # Construct context from preceding 2 turns
                    prev_turn_1 = turns[i-2]
                    prev_turn_2 = turns[i-1]
                    
                    context = [
                        {"role": "user" if i % 2 == 0 else "assistant", "content": prev_turn_1["text"]},
                        {"role": "assistant" if i % 2 == 0 else "user", "content": prev_turn_2["text"]}
                    ]
                    
                    # Simulating entity extraction for the context to mock state_t-1
                    # In a real conversation, the entities would be tracked from Turn 1.
                    # We will extract entities using a simple heuristic from the context for testing.
                    inferred_entities = {}
                    
                    # Look for potential key subjects in context to populate State_t-1
                    context_full_text = (prev_turn_1["text"] + " " + prev_turn_2["text"]).lower()
                    if "astrophysics" in context_full_text or "physics" in context_full_text:
                        inferred_entities["subject"] = "astrophysics"
                    if "black holes" in context_full_text:
                        inferred_entities["concept"] = "black holes"
                    if "quantum computing" in context_full_text or "computer" in context_full_text:
                        inferred_entities["technology"] = "quantum computing"
                    if "puzzle" in context_full_text:
                        inferred_entities["hobby"] = "puzzles"
                    if "coin" in context_full_text or "stamp" in context_full_text:
                        inferred_entities["hobby"] = "coins and stamps collecting"
                    if "clair de lune" in context_full_text or "piano" in context_full_text:
                        inferred_entities["music"] = "Clair de Lune"
                    if "sky map" in context_full_text or "star map" in context_full_text:
                        inferred_entities["item"] = "vintage sky map"
                        
                    eval_cases.append({
                        "id": f"{sample_id}_{session_key}_turn_{i}",
                        "context": context,
                        "query_t": current_text,
                        "inferred_entities": inferred_entities
                    })
                    cases_run += 1
                    
    print(f"\nExtracted {len(eval_cases)} pronoun evaluation cases from LoCoMo dialogues.")
    print("=" * 80)
    print("RUNNING REWRITE PIPELINE ON LOCOMO CASES...")
    print("=" * 80)
    
    results = []
    
    for idx, case in enumerate(eval_cases):
        case_id = case["id"]
        query_t = case["query_t"]
        context = case["context"]
        inferred_entities = case["inferred_entities"]
        
        print(f"\n[{idx+1}/{len(eval_cases)}] Case: {case_id}")
        
        # 1. Reset pipeline session
        session_id = f"eval_{case_id}"
        clear_session_cache(session_id)
        
        # 2. Pre-populate history
        for turn in context:
            save_history(session_id, turn["content"])
            
        # 3. Pre-populate old state with inferred entities
        state_t_minus_1 = ConversationState(entities=inferred_entities)
        save_state_to_redis(session_id, state_t_minus_1)
        
        # 4. Run pipeline
        try:
            q_final = run_pipeline(query_t, session_id)
            
            results.append({
                "case_id": case_id,
                "context": context,
                "inferred_state_t_minus_1": inferred_entities,
                "query_t": query_t,
                "q_final": q_final
            })
        except Exception as e:
            print(f"ERROR executing case {case_id}: {e}")
            results.append({
                "case_id": case_id,
                "error": str(e)
            })
            
    # Write results to outputs folder
    output_dir = os.path.join(project_root, "outputs")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "locomo_eval_results.json")
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        
    print("\n" + "=" * 80)
    print(f"EVALUATION COMPLETE. Results saved to: {output_file}")
    print("=" * 80)

if __name__ == "__main__":
    run_locomo_evaluation()
