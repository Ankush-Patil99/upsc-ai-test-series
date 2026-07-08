from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from pgvector.sqlalchemy import Vector
from datetime import datetime
import os
import yaml

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "configs", "settings.yaml")
with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)

Base = declarative_base()


class User(Base):
    """Platform User Profile — stores credentials and session history."""
    __tablename__ = "users"

    id             = Column(Integer, primary_key=True, index=True)
    name           = Column(String, nullable=False)
    email          = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role           = Column(String, default="student")   # student | admin
    is_active      = Column(Boolean, default=True)
    is_premium     = Column(Boolean, default=False)
    tier_points    = Column(Integer, default=0)
    streak_count   = Column(Integer, default=0)
    last_streak_date = Column(DateTime)
    created_at     = Column(DateTime, default=datetime.utcnow)

    # Relationships
    test_sessions   = relationship("TestSession",   back_populates="user")
    taxonomy_scores = relationship("TaxonomyScore", back_populates="user")
    sent_friend_requests = relationship("Friendship", foreign_keys="[Friendship.user_id]", back_populates="sender")
    received_friend_requests = relationship("Friendship", foreign_keys="[Friendship.friend_id]", back_populates="receiver")


class Friendship(Base):
    """Stores connections and friend requests between users."""
    __tablename__ = "friendships"
    
    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    friend_id  = Column(Integer, ForeignKey("users.id"), nullable=False)
    status     = Column(String, default="pending")  # pending | accepted | rejected
    created_at = Column(DateTime, default=datetime.utcnow)

    sender   = relationship("User", foreign_keys=[user_id], back_populates="sent_friend_requests")
    receiver = relationship("User", foreign_keys=[friend_id], back_populates="received_friend_requests")


class Challenge(Base):
    """Stores head-to-head test challenges between friends."""
    __tablename__ = "challenges"

    id               = Column(Integer, primary_key=True, index=True)
    challenger_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    challenged_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    topic            = Column(String, nullable=False)
    status           = Column(String, default="pending")  # pending | accepted | completed | declined
    challenger_score = Column(Float, nullable=True)
    challenged_score = Column(Float, nullable=True)
    created_at       = Column(DateTime, default=datetime.utcnow)
    
    challenger = relationship("User", foreign_keys=[challenger_id])
    challenged = relationship("User", foreign_keys=[challenged_id])


class TestSession(Base):
    """Logs every individual exam attempt by a user."""
    __tablename__ = "test_sessions"

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=False)
    topic_tested    = Column(String)
    score           = Column(Float)          # percentage 0-100
    total_questions = Column(Integer)
    time_taken_secs = Column(Integer)        # seconds spent in exam
    attempt_data    = Column(String)         # JSON string: {wrongIndices: [], unattemptedIndices: [], state: []}
    created_at      = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="test_sessions")


class TaxonomyScore(Base):
    """Dynamically charts strengths & weaknesses across the Syllabus."""
    __tablename__ = "taxonomy_scores"

    id                 = Column(Integer, primary_key=True, index=True)
    user_id            = Column(Integer, ForeignKey("users.id"))
    category           = Column(String, index=True)  # e.g. "Environment -> Conventions"
    mastery_percentage = Column(Float, default=0.0)
    last_tested        = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="taxonomy_scores")


class MockTest(Base):
    """Stores pre-generated bulk question arrays (50-100 questions)."""
    __tablename__ = "mock_tests"

    id         = Column(Integer, primary_key=True, index=True)
    topic      = Column(String, index=True)
    count      = Column(Integer)
    paper_type = Column(String, default="GS-1")   # GS-1 | GS-2 | GS-3 | PYQ
    created_at = Column(DateTime, default=datetime.utcnow)

    questions = relationship("TestQuestion", back_populates="test")


class TestQuestion(Base):
    """Individual question belonging to a MockTest."""
    __tablename__ = "test_questions"

    id             = Column(Integer, primary_key=True, index=True)
    test_id        = Column(Integer, ForeignKey("mock_tests.id"))
    question       = Column(String)
    options_json   = Column(String)      # JSON string: {"a":..,"b":..,"c":..,"d":..}
    correct_option = Column(String)      # "a" | "b" | "c" | "d"
    rationale      = Column(String)
    mains_hint     = Column(String)
    subject        = Column(String)      # Polity | History | Economy | etc.
    difficulty     = Column(String, default="medium")  # easy | medium | hard

    test = relationship("MockTest", back_populates="questions")


class UniversalQuestionBank(Base):
    """Central repository for up to 11000+ questions for AI test generation and semantic search."""
    __tablename__ = "universal_question_bank"

    id             = Column(Integer, primary_key=True, index=True)
    subject        = Column(String, index=True)      # e.g., "Ancient History", "Art and Culture"
    topic          = Column(String, index=True)      # e.g., "Indus Valley Civilization"
    question       = Column(String)
    options_json   = Column(String)      # JSON string: ["Option A", "Option B", "Option C", "Option D"]
    correct_option = Column(String)      # Exact text of the correct option
    rationale      = Column(String)
    mains_hint     = Column(String)
    difficulty     = Column(String, default="medium")  # easy | medium | hard
    created_at     = Column(DateTime, default=datetime.utcnow)
    embedding      = Column(Vector(384)) # all-MiniLM-L6-v2 dimension
# ── Database Engine ──────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", config["db"]["postgres_url"])
engine       = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_analytics_tables():
    """Create all tables if they don't already exist."""
    Base.metadata.create_all(bind=engine)
