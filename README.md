# AI-powered UPSC Test Series Platform

This project is a scalable, production-grade AI-powered UPSC Test Series Platform.

## Architecture

- **Data Ingestion**: Parses books and syllabus PDFs.
- **Current Affairs Engine**: Dynamic updating of knowledge.
- **MCQ & Mains Generation**: Generates contextual questions and descriptive Mains facts.
- **Analytics & Recommendations**: Strong topic categorization and spaced repetition logic.

## Getting Started
1. `pip install -r requirements.txt`
2. Configure `configs/settings.yaml`
3. `uvicorn api.main:app --reload`
