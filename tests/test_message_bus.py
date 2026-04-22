from __future__ import annotations

from mat.state.message_bus import MessageBus


def test_send_and_poll(tmp_path):
    bus = MessageBus(tmp_path)
    bus.send(to="alice", sender="bob", content="hi")
    bus.send(to="alice", sender="bob", content="again")

    msgs = bus.poll("alice")
    assert [m.content for m in msgs] == ["hi", "again"]
    assert all(m.sender == "bob" for m in msgs)


def test_cursor_advances(tmp_path):
    bus = MessageBus(tmp_path)
    bus.send(to="alice", sender="bob", content="first")
    assert len(bus.poll("alice")) == 1
    assert bus.poll("alice") == []  # nothing new

    bus.send(to="alice", sender="bob", content="second")
    msgs = bus.poll("alice")
    assert [m.content for m in msgs] == ["second"]


def test_separate_inboxes(tmp_path):
    bus = MessageBus(tmp_path)
    bus.send(to="alice", sender="bob", content="for alice")
    bus.send(to="charlie", sender="bob", content="for charlie")
    assert [m.content for m in bus.poll("alice")] == ["for alice"]
    assert [m.content for m in bus.poll("charlie")] == ["for charlie"]


def test_poll_unknown_agent_is_empty(tmp_path):
    bus = MessageBus(tmp_path)
    assert bus.poll("nobody") == []


def test_cc_delivers_to_cc_agent(tmp_path):
    bus = MessageBus(tmp_path, cc_agent="lead")
    bus.send(to="researcher", sender="writer", content="clarify please")

    direct = bus.poll("researcher")
    assert len(direct) == 1 and direct[0].cc is False

    cc = bus.poll("lead")
    assert len(cc) == 1
    assert cc[0].cc is True
    assert cc[0].original_to == "researcher"
    assert cc[0].sender == "writer"
    assert cc[0].content == "clarify please"


def test_cc_suppressed_when_lead_is_sender_or_recipient(tmp_path):
    bus = MessageBus(tmp_path, cc_agent="lead")

    # Lead-as-recipient: no duplicate copy in lead's inbox.
    bus.send(to="lead", sender="writer", content="hi boss")
    assert len(bus.poll("lead")) == 1  # just the direct one

    # Lead-as-sender: no self-CC.
    bus.send(to="writer", sender="lead", content="go")
    assert len(bus.poll("writer")) == 1
    assert bus.poll("lead") == []  # no self-CC added


def test_cc_disabled_by_default(tmp_path):
    bus = MessageBus(tmp_path)  # cc_agent=None
    bus.send(to="researcher", sender="writer", content="hey")
    assert bus.poll("lead") == []


def test_unread_count(tmp_path):
    bus = MessageBus(tmp_path)
    assert bus.unread_count("alice") == 0
    bus.send(to="alice", sender="bob", content="1")
    bus.send(to="alice", sender="bob", content="2")
    assert bus.unread_count("alice") == 2
    bus.poll("alice")
    assert bus.unread_count("alice") == 0
    bus.send(to="alice", sender="bob", content="3")
    assert bus.unread_count("alice") == 1
