from typing import TypedDict, List, Optional, Dict, Any

class QuestionState(TypedDict):
    # INPUT FIELDS
    topic: str
    subtopic: str
    difficulty: str
    paper: str
    question_type: str
    
    # GENERATED FIELDS
    research_context: Optional[str]
    pyq_context: Optional[str]
    question_stem: Optional[str]
    correct_answer: Optional[str]
    distractors: Optional[List[str]]
    explanation: Optional[str]
    mains_fact: Optional[str]
    formatted_question: Optional[Dict[str, Any]]
    tags: Optional[List[str]]
    difficulty_score: Optional[float]
    estimated_time_seconds: Optional[int]
    
    # QA FIELDS
    qa_score: Optional[float]
    qa_flags: Optional[List[str]]
    retry_count: int
    approved: bool
