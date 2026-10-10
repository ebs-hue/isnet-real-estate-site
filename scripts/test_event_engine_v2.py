"""Regression tests for the shared ISNET event engine."""
import unittest
from event_engine_v2 import canonical, duplicate_agent_ids, occurrence_key


def event(event_id, venue="משכן לאמנויות הבמה", time="20:30", source="internal"):
    return {
        "event_id": event_id, "city": "אשדוד",
        "title": "מופע מוזיקה", "start_date": "2026-12-01",
        "start_time": time, "venue": venue, "source": source,
    }


class IdentityTests(unittest.TestCase):
    def test_title_normalization(self):
        self.assertEqual(canonical("  מופע—מוזיקה "), canonical("מופע מוזיקה"))

    def test_city_separation(self):
        e = event("auto_1")
        self.assertNotEqual(occurrence_key(e, "ashdod"), occurrence_key(e, "rishon-lezion"))

    def test_same_occurrence_only_one_board(self):
        events = [event("auto_1"), event("board_1", source="national_stage_boards")]
        self.assertEqual(duplicate_agent_ids(events, "ashdod", "2026-10-10"), {"auto_1"})

    def test_distinct_venue_is_not_duplicate(self):
        events = [event("auto_1", venue="אודיטוריום אשדוד"),
                  event("board_1", source="national_stage_boards")]
        self.assertFalse(duplicate_agent_ids(events, "ashdod", "2026-10-10"))

    def test_distinct_time_is_not_duplicate(self):
        events = [event("auto_1", time="18:30"),
                  event("board_1", source="national_stage_boards")]
        self.assertFalse(duplicate_agent_ids(events, "ashdod", "2026-10-10"))

    def test_manual_lock_preserved(self):
        locked = event("auto_1")
        locked["human_manual_override"] = True
        events = [locked, event("board_1", source="national_stage_boards")]
        self.assertFalse(duplicate_agent_ids(events, "ashdod", "2026-10-10"))

    def test_board_missing_keeps_agent(self):
        self.assertFalse(duplicate_agent_ids([event("auto_1")], "ashdod", "2026-10-10"))

    def test_existing_id_preferred_to_new_board_id(self):
        events = [event("auto_existing", source="national_stage_boards"),
                  event("board_new", source="national_stage_boards")]
        self.assertEqual(duplicate_agent_ids(events, "ashdod", "2026-10-10"), {"board_new"})


if __name__ == "__main__":
    unittest.main()
