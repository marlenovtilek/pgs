from app.services.display import get_display_message, list_display_messages

from tests.conftest import seed_display, seed_spot, seed_zone_with_row


def test_list_display_messages_uses_zone_free_count(db_session):
    zone, row = seed_zone_with_row(db_session)
    seed_spot(db_session, row, code="A-001", status="FREE", sort_order=1)
    seed_spot(db_session, row, code="A-002", status="OCCUPIED", sort_order=2)
    seed_display(db_session, zone, arrow_direction="RIGHT")
    db_session.commit()

    messages = list_display_messages(db_session)

    assert len(messages) == 1
    assert messages[0].display_code == "DISP-A-01"
    assert messages[0].zone_code == "A"
    assert messages[0].arrow_direction == "RIGHT"
    assert messages[0].free_spots == 1
    assert messages[0].message == "A RIGHT 1"


def test_get_display_message_returns_none_for_missing_display(db_session):
    assert get_display_message(db_session, "MISSING") is None


def test_list_display_messages_filters_by_active_state(db_session):
    zone, row = seed_zone_with_row(db_session)
    seed_spot(db_session, row, code="A-001", status="FREE")
    seed_display(db_session, zone, code="ACTIVE", is_active=True)
    seed_display(db_session, zone, code="INACTIVE", is_active=False)
    db_session.commit()

    messages = list_display_messages(db_session, is_active=True)

    assert [message.display_code for message in messages] == ["ACTIVE"]
