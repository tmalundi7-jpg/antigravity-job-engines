import os
import logging
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, String, Text, Integer, JSON, DateTime, Float, Boolean, text
from sqlalchemy.orm import declarative_base, sessionmaker
import config

logger = logging.getLogger("core.db")

Base = declarative_base()


def get_engine():
    uri = getattr(config, "POSTGRES_URI", "")
    # Check if postgres uri is usable
    if uri and uri.startswith("postgresql"):
        try:
            import psycopg2
            test_engine = create_engine(uri, connect_args={"connect_timeout": 3})
            with test_engine.connect() as conn:
                logger.info("Connected successfully to PostgreSQL.")
            return test_engine
        except Exception as e:
            logger.warning(f"PostgreSQL connection failed ({e}). Falling back to local SQLite database.")

    # Fallback to local SQLite database
    sqlite_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "job_engine.db")
    logger.info(f"Using SQLite database at {sqlite_path}")
    return create_engine(f"sqlite:///{sqlite_path}", connect_args={"check_same_thread": False})


engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class WorkflowState(Base):
    __tablename__ = 'workflows'
    id = Column(String, primary_key=True)
    status = Column(String, default="PENDING")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=True)
    data = Column(JSON)


class JobListing(Base):
    __tablename__ = 'job_listings'
    id = Column(String, primary_key=True)
    company = Column(String)
    title = Column(String)
    location = Column(String)
    description = Column(Text)
    requirements = Column(JSON)
    salary_range = Column(String, nullable=True)
    source_url = Column(String, nullable=True)
    raw_html = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class MatchResult(Base):
    __tablename__ = 'match_results'
    id = Column(String, primary_key=True)
    workflow_id = Column(String, nullable=True)
    job_id = Column(String)
    candidate_id = Column(String, nullable=True)
    similarity_score = Column(Float)
    structured_score = Column(Float, nullable=True)
    final_score = Column(Float)
    passed_prefilter = Column(Boolean, default=True)
    reasoning = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


def init_db():
    Base.metadata.create_all(bind=engine)
    # Ensure newly added columns exist in existing SQLite databases
    try:
        with engine.connect() as conn:
            # Check workflows.updated_at
            try:
                conn.execute(text("ALTER TABLE workflows ADD COLUMN updated_at DATETIME"))
                conn.commit()
            except Exception:
                pass
            # Check match_results.passed_prefilter
            try:
                conn.execute(text("ALTER TABLE match_results ADD COLUMN passed_prefilter BOOLEAN DEFAULT 1"))
                conn.commit()
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"Error during schema migration: {e}")
    logger.info("Database schema initialized.")


def checkpoint_workflow(workflow_id: str, status: str, data: dict = None) -> bool:
    """
    Persist or update intermediate workflow state in the database.
    Thread-safe and exception-resilient for SQLite and PostgreSQL.
    """
    try:
        with SessionLocal() as db:
            record = db.query(WorkflowState).filter(WorkflowState.id == workflow_id).first()
            now_utc = datetime.now(timezone.utc)
            if record:
                record.status = status
                if data is not None:
                    existing_data = dict(record.data or {})
                    existing_data.update(data)
                    record.data = existing_data
                record.updated_at = now_utc
            else:
                record = WorkflowState(
                    id=workflow_id,
                    status=status,
                    data=data or {},
                    created_at=now_utc,
                    updated_at=now_utc
                )
                db.add(record)
            db.commit()
            return True
    except Exception as e:
        logger.error(f"Failed to checkpoint workflow [{workflow_id}] status='{status}': {e}")
        return False
