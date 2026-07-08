from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, status, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
import tempfile
import os
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from dotenv import load_dotenv

# Load .env variables FIRST — before any module reads os.environ
load_dotenv()

# ── LangSmith LLMOps Tracing ─────────────────────────────────────────────────
# When LANGCHAIN_API_KEY is set, all LangGraph runs are automatically traced
# to the LangSmith dashboard for monitoring latency, tokens, and hallucinations.
if os.getenv("LANGCHAIN_API_KEY"):
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
    os.environ.setdefault("LANGCHAIN_PROJECT", "upsc-test-series")
    logging.getLogger("upsc_auth").info("[LangSmith] Tracing ENABLED — all LangGraph runs will be logged.")

from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from src.mcq_generation.generator import LangGraphMCQGenerator
from src.agents.scraper import ScraperAgent
from api.models import create_analytics_tables, SessionLocal, MockTest, TestQuestion, User, TestSession, TaxonomyScore
from api.auth import (
    get_db, get_current_user, get_optional_user,
    hash_password, verify_password,
    create_access_token, decode_token
)
from sqlalchemy.orm import Session

# ── Logging setup ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("upsc_auth")

# ── Custom Rate Limiter ────────────────────────────────────────────────────────
MAX_LOGIN_ATTEMPTS    = 5    # max failed logins before lockout
MAX_REGISTER_ATTEMPTS = 3    # max register attempts per minute
RATELIMIT_WINDOW_SECS = 60   # sliding window duration in seconds

# {ip_address: [datetime_of_attempt, ...]}
_login_attempts:    dict = defaultdict(list)
_register_attempts: dict = defaultdict(list)

def _check_rate_limit(store: dict, ip: str, max_attempts: int) -> tuple:
    """
    Sliding-window rate limiter.
    Returns (is_blocked: bool, attempts_so_far: int, seconds_until_reset: int)
    """
    now    = datetime.utcnow()
    cutoff = now - timedelta(seconds=RATELIMIT_WINDOW_SECS)
    # Remove timestamps outside the window
    store[ip] = [t for t in store[ip] if t > cutoff]
    count = len(store[ip])
    if count >= max_attempts:
        # Time until the oldest attempt falls out of the window
        oldest  = store[ip][0]
        reset_in = int((oldest + timedelta(seconds=RATELIMIT_WINDOW_SECS) - now).total_seconds()) + 1
        return True, count, max(reset_in, 1)
    return False, count, 0

def _record_attempt(store: dict, ip: str):
    """Record a new attempt for this IP."""
    store[ip].append(datetime.utcnow())

# ── JWT Token Blacklist (in-memory; use Redis in production) ──────────────────
TOKEN_BLACKLIST: set = set()



# ── Pydantic Schemas (request / response shapes) ─────────────────────────────
class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters.")
        return v

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Name cannot be empty.")
        return v.strip()


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    token: str
    user_id: int
    name: str
    email: str
    role: str


class SubmitTestRequest(BaseModel):
    topic_tested: str
    score: float
    total_questions: int
    time_taken_secs: int
    subject_stats: dict

def run_daily_current_affairs_pipeline():
    print("\n[CRON] Executing Automatic Current Affairs Pipeline...")
    # 1. Scrape all 7 sources
    scraper = ScraperAgent()
    raw_articles = scraper.fetch_all_current_affairs()
    
    # 2. Semantic Updater Pipeline (Chunk -> Qwen AI Classify -> PGVector Deduplicate -> Insert)
    from src.agents.updater import CAUpdaterNode
    updater = CAUpdaterNode()
    updater.execute(raw_articles)
    
    print(f"[CRON] CA Processing Cycle Gracefully Completed.\n")

# Instantiate Scheduler
scheduler = BackgroundScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Application Startup
    scheduler.add_job(run_daily_current_affairs_pipeline, 'interval', hours=24)
    scheduler.start()
    create_analytics_tables()
    print("Background APScheduler and Analytics Database Started!")
    
    yield
    
    # Application Shutdown
    scheduler.shutdown()

# Initialize FastAPI App
app = FastAPI(title="UPSC Test Series API", lifespan=lifespan)


# ── CORS — tightened: only allow your own origins ───────────────────────────────
# In production, replace with your actual deployed domain.
ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    os.getenv("PRODUCTION_DOMAIN", ""),   # set this in .env when deploying
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in ALLOWED_ORIGINS if o],  # filter empty strings
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# ── Security Headers Middleware ────────────────────────────────────────────────
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """
    Adds standard HTTP security headers to every response:
    - X-Content-Type-Options :  prevents MIME-type sniffing attacks
    - X-Frame-Options         :  prevents clickjacking (embedding in iframes)
    - X-XSS-Protection        :  enables browser's built-in XSS filter
    - Referrer-Policy         :  limits referrer info sent to other sites
    """
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"]         = "DENY"
    response.headers["X-XSS-Protection"]        = "1; mode=block"
    response.headers["Referrer-Policy"]         = "strict-origin-when-cross-origin"
    return response



# ── AUTH ENDPOINTS ────────────────────────────────────────────────────────────
@app.post("/api/auth/register", response_model=AuthResponse, tags=["Auth"])
def register(request: Request, payload: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new student account. Returns a JWT token on success."""
    import traceback
    client_ip = request.client.host

    # ── Rate limit: 3 register attempts per minute per IP ────────────────────────
    blocked, count, reset_in = _check_rate_limit(_register_attempts, client_ip, MAX_REGISTER_ATTEMPTS)
    if blocked:
        logger.warning(f"[REGISTER BLOCKED] IP: {client_ip} | too many attempts")
        raise HTTPException(
            status_code=429,
            detail={"message": f"Too many registration attempts. Try again in {reset_in} seconds.",
                    "remaining": 0, "reset_in": reset_in}
        )
    _record_attempt(_register_attempts, client_ip)

    try:
        existing = db.query(User).filter(User.email == payload.email.lower().strip()).first()
        if existing:
            logger.warning(f"[REGISTER] Duplicate email | IP: {client_ip} | email: {payload.email}")
            raise HTTPException(status_code=400, detail="An account with this email already exists.")

        user = User(
            name=payload.name,
            email=payload.email.lower().strip(),
            hashed_password=hash_password(payload.password),
            role="student",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        logger.info(f"[REGISTER] New user | IP: {client_ip} | email: {payload.email}")
        token = create_access_token(user.id, user.email)
        return AuthResponse(token=token, user_id=user.id, name=user.name, email=user.email, role=user.role)

    except HTTPException:
        raise
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"[REGISTER ERROR] {str(e)}\n{tb}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.post("/api/auth/login", response_model=AuthResponse, tags=["Auth"])
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Login with email + password.
    Tracks FAILED attempts per IP in a 60-second sliding window.
    Returns remaining_attempts after each wrong password.
    Locks out the IP after 5 failed attempts.
    """
    client_ip = request.client.host
    log_email = payload.email.lower().strip()
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    # ── Check if already locked out ──────────────────────────────────────────────
    blocked, count, reset_in = _check_rate_limit(_login_attempts, client_ip, MAX_LOGIN_ATTEMPTS)
    if blocked:
        logger.warning(f"[LOGIN LOCKED] IP: {client_ip} | reset_in: {reset_in}s")
        raise HTTPException(
            status_code=429,
            detail={"message": f"Too many failed attempts. Try again in {reset_in} seconds.",
                    "remaining": 0, "reset_in": reset_in}
        )

    # ── Verify credentials ─────────────────────────────────────────────────────────
    user = db.query(User).filter(User.email == log_email).first()

    if not user or not verify_password(payload.password, user.hashed_password):
        # Record this failed attempt
        _record_attempt(_login_attempts, client_ip)
        # Re-check to get updated count + remaining
        _, new_count, new_reset = _check_rate_limit(_login_attempts, client_ip, MAX_LOGIN_ATTEMPTS)
        remaining = max(MAX_LOGIN_ATTEMPTS - new_count, 0)
        logger.warning(f"[LOGIN FAILED] IP: {client_ip} | email: {log_email} | failures: {new_count}/{MAX_LOGIN_ATTEMPTS}")

        if remaining == 0:
            raise HTTPException(
                status_code=429,
                detail={"message": f"Account locked. Too many failed attempts. Try again in {new_reset} seconds.",
                        "remaining": 0, "reset_in": new_reset}
            )
        raise HTTPException(
            status_code=401,
            detail={"message": "Incorrect email or password.",
                    "remaining": remaining}
        )

    if not user.is_active:
        logger.warning(f"[LOGIN BLOCKED] IP: {client_ip} | email: {log_email} | deactivated")
        raise HTTPException(status_code=403, detail="Your account has been deactivated. Please contact support.")

    # ── Success: clear failed attempts for this IP ─────────────────────────────────
    _login_attempts[client_ip] = []
    token = create_access_token(user.id, user.email)
    logger.info(f"[LOGIN SUCCESS] IP: {client_ip} | user_id: {user.id} | email: {log_email} | {timestamp}")
    return AuthResponse(token=token, user_id=user.id, name=user.name, email=user.email, role=user.role)



@app.post("/api/auth/logout", tags=["Auth"])
def logout(request: Request, current_user: User = Depends(get_current_user)):
    """
    Invalidates the current JWT token server-side.
    After calling this, the token is blacklisted and can no longer be used,
    even if it hasn't expired yet.
    """
    # Extract the raw token from the Authorization header
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "").strip()
    if token:
        TOKEN_BLACKLIST.add(token)
    logger.info(f"[LOGOUT] user_id: {current_user.id} | email: {current_user.email}")
    return {"status": "success", "message": "Logged out successfully."}


@app.get("/api/auth/me", tags=["Auth"])
def get_me(request: Request, current_user: User = Depends(get_current_user)):
    """
    Returns the currently authenticated user's profile.
    Also checks the token blacklist (handles logout properly).
    """
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "").strip()
    if token in TOKEN_BLACKLIST:
        raise HTTPException(status_code=401, detail="Token has been invalidated. Please log in again.")
    return {
        "user_id":      current_user.id,
        "name":         current_user.name,
        "email":        current_user.email,
        "role":         current_user.role,
        "member_since": current_user.created_at.strftime("%B %Y"),
    }



class GoogleTokenRequest(BaseModel):
    credential: str   # The ID token string from Google's GSI library


@app.post("/api/auth/google", response_model=AuthResponse, tags=["Auth"])
def google_auth(payload: GoogleTokenRequest, db: Session = Depends(get_db)):
    """
    Verify a Google ID token from the frontend, then either:
      - Log in the user (if email already exists in DB)
      - Create a new account (first time Google sign-in)
    Returns a JWT token identical to the email/password flow.
    """
    import os
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests

    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")

    if not GOOGLE_CLIENT_ID or GOOGLE_CLIENT_ID == "YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Sign-In is not configured yet. Please add GOOGLE_CLIENT_ID to your .env file.",
        )

    # ── Verify the token with Google's servers ────────────────────────────────
    try:
        id_info = id_token.verify_oauth2_token(
            payload.credential,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google token: {str(e)}",
        )

    # ── Extract user info from verified token ─────────────────────────────────
    google_email = id_info.get("email", "").lower().strip()
    google_name  = id_info.get("name", google_email.split("@")[0].title())
    google_sub   = id_info.get("sub")   # unique Google user ID

    if not google_email:
        raise HTTPException(status_code=400, detail="Could not retrieve email from Google account.")

    # ── Upsert: find or create user ───────────────────────────────────────────
    user = db.query(User).filter(User.email == google_email).first()

    if not user:
        # First time signing in with Google — create account automatically
        # Use hashed google_sub as placeholder password (user will never log in with pw)
        user = User(
            name=google_name,
            email=google_email,
            hashed_password=hash_password(google_sub),  # placeholder, never used
            role="student",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"[Auth] New user via Google: {google_email}")
    else:
        print(f"[Auth] Existing user login via Google: {google_email}")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated. Contact support.")

    token = create_access_token(user.id, user.email)
    return AuthResponse(
        token=token,
        user_id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
    )


# Standard Endpoints
generator_engine = LangGraphMCQGenerator()

@app.get("/")
def health_check():
    return {"status": "operational", "message": "UPSC API is fully operational with active Background Tasks."}

@app.get("/generate/{topic}")
def generate_mcq(topic: str, difficulty: str = "medium"):
    """Generates an MCQ and descriptive Mains facts leveraging DeepSeek context."""
    try:
        result = generator_engine.generate(topic=topic, difficulty=difficulty)
        return {"status": "success", "topic": topic, "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/trigger-pipeline")
def trigger_pipeline():
    """Manual trigger if you want an immediate pull from your 7 sources, bypassing the 24 hour timer."""
    run_daily_current_affairs_pipeline()
    return {"status": "CA Pipeline triggered successfully in background."}

@app.post("/ingest/system-book")
async def upload_system_book(file: UploadFile = File(...)):
    """
    Upload massive PDF reference books (e.g. Laxmikanth). 
    File is cached locally, embedded natively via book_ingestor, and instantly scrubbed.
    """
    if not file.filename.endswith(".pdf"):
        return {"status": "error", "message": "Only PDF reference books are allowed."}
        
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
            
        from src.ingestion.book_ingestor import ingest_pdf_book
        # We process it synchronously for explicit verification, but typically should be a background task
        pages_processed = ingest_pdf_book(tmp_path, file.filename)
        
        # Cleanup
        os.remove(tmp_path)
        
        return {"status": "success", "message": f"Successfully ingested {file.filename}", "pages_embedded": pages_processed}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/tests/")
def list_mock_tests(db: Session = Depends(get_db)):
    """Retrieves all offline mock tests generated directly from the DB."""
    tests = db.query(MockTest).order_by(MockTest.created_at.desc()).all()
    return {"status": "success", "tests": tests}

@app.get("/api/tests/{test_id}")
def fetch_mock_test(test_id: int, db: Session = Depends(get_db)):
    """Retrieves the full array of questions for a specific Offline Mock Test!"""
    test = db.query(MockTest).filter(MockTest.id == test_id).first()
    if not test:
        return {"status": "error", "message": "Test not found."}
    
    # We serialize the JSON options string natively back to dictionary payload
    import json
    questions_list = []
    for q in test.questions:
        try:
            ops = json.loads(q.options_json)
        except:
            ops = {}
        questions_list.append({
            "id": q.id,
            "question": q.question,
            "options": ops,
            "correct_option": q.correct_option,
            "rationale": q.rationale,
            "mains_hint": q.mains_hint,
            "subject": q.subject,
            "difficulty": q.difficulty
        })
        
    return {"status": "success", "topic": test.topic, "count": test.count, "questions": questions_list}


@app.post("/api/tests/submit", tags=["Tests"])
def submit_test(payload: SubmitTestRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Saves test results and updates user taxonomy scores."""
    try:
        # Create new TestSession
        new_session = TestSession(
            user_id=current_user.id,
            topic_tested=payload.topic_tested,
            score=payload.score,
            total_questions=payload.total_questions,
            time_taken_secs=payload.time_taken_secs,
        )
        db.add(new_session)
        
        # Update TaxonomyScores
        for subject, stats in payload.subject_stats.items():
            if stats.get("total", 0) == 0:
                continue
                
            score_pct = (stats.get("correct", 0) / stats.get("total", 1)) * 100
            
            tax = db.query(TaxonomyScore).filter(TaxonomyScore.user_id == current_user.id, TaxonomyScore.category == subject).first()
            if not tax:
                tax = TaxonomyScore(
                    user_id=current_user.id,
                    category=subject,
                    mastery_percentage=score_pct,
                    last_tested=datetime.utcnow()
                )
                db.add(tax)
            else:
                # simple moving average
                tax.mastery_percentage = (tax.mastery_percentage + score_pct) / 2.0
                tax.last_tested = datetime.utcnow()
                
        db.commit()
        return {"status": "success", "message": "Test results saved successfully."}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}


@app.get("/api/analytics", tags=["Analytics"])
def get_analytics(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Retrieves user's taxonomy scores and past test sessions."""
    try:
        sessions = db.query(TestSession).filter(TestSession.user_id == current_user.id).order_by(TestSession.created_at.desc()).all()
        taxonomy = db.query(TaxonomyScore).filter(TaxonomyScore.user_id == current_user.id).all()
        
        session_list = [{"id": s.id, "topic_tested": s.topic_tested, "score": s.score, "time_taken_secs": s.time_taken_secs, "created_at": s.created_at} for s in sessions]
        taxonomy_list = [{"category": t.category, "mastery_percentage": t.mastery_percentage} for t in taxonomy]
        
        return {"status": "success", "sessions": session_list, "taxonomy": taxonomy_list}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Frontend UI Mount — serve index.html at both / and /app
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/app")
def serve_frontend():
    return FileResponse("frontend/index.html")

@app.get("/ui")
def serve_frontend_alt():
    return FileResponse("frontend/index.html")

class DiagnosisRequest(BaseModel):
    subject: str
    accuracy: float
    wrong_questions: list[str]

@app.post("/api/analytics/diagnosis", tags=["Analytics"])
def get_diagnosis(payload: DiagnosisRequest):
    try:
        from src.mcq_generation.generator import llm_cascade
        from langchain_core.prompts import PromptTemplate
        
        prompt = PromptTemplate.from_template(
            "You are an expert UPSC Civil Services mentor analyzing performance in {subject} ({accuracy}% accuracy).\n"
            "The user answered these questions wrong recently:\n{wrong_questions}\n\n"
            "Based ONLY on the themes of these specific wrong questions, list 2-3 highly specific micro-topics to improve.\n"
            "CRITICAL OUTPUT FORMAT RULES - follow exactly:\n"
            "1. Start with exactly: 'You can improve the following:'\n"
            "2. Each bullet must contain ONLY the micro-topic name. Nothing else. No colon, no description, no 'fundamental concepts', no 'related topics'.\n"
            "3. Each bullet on its own line starting with '- '\n"
            "4. Micro-topics must be very specific (e.g. 'WTO Dispute Settlement Body', 'Article 356 - President Rule', 'Biodiversity Hotspots in India').\n"
            "5. DO NOT use markdown bolding (**). DO NOT add any prose after the topic name.\n"
            "Example correct output:\n"
            "You can improve the following:\n"
            "- WTO Dispute Settlement Body\n"
            "- Article 356 President Rule provisions\n"
            "- Biodiversity Hotspots in India"
        )
        
        wq_text = chr(10).join(f"- {q}" for q in payload.wrong_questions) if payload.wrong_questions else "No specific questions provided, just give 2 core subtopics for this subject."
        
        raw_ai = None
        for llm in llm_cascade:
            if llm is None: continue
            try:
                chain = prompt | llm
                raw_ai = chain.invoke({"subject": payload.subject, "accuracy": payload.accuracy, "wrong_questions": wq_text})
                break
            except Exception:
                continue
                
        if raw_ai is not None:
            text = raw_ai.content if hasattr(raw_ai, 'content') else str(raw_ai)
            return {"status": "success", "diagnosis": text}
        return {"status": "error", "diagnosis": "Could not generate diagnosis. Please focus on standard NCERTs for now."}
    except Exception as e:
        return {"status": "error", "diagnosis": str(e)}
