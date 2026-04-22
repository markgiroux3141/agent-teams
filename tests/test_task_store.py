from __future__ import annotations

from mat.state.task_store import TaskStore


def test_create_and_list(tmp_path):
    store = TaskStore(tmp_path / "tasks.jsonl")
    tid = store.create_task("Write haiku", "About observability")
    assert tid == "t_001"
    tasks = store.list_tasks()
    assert len(tasks) == 1
    assert tasks[0].title == "Write haiku"
    assert tasks[0].status == "created"
    assert tasks[0].assigned_to is None


def test_assign_and_lifecycle(tmp_path):
    store = TaskStore(tmp_path / "tasks.jsonl")
    tid = store.create_task("t", "d")

    store.assign_task(tid, "alice")
    t = store.get_task(tid)
    assert t.assigned_to == "alice"
    assert t.status == "assigned"

    store.update_status(tid, "in_progress")
    assert store.get_task(tid).status == "in_progress"

    store.update_status(tid, "completed", result_ref="haiku.md", note="done")
    t = store.get_task(tid)
    assert t.status == "completed"
    assert t.result_ref == "haiku.md"
    assert t.note == "done"


def test_filter_by_status(tmp_path):
    store = TaskStore(tmp_path / "tasks.jsonl")
    a = store.create_task("a", "")
    b = store.create_task("b", "")
    store.update_status(a, "completed")
    assert [t.task_id for t in store.list_tasks(status="completed")] == [a]
    assert [t.task_id for t in store.list_tasks(status="created")] == [b]


def test_replay_from_disk_restores_state_and_counter(tmp_path):
    path = tmp_path / "tasks.jsonl"
    s1 = TaskStore(path)
    s1.create_task("a", "")
    s1.create_task("b", "")

    s2 = TaskStore(path)
    assert {t.task_id for t in s2.list_tasks()} == {"t_001", "t_002"}
    tid3 = s2.create_task("c", "")
    assert tid3 == "t_003"


def test_claim_blocks_when_already_owned(tmp_path):
    store = TaskStore(tmp_path / "tasks.jsonl")
    tid = store.create_task("t", "")
    assert store.claim_task(tid, "alice") is True
    assert store.claim_task(tid, "bob") is False
    assert store.get_task(tid).assigned_to == "alice"
