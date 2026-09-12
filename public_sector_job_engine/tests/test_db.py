import uuid
import pytest
from core.db import init_db, SessionLocal, JobListing, MatchResult

def test_db_init_and_crud():
    init_db()
    test_id = str(uuid.uuid4())
    
    with SessionLocal() as db:
        listing = JobListing(
            id=test_id,
            company="FTSE Test Co",
            title="Management Accountant",
            location="London",
            description="Test description",
            requirements=["ACCA", "Excel"]
        )
        db.add(listing)
        db.commit()

    with SessionLocal() as db:
        fetched = db.query(JobListing).filter(JobListing.id == test_id).first()
        assert fetched is not None
        assert fetched.company == "FTSE Test Co"
        assert fetched.title == "Management Accountant"
        assert "ACCA" in fetched.requirements
