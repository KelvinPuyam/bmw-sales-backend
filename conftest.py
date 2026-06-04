"""
Runs before any test module is collected.
Sets environment variables that database.py and security.py read at import time.
"""
import os

# Must be set BEFORE database.py is imported (it calls create_engine at module level)
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_EXPIRE_MINUTES", "60")

# pytest                        # all tests
# pytest tests/test_security.py # just one file
# pytest -v --tb=short          # verbose with short tracebacks
# pytest --cov=app              # with coverage report