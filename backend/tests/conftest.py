"""Pytest Configuration and Fixtures."""
import os
import sys
import pytest

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import Base, engine
import app.models  # Ensure all SQLAlchemy models are registered


@pytest.fixture(autouse=True, scope="session")
def setup_test_database():
    """Create all database tables before tests run and drop them after."""
    Base.metadata.create_all(bind=engine)
    yield
    # Tables can remain or be cleared
