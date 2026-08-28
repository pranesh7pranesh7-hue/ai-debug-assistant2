"""BugSense AI - Development Launcher.
Runs database migrations/seeding and starts backend server on port 8000.
"""
import os
import sys
import subprocess


def main():
    print("==================================================")
    print("  BugSense AI - Development Server Launcher")
    print("==================================================")

    # Change to backend directory
    backend_dir = os.path.join(os.path.dirname(__file__), "backend")
    os.chdir(backend_dir)

    # Seed demo data if database not present
    print("\nInitializing & seeding demo environment...")
    subprocess.run([sys.executable, "-m", "app.seed_demo"])

    print("\nStarting FastAPI server on http://127.0.0.1:8000...")
    print("Swagger API Documentation: http://127.0.0.1:8000/docs")
    print("Frontend available at: http://127.0.0.1:8000/ or via static server\n")

    subprocess.run([
        sys.executable, "-m", "uvicorn", "app.main:app",
        "--host", "127.0.0.1",
        "--port", "8000",
        "--reload"
    ])


if __name__ == "__main__":
    main()
