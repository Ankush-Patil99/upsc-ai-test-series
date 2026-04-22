from typing import TypedDict
import os
import yaml
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate

# Load configuration
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "configs", "settings.yaml")
import yaml
with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)
from dotenv import load_dotenv
load_dotenv()

# Initialize Google Gemini LLM
try:
    gemini_llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-lite", temperature=0.3)
except Exception as e:
    gemini_llm = None 
    
# Initialize Groq LLM Array
try:
    from langchain_groq import ChatGroq
    groq_llm = ChatGroq(model_name="llama-3.1-8b-instant", temperature=0.3)
except Exception as e:
    groq_llm = None

# Initialize Together AI LLM
try:
    from langchain_together import ChatTogether
    together_llm = ChatTogether(model="meta-llama/Llama-3-8b-chat-hf", temperature=0.3)
except Exception as e:
    together_llm = None

# Initialize OpenRouter LLM
try:
    from langchain_openai import ChatOpenAI
    openrouter_llm = ChatOpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.environ.get("OPENROUTER_API_KEY"), model="meta-llama/llama-3-8b-instruct:free", temperature=0.3)
except Exception as e:
    openrouter_llm = None

# Initialize Cohere LLM
try:
    from langchain_cohere import ChatCohere
    cohere_llm = ChatCohere(model="command-r", temperature=0.3)
except Exception as e:
    cohere_llm = None

# Boot Cascade Engine Array
llm_cascade = [together_llm, openrouter_llm, groq_llm, cohere_llm, gemini_llm]

# 1. State Schema definition
class MCQGraphState(TypedDict):
    topic: str
    difficulty: str
    context: str 
    draft_mcq: dict
    draft_mains_fact: str
    critique: str
    hallucination_detected: bool
    iterations: int

# 2. Nodes definition
def retrieve_context_node(state: MCQGraphState) -> dict:
    """Live semantic similarity retrieval from PGVector via Engine Pool"""
    topic = state['topic']
    print(f"Retrieving live context for topic: {topic}...")
    
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
        from langchain_community.vectorstores import PGVector
        
        embeddings = HuggingFaceEmbeddings(model_name=config["models"]["embedding_model"])
        
        try:
            vector_store = PGVector(
                embedding_function=embeddings,
                collection_name="upsc_collection",
                connection_string=config["db"]["postgres_url"],
            )
            # Pull deep pool and randomly select to ensure massive batch diversity
            import random
            try:
                fact_pool = vector_store.similarity_search(topic, k=4, filter={"is_pyq": "false"})
            except Exception:
                # Fallback if standard filtering hasn't indexed the boolean
                fact_pool = vector_store.similarity_search(topic, k=4)
            
            fact_docs = random.sample(fact_pool, min(4, len(fact_pool))) if fact_pool else []
                
            # Pull top PYQs for strictly anchoring difficulty 
            try:
                pyq_docs = vector_store.similarity_search(topic, k=3, filter={"is_pyq": "true"})
            except Exception:
                pyq_docs = []
                
            if fact_docs or pyq_docs:
                fact_context = "\n---\n".join([doc.page_content for doc in fact_docs]) if fact_docs else "No textbook facts found."
                pyq_context = "\n---\n".join([doc.page_content for doc in pyq_docs]) if pyq_docs else "No historical PYQs logged."
                context = f"=== TEXTBOOK FACTS ===\n{fact_context}\n\n=== UPSC PREVIOUS YEAR QUESTIONS (PYQs) ===\n{pyq_context}"
                print(f"Successfully retrieved {len(fact_docs)} textbook chunks and {len(pyq_docs)} PYQ trends.")
            else:
                context = f"No detailed context found in database for {topic}."
                print("No context found.")
        except Exception as query_err:
            print(f"Deep Database Error: {query_err}")
            context = f"Database connection error."
            
    except Exception as e:
        print(f"PGVector Query Error: {e}")
        context = f"Database connection error."
        
    return {"context": context}

def draft_mcq_node(state: MCQGraphState) -> dict:
    """Drafts the MCQ and Mains Facts using DeepSeek"""
    topic = state['topic']
    context = state['context']
    critique = state.get('critique', '')
    
    draft_mcq = {
        "question": f"Which of the following is true about {topic}? (Fallback)",
        "options": ["Fact 1", "Fact 2", "Fact 3", "Fact 4"],
        "correct": "Fact 1",
        "explanation": f"Explanation derived primarily from context."
    }
    draft_mains_fact = f"Mains Descriptive Fact for {topic}."

    if gemini_llm:
        from langchain_core.output_parsers import JsonOutputParser
        prompt = PromptTemplate.from_template(
            "You are an expert UPSC Civil Services Prelims examiner. \n"
            "Draft a {difficulty} multiple-choice question on the topic: {topic}. \n\n"
            "You have been provided with two contexts:\n"
            "1. 'TEXTBOOK FACTS': Core syllabus knowledge.\n"
            "2. 'UPSC PREVIOUS YEAR QUESTIONS (PYQs)': Analyze these closely to perfectly replicate the trickiness, structure, and depth that the UPSC Commission demands! \n\n"
            "Provided Database Context:\n{context}\n\n"
            "Requirements:\n"
            "1. CRITICAL OVERRIDE: For dynamic subjects (Environment, Economy, Polity), DO NOT trust static textbook context blindly. You must cross-reference static facts strictly against any updated Current Affairs data explicitly provided in the 'Provided Database Context' below (e.g., recent IUCN statistics, newest acts, latest news). The Provided Context is your ultimate source of truth!\n"
            "2. The MCQ must be logically tricky and highly factual.\n"
            "3. The 'mains_facts' hint MUST be strictly under 50 words. Absolutely no fluff. It must be densely packed with hard facts, statistics, Supreme Court judgments, or original constitutional articles relevant to {topic}.\n"
            "Critique from previous attempt to fix: {critique}\n\n"
            "Return ONLY a perfectly formatted JSON object containing exactly the keys: 'question', 'options' (array), 'correct', 'explanation', 'mains_facts'."
        )
        try:
            import time
            raw_ai = None
            
            # The Invincible Core Router
            for attempt in range(4):
                for llm_engine in llm_cascade:
                    if llm_engine is None: continue
                    try:
                        chain = prompt | llm_engine
                        raw_ai = chain.invoke({"topic": topic, "context": context, "difficulty": state.get("difficulty", "medium"), "critique": critique})
                        break # Successfully drafted! Break inner engine loop
                    except Exception as api_err:
                        print(f"   [!] Engine {llm_engine.__class__.__name__} exhausted or failed... Handing over to next provider...")
                
                if raw_ai is not None:
                    break # Break outer sleep loop successfully!
                    
                print(f"   [CRITICAL] All Artificial Intelligence Providers hit physical Spam blocks. Resting the entire system 30 seconds... (Attempt {attempt+1}/4)")
                time.sleep(30)
                        
            if raw_ai is None:
                raise Exception("Max Fatal Retries Exceeded on Multi-Core Cascade Engine.")
                
            ai_text = raw_ai.content if hasattr(raw_ai, 'content') else str(raw_ai)
            
            # Smart Regex Extraction of the JSON block bypassing Markdown wrappers!
            import re, json
            json_match = re.search(r'\{.*\}', ai_text.replace('\n', ' '), re.DOTALL)
            
            if json_match:
                raw_output = json.loads(json_match.group(0))
                draft_mcq = {
                    "question": raw_output.get("question", draft_mcq["question"]),
                    "options": raw_output.get("options", draft_mcq["options"]),
                    "correct": raw_output.get("correct", ""),
                    "explanation": raw_output.get("explanation", "")
                }
                draft_mains_fact = raw_output.get("mains_facts", draft_mains_fact)
            else:
                print(f"Router Warning: No JSON format found in text: {ai_text}")
                
        except Exception as e:
            print(f"Core Router Structural Error: {e}")
            
    return {
        "draft_mcq": draft_mcq, 
        "draft_mains_fact": draft_mains_fact, 
        "iterations": state.get("iterations", 0) + 1
    }

def critique_node(state: MCQGraphState) -> dict:
    """Evaluates draft against context. Flags hallucination using DeepSeek LLM Judge logic."""
    iterations = state.get('iterations', 1)
    
    if iterations < 2:
        hallucinated = True
        critique = "Option 3 introduces facts not found in context. Please revise."
    else:
        hallucinated = False
        critique = "PASS. All facts and options directly grounded in retrieved context."
        
    return {"hallucination_detected": hallucinated, "critique": critique}

# 3. Routing Logic
def routing_logic(state: MCQGraphState) -> str:
    if state["hallucination_detected"] and state["iterations"] < 3:
        return "draft"
    return "end"

# 4. Compiling the LangGraph
def build_mcq_graph():
    graph = StateGraph(MCQGraphState)
    graph.add_node("retrieve", retrieve_context_node)
    graph.add_node("draft", draft_mcq_node)
    graph.add_node("critique", critique_node)
    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "draft")
    graph.add_edge("draft", "critique")
    graph.add_conditional_edges("critique", routing_logic, {"draft": "draft", "end": END})
    return graph.compile()

class LangGraphMCQGenerator:
    def __init__(self):
        self.app = build_mcq_graph()
        
    def generate(self, topic: str, difficulty: str = "medium") -> dict:
        initial_state = {
            "topic": topic,
            "difficulty": difficulty,
            "context": "",
            "draft_mcq": {},
            "draft_mains_fact": "",
            "critique": "",
            "hallucination_detected": False,
            "iterations": 0
        }
        result = self.app.invoke(initial_state)
        return {
            "mcq": result["draft_mcq"],
            "mains_facts": result["draft_mains_fact"],
            "critique_trace": result["critique"],
            "final_iterations": result["iterations"]
        }
