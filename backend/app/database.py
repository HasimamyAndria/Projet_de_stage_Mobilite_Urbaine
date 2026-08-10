from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()

_db_user = os.getenv("DB_USER")
_db_password = os.getenv("DB_PASSWORD")
_db_host = os.getenv("DB_HOST")
_db_port = os.getenv("DB_PORT")
_db_name = os.getenv("DB_NAME")

if not all([_db_user, _db_password, _db_host, _db_port, _db_name]):
    raise RuntimeError(
        "Variables DB manquantes (DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME). "
        "Copier .env.example vers .env."
    )

DATABASE_URL = (
    f"postgresql://{_db_user}:{_db_password}@{_db_host}:{_db_port}/{_db_name}"
)

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()