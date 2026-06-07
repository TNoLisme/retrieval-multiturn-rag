from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class ConversationState(BaseModel):
    intent: str = Field(default="inquiry", description="The user's intent (inquiry, compare, list...)")
    entities: List[str] = Field(default_factory=list, description="All entities mentioned in the chat (people, places, objects, events, etc.). This field determines need_retrieval.")
    attributes: List[str] = Field(default_factory=list, description="Properties, characteristics, colors, and time mentioned inside the conversation for the entities.")
    unresolved_references: List[str] = Field(default_factory=list, description="Referring pronouns ('it', 'they', 'that'...) ACTUALLY APPEARING in the new query. This is for reference tracking and does NOT determine need_retrieval directly. Empty [] if none.")

class TrackerOutput(BaseModel):
    state: ConversationState
    need_retrieval: bool = Field(
        description="True IF AND ONLY IF state.entities is empty [] after the Tracker merges State_t-1 + Query_t. "
                    "This means the pipeline does not know what entity/subject is being discussed and must search the Memo DB. "
                    "False if state.entities contains at least 1 entry."
    )
    confidence: float
