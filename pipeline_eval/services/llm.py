import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

def get_llm(temperature: float = 0.0):
    """
    Initialize and return the appropriate LLM client.
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        return ChatOpenAI(model="gpt-4o-mini", temperature=temperature)
    
    return ChatOllama(model="qwen2.5:3b", temperature=temperature)


# =====================================================================
# ENGLISH PROMPTS FOR EVALUATION
# =====================================================================

# 1. Boundary Detection (HingeMem fallback)
FALLBACK_PROMPT = """[ROLE] You are a dialogue flow monitor for a conversational assistant.
[TASK] Based on the recent chat history and the new query, determine if the user is continuing the current topic or shifting to a completely different topic.

[RECENT CHAT HISTORY]
{context}

[NEW QUERY]
{query}

[CLASSIFICATION RULES - READ CAREFULLY]
1. ALWAYS return "continue" if the new query contains referring pronouns ("it", "they", "them", "that", "this", "he", "she", "his", "her", "these", "those") pointing to the existing context, as this indicates continuation.
2. ALWAYS return "continue" if the new query asks for details, clarification, or a different aspect of the object/topic under discussion.
3. Return "hard_shift" ONLY when the new query introduces a COMPLETELY NEW topic that has no semantic or lexical connection to the recent history.

[STRICT OUTPUT FORMAT]
You must reply with exactly one of the following two words, with no explanation or other text:
- hard_shift
- continue
[RESULT]:"""

# Entity Extraction for Boundary Heuristic
ENTITY_EXTRACTION_PROMPT = """[ROLE] You are a fast NLP Entity Extractor.
[TASK] Extract the key entities (people, places, objects, specific topics) from the given text.
[TEXT] {text}
[FORMAT] Return ONLY a comma-separated list of entities. If none are found, return "None". Do NOT explain.
[OUTPUT]:"""



# 2. State Tracker + Checker
TRACKER_PROMPT = """[ROLE] You are an AI State Tracker for a conversational assistant.
[TASK] Synthesize information from the old state (State_t-1) and the new query to produce the most complete new state (State_t).

[OLD STATE (State_t-1)]
{old_state}

[USER'S NEW QUERY]
{query}

[OPERATIONAL PRINCIPLES]
Follow these 2 steps in order:

STEP 1 - TRACKING (State Update):
- If the old state contains "entities" (e.g., {{"person": "Caroline"}}), you MUST keep those entities in the new State_t, merging them with any new entities extracted from the New Query.
- Extract new "intent", "entities", "attributes", "constraints" from the New Query.
- Fill in "unresolved_references" if the New Query contains referring pronouns ("it", "they", "them", "that", "this", "he", "she", "his", "her", "these", "those", "here", "there", "then"...) — only add them if they ACTUALLY APPEAR in the query text.

STEP 2 - CHECKING (Completeness Check):
- After updating, check the new State_t: is the "entities" dictionary empty {{}}?
- Set "need_retrieval" = true: IF and ONLY IF "entities" is empty {{}} after merging. This means the pipeline does not know what entity/subject is being discussed and must retrieve memos.
- Set "need_retrieval" = false: IF "entities" has at least 1 entry (even if the query uses a pronoun, if the old state has entities, they are merged, so entities is not empty).

[VÍ DỤ 1 — Continue + Clear query (no pronouns)]
State_t-1: {{"intent": "inquiry", "entities": {{}}, "attributes": {{}}, "constraints": [], "unresolved_references": []}}
New Query: "What is astrophysics?"
→ Tracking: new entities = {{"subject": "astrophysics"}}
→ Checking: entities not empty → need_retrieval = false
JSON Output:
{{
  "state": {{"intent": "inquiry", "entities": {{"subject": "astrophysics"}}, "attributes": {{}}, "constraints": [], "unresolved_references": []}},
  "need_retrieval": false,
  "confidence": 1.0
}}

[VÍ DỤ 2 — Continue + Query uses pronoun "it" + State_t-1 has entities]
State_t-1: {{"intent": "inquiry", "entities": {{"subject": "astrophysics"}}, "attributes": {{}}, "constraints": [], "unresolved_references": []}}
New Query: "Why is it so interesting?"
→ Tracking: MERGE entities from State_t-1 → entities = {{"subject": "astrophysics"}}, add attributes = {{"property": "interesting"}}, unresolved_references = ["it"] (since "it" appears in the query)
→ Checking: entities not empty (has "astrophysics" merged from old state) → need_retrieval = false
JSON Output:
{{
  "state": {{"intent": "inquiry", "entities": {{"subject": "astrophysics"}}, "attributes": {{"property": "interesting"}}, "constraints": [], "unresolved_references": ["it"]}},
  "need_retrieval": false,
  "confidence": 1.0
}}

[VÍ DỤ 3 — Hard shift happened (State_t-1 empty) + Query uses pronoun "it"]
State_t-1: {{"intent": "inquiry", "entities": {{}}, "attributes": {{}}, "constraints": [], "unresolved_references": []}}
New Query: "Why is it so interesting?"
→ Tracking: State_t-1 has no entities. Query doesn't name any entity. entities = {{}}, unresolved_references = ["it"]
→ Checking: entities empty → need_retrieval = true (must search memos to resolve what "it" refers to)
JSON Output:
{{
  "state": {{"intent": "inquiry", "entities": {{}}, "attributes": {{"property": "interesting"}}, "constraints": [], "unresolved_references": ["it"]}},
  "need_retrieval": true,
  "confidence": 0.8
}}

[STRICT OUTPUT FORMAT]
- RETURN ONLY A VALID JSON BLOCK.
- DO NOT use markdown fences (no ```json ... ```).
- NO extra text outside the JSON.
[JSON RESULT]:"""


# 3. Controlled Rewrite
REWRITE_PROMPT = """[ROLE] You are a query reformulation expert.
[TASK] Based on the current conversation state and any retrieved long-term memories (memos), rewrite the user's raw query into a Standalone Query (Q_final) that can be executed independently against a search index.

[CURRENT CONVERSATION STATE]
- Entities: {entities}
- Attributes: {attributes}
- Constraints: {constraints}

[RETRIEVED MEMOS (Long-term Context)]
{memos}

[USER'S RAW QUERY]
{query}

[STRICT REQUIREMENTS]
1. FULL SEMANTICS: Replace all referring pronouns ("it", "they", "them", "that", "this", "he", "she", "his", "her", "these", "those") with the SPECIFIC Entity Name from the [State] or [Retrieved Memos]. The rewritten query must stand on its own without any conversational history.
2. PRESERVE ENTITY NAMES: DO NOT replace specific entity names with generic category names. Keep the exact names.
3. USE MEMOS IF NEEDED: If the state is empty but the Memos provide the missing context, use the Memos to resolve pronouns.
4. DO NOT ANSWER: Your only job is to rewrite the query. Do not answer it.
5. FORMAT: Return ONLY the rewritten query. No greetings, no explanations.
[STANDALONE QUERY]:"""


# 4. Answer Generation (if needed for end-to-end evaluation)
ANSWER_PROMPT = """You are a helpful conversational assistant. Answer the user's question based on the provided context and history.

[CONTEXT]
{context}

[CHAT HISTORY]
{chat_history}

[USER QUESTION]
{query}

Provide a concise, direct answer based on the context. If the context doesn't contain the answer, say "I cannot find this information in the provided context."
"""
