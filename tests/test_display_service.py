from app.services.display import (
    build_entry_display_message,
    get_display_message,
    list_display_messages,
)
from app.schemas.display import DisplayCreateRequest

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
    assert messages[0].sector_code == "A"
    assert messages[0].arrow_direction == "RIGHT"
    assert messages[0].free_spots == 1
    assert messages[0].parking_symbol == "P"
    assert messages[0].display_text == "RIGHT 1 P"
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


def test_display_message_keeps_configured_arrow_when_zone_has_no_free_spots(db_session):
    zone, row = seed_zone_with_row(db_session)
    seed_spot(db_session, row, code="A-001", status="OCCUPIED")
    seed_display(db_session, zone, arrow_direction="RIGHT")
    db_session.commit()

    messages = list_display_messages(db_session)

    assert messages[0].arrow_direction == "RIGHT"
    assert messages[0].parking_symbol == "P"
    assert messages[0].display_text == "RIGHT 0 P"
    assert messages[0].message == "A RIGHT 0"


def test_display_message_formats_parking_zone_for_drivers(db_session):
    zone, row = seed_zone_with_row(db_session, sector_code="B1-C", row_code="B1-C")
    seed_spot(db_session, row, code="B1-C001", status="FREE")
    seed_spot(db_session, row, code="B1-C002", status="OCCUPIED")
    seed_display(db_session, zone, code="DISP-B1-C", arrow_direction="AHEAD")
    db_session.commit()

    messages = list_display_messages(db_session)

    assert messages[0].message == "B1-C 1"
    assert messages[0].display_text == "AHEAD 1 P"


def test_build_entry_display_message_combines_zone_lines(db_session):
    zone_b1, row_b1 = seed_zone_with_row(db_session, sector_code="B1-C", row_code="B1-C")
    seed_spot(db_session, row_b1, code="B1-C001", status="FREE")
    seed_display(db_session, zone_b1, code="DISP-B1-C", arrow_direction="AHEAD")

    zone_b2, row_b2 = seed_zone_with_row(db_session, sector_code="B2-C", row_code="B2-C")
    seed_spot(db_session, row_b2, code="B2-C01", status="FREE")
    seed_spot(db_session, row_b2, code="B2-C02", status="FREE")
    seed_display(db_session, zone_b2, code="DISP-B2-C", arrow_direction="AHEAD")
    db_session.commit()

    entry = build_entry_display_message(list_display_messages(db_session))

    assert entry.display_code == "DISP-ENTRY-MAIN"
    assert entry.free_spots == 3
    assert entry.lines == [
        "B1-C 1",
        "B2-C 2",
    ]


def test_display_create_request_rejects_full_as_manual_arrow_direction():
    try:
        DisplayCreateRequest(
            title="Display",
            code="DISP-B1-A",
            sector_code="B1-A",
            arrow_direction="FULL",
        )
    except ValueError:
        return

    raise AssertionError("FULL must not be configurable manually.")
