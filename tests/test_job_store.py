from alphaagent.api.job_store import JobStore
from alphaagent.api.schemas.backtest import JobStatus
from alphaagent.storage.db import Database


def test_terminal_state_persists_and_hydrates(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    store = JobStore(db)
    job = store.create(label="x")
    job.update(status=JobStatus.RUNNING, bars_processed=5)   # not persisted
    job.update(status=JobStatus.COMPLETED, result={"k": 1})  # persisted

    store2 = JobStore(db)  # simulate restart
    j2 = store2.get(job.id)
    assert j2 is not None
    assert j2.status == JobStatus.COMPLETED
    assert j2.result == {"k": 1}
    assert j2.label == "x"


def test_interrupted_job_marked_failed_on_restart(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    store = JobStore(db)
    job = store.create()           # inserts a PENDING row, never reaches terminal

    store2 = JobStore(db)          # restart
    j2 = store2.get(job.id)
    assert j2.status == JobStatus.FAILED
    assert j2.error == "interrupted by restart"


def test_delete_removes_row(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    store = JobStore(db)
    job = store.create()
    assert store.delete(job.id) is True

    store2 = JobStore(db)
    assert store2.get(job.id) is None


def test_list_includes_persisted_history(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    store = JobStore(db)
    a = store.create(label="a")
    a.update(status=JobStatus.COMPLETED, result={})
    store2 = JobStore(db)
    assert a.id in {j.id for j in store2.list()}


def test_kind_roundtrips_and_filters(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    store = JobStore(db)
    b = store.create(label="bt")                 # default kind backtest
    s = store.create(label="sc", kind="screen")
    b.update(status=JobStatus.COMPLETED, result={})
    s.update(status=JobStatus.COMPLETED, result={})

    store2 = JobStore(db)  # restart -> hydrate
    assert store2.get(b.id).kind == "backtest"
    assert store2.get(s.id).kind == "screen"
    screen_ids = {j.id for j in store2.list(kind="screen")}
    assert screen_ids == {s.id}
    assert b.id in {j.id for j in store2.list()}  # no-arg lists all
