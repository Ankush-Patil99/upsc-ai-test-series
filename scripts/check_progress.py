# -*- coding: utf-8 -*-
import sys, time, re, io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api.models import SessionLocal, UniversalQuestionBank

LOG_FILE = Path(__file__).parent.parent / "logs" / "ingest_phase1_retry.log"

def get_db_count():
    db = SessionLocal()
    c = db.query(UniversalQuestionBank).count()
    db.close()
    return c

def check_progress():
    print("=" * 60)
    print(" 🚀 INGESTION PIPELINE PROGRESS MONITOR")
    print("=" * 60)
    
    if not LOG_FILE.exists():
        print("Log file not found yet. The process might be starting up...")
        return
        
    try:
        with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Could not read log file: {e}")
        return

    current_pdf = "Unknown"
    current_batch = 0
    total_batches = 0
    recent_activity = []
    
    # Parse log file backwards to find the current state
    for line in reversed(lines):
        line = line.strip()
        if not line or "Ignoring wrong pointing object" in line:
            continue
            
        if len(recent_activity) < 5 and ("[PARSE]" in line or "[LLM]" in line or "[DB]" in line or "Inserted" in line):
            recent_activity.insert(0, line)
            
        if "[PARSE] Batch" in line and total_batches == 0:
            m = re.search(r"Batch (\d+)/(\d+)", line)
            if m:
                current_batch = int(m.group(1))
                total_batches = int(m.group(2))
                
        if "to process for" in line and current_pdf == "Unknown":
            m = re.search(r"process for '(.+)'", line)
            if m:
                current_pdf = m.group(1)
                break  # Stop parsing backwards once we find the start of the current PDF

    print(f"\n📂 Currently Processing PDF : {current_pdf}")
    if total_batches > 0:
        pct = (current_batch / total_batches) * 100
        bar_len = 30
        filled = int((current_batch / total_batches) * bar_len)
        bar = "█" * filled + "░" * (bar_len - filled)
        print(f"⏳ PDF Progress           : [{bar}] {pct:.1f}% (Batch {current_batch}/{total_batches})")
    
    print(f"\n💾 Total Questions in DB  : {get_db_count()}")
    
    print("\n📝 Latest Log Activity:")
    for act in recent_activity:
        print(f"   > {act}")
        
    print("\n" + "=" * 60)
    if "PHASE 1 COMPLETE" in "".join(lines[-10:]):
        print("✅ INGESTION COMPLETELY FINISHED!")
    else:
        print("Status: 🟢 RUNNING FINE. (It takes ~15-20 mins per large PDF due to API limits)")
        print("=" * 60)

if __name__ == "__main__":
    check_progress()
