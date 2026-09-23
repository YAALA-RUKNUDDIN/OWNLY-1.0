"""Run the pytest suite with a SQLite test DB (Docker-independent).

BCRYPT_ROUNDS=4 keeps hashing cheap in tests; production keeps the
default (12) from the environment. For a PostgreSQL-parity run:
  TEST_DATABASE_URL=postgresql+psycopg2://ownly:ownly_secret@localhost:5433/ownly_test
"""
import os, subprocess, sys

os.environ.setdefault("DATABASE_URL", "sqlite:///./ownly_test.db")
os.environ["BCRYPT_ROUNDS"] = "4"
sys.exit(subprocess.call([sys.executable, "-X", "utf8", "-m", "pytest", "-q", "tests/"]))




