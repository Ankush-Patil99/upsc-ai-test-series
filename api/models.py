from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
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
    created_at     = Column(DateTime, default=datetime.utcnow)

    # Relationships
    test_sessions   = relationship("TestSession",   back_populates="user")
    taxonomy_scores = relationship("TaxonomyScore", back_populates="user")


class TestSession(Base):
    """Logs every individual exam attempt by a user."""
    __tablename__ = "test_sessions"

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=False)
    topic_tested    = Column(String)
    score           = Column(Float)          # percentage 0-100
    total_questions = Column(Integer)
    time_taken_secs = Column(Integer)        # seconds spent in exam
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


# ── Database Engine ──────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", config["db"]["postgres_url"])
engine       = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_analytics_tables():
    """Create all tables if they don't already exist."""
    Base.metadata.create_all(bind=engine)
