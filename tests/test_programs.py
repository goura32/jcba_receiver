from datetime import UTC, datetime

from jcba_receiver.programs import current_from_entries


def test_current_program_ignores_malformed_timetable_entries():
    now = datetime(2026, 8, 31, 12, tzinfo=UTC)

    assert current_from_entries(["invalid", 4, [], {"start": 1, "end": None}], now) is None
