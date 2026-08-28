import asyncio
import sys
from app.core.security import get_password_hash
from app.database import Base, SessionLocal, engine
from app.models.user import User
from app.modules.code_upload.uploader import CodeUploader
from app.services.analysis_service import AnalysisService
from app.services.agentic_service import AgenticService
from app.models.project import Project
from app.models.code_submission import CodeSubmission

# Ensure UTF-8 output on Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass



SAMPLE_BUGGY_CODE = '''# BugSense AI Demo Case: Multi-Bug Scenario
import sqlite3

def add_user_to_list(username, user_list=[]):
    """Bug 1: Mutable default argument retains state across calls."""
    user_list.append(username)
    return user_list

def process_file_data(filepath):
    """Bug 2: Resource leak - file opened without 'with' statement."""
    f = open(filepath, "r")
    data = f.read()
    return data

def calculate_item_indices(items):
    """Bug 3: Off-by-one error causing IndexError at runtime."""
    indices = []
    for i in range(len(items) + 1):
        indices.append(items[i])
    return indices

def fetch_user_record(db_path, user_id):
    """Bug 4: Security vulnerability - SQL Injection via f-string."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE id = '{user_id}'"
    cursor.execute(query)
    return cursor.fetchall()

def risky_operation():
    """Bug 5: Bare except catches system exit signals."""
    try:
        val = 10 / 2
        return val
    except:
        pass
'''


async def seed():
    """Seed the database with a test user and initial analysis."""
    print("🌱 Initializing BugSense AI database schema...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Create test user
        demo_email = "demo@bugsense.ai"
        user = db.query(User).filter(User.email == demo_email).first()
        if not user:
            user = User(
                email=demo_email,
                hashed_password=get_password_hash("password123"),
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"✅ Created demo user: {demo_email} (Password: password123)")

        # Upload sample buggy script
        sub = CodeUploader.process_raw_code(
            db=db,
            user_id=user.id,
            raw_code=SAMPLE_BUGGY_CODE,
            filename="demo_vulnerabilities.py",
        )
        print(f"✅ Uploaded sample script (Submission #{sub.id})")

        # Run analysis
        print("🔍 Running multi-tool static analysis and AST bug detection...")
        analysis_result = await AnalysisService.run_full_analysis(db, sub.id)
        print(f"✅ Analysis completed: Found {analysis_result['total_bugs']} bugs.")

        # Run agentic repair
        print("🤖 Running agentic autonomous debugging state machine...")
        agentic_res = await AgenticService.start_agentic_loop(db, sub.id, max_retries=2)
        print(f"✅ Agentic loop completed. Verified status: {agentic_res['is_verified']}")

        print("\n🎉 Demo Database successfully seeded and ready!")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(seed())
