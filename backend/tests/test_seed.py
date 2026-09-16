"""SEED_DEMO: a fresh deployment should show a scored dashboard, not an empty state."""
import asyncio
import os
from pathlib import Path

from sqlalchemy import func, select

from app.db import Base, SessionLocal, engine
from app.main import seed_demo_data, seed_demo_enabled
from app.models import Lead


def setup_module():
    engine.dispose()  # a previous module may have deleted the database file
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def teardown_module():
    os.environ.pop("SEED_DEMO", None)
    engine.dispose()
    Path("test_dealsieve.db").unlink(missing_ok=True)


def test_seed_demo_is_off_by_default():
    os.environ.pop("SEED_DEMO", None)
    assert seed_demo_enabled() is False
    for value in ("true", "TRUE", "1", "yes"):
        os.environ["SEED_DEMO"] = value
        assert seed_demo_enabled() is True, value
    os.environ["SEED_DEMO"] = "false"
    assert seed_demo_enabled() is False


def test_seed_imports_and_scores_the_sample_dataset():
    asyncio.run(seed_demo_data())
    with SessionLocal() as db:
        leads = list(db.scalars(select(Lead)).all())
        assert len(leads) == 13, [l.name for l in leads]
        assert all(l.status in ("enriched", "failed") for l in leads)
        scored = [l for l in leads if l.score and l.score > 0]
        assert len(scored) == 13
        assert any(l.tier == "A" for l in leads)


def test_seed_is_a_no_op_when_leads_already_exist():
    """Re-running must never duplicate or overwrite a user's own import."""
    with SessionLocal() as db:
        before = db.scalar(select(func.count(Lead.id)))
    asyncio.run(seed_demo_data())
    with SessionLocal() as db:
        assert db.scalar(select(func.count(Lead.id))) == before
