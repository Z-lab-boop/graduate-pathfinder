"""Schedule boundaries and portable RFC 5545 serialization contracts."""
from datetime import datetime, timezone
import re
import unittest

from scripts.detect_schedule_conflicts import detect_conflicts, parse_event
from scripts.generate_calendar import render_ics


def event(candidate_id="a", **changes):
    record = {"candidate_id": candidate_id, "event_type": "assessment",
              "start": "2027-06-01T09:00:00+08:00",
              "end": "2027-06-01T10:00:00+08:00"}
    record.update(changes)
    return record


def unfolded(ics):
    return ics.replace("\r\n ", "")


class ScheduleTests(unittest.TestCase):
    def test_parse_normalizes_utc_and_preserves_local_values_without_mutation(self):
        record = event()
        parsed = parse_event(record)
        self.assertEqual(parsed["start_utc"], datetime(2027, 6, 1, 1, tzinfo=timezone.utc))
        self.assertEqual(parsed["end_utc"], datetime(2027, 6, 1, 2, tzinfo=timezone.utc))
        self.assertEqual(parsed["start"], record["start"])
        self.assertNotIn("start_utc", record)
        self.assertEqual(parse_event(parsed), parsed)

    def test_overlaps_report_both_events_and_original_local_timestamps(self):
        first = event()
        second = event("b", event_type="interview", start="2027-06-01T01:30:00Z",
                       end="2027-06-01T03:00:00+00:00")
        self.assertEqual(detect_conflicts([first, second]), [{
            "candidate_ids": ["a", "b"], "event_types": ["assessment", "interview"],
            "overlap_minutes": 30.0,
            "local_timestamps": [{"start": first["start"], "end": first["end"]},
                                 {"start": second["start"], "end": second["end"]}],
        }])

    def test_adjacent_and_disjoint_events_do_not_overlap(self):
        for start in ("2027-06-01T10:00:00+08:00", "2027-06-01T11:00:00+08:00"):
            self.assertEqual(detect_conflicts([event(), event("b", start=start,
                             end="2027-06-01T12:00:00+08:00")]), [])

    def test_containment_and_same_candidate_are_still_conflicts(self):
        inner = event(start="2027-06-01T09:10:00+08:00", end="2027-06-01T09:20:00+08:00")
        self.assertEqual(detect_conflicts([event(), inner])[0]["overlap_minutes"], 10)

    def test_all_overlapping_pairs_reported_once(self):
        self.assertEqual(len(detect_conflicts([event("a"), event("b"), event("c")])), 3)
        self.assertEqual(detect_conflicts([]), [])

    def test_seconds_are_not_rounded_to_whole_minutes(self):
        other = event("b", start="2027-06-01T09:59:30+08:00", end="2027-06-01T10:01:00+08:00")
        self.assertEqual(detect_conflicts([event(), other])[0]["overlap_minutes"], 0.5)

    def test_missing_timezone_or_unresolved_date_rejected(self):
        for value in (None, "", "unknown", "2027-06-01", "2027-06-01T09:00:00",
                      "2027-06-01T09:00:00-00:00"):
            for field in ("start", "end"):
                with self.subTest(value=value, field=field), self.assertRaises(ValueError):
                    parse_event(event(**{field: value}))

    def test_invalid_offsets_and_dates_rejected(self):
        for value in ("2027-06-01T09:00:00+08:60", "2027-06-01T09:00:00+24:00",
                      "2027-02-30T09:00:00+08:00"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_event(event(start=value))

    def test_unknown_deadline_precision_rejected(self):
        for field in ("precision", "deadline_precision", "date_precision"):
            for precision in ("unknown", "date", "estimated", None):
                with self.subTest(field=field, precision=precision), self.assertRaises(ValueError):
                    parse_event(event(event_type="deadline", **{field: precision}))
        self.assertEqual(parse_event(event(precision="exact"))["candidate_id"], "a")

    def test_end_must_be_after_start(self):
        for end in ("2027-06-01T09:00:00+08:00", "2027-06-01T08:59:59+08:00"):
            with self.subTest(end=end), self.assertRaises(ValueError):
                parse_event(event(end=end))

    def test_fractional_seconds_are_rejected_instead_of_truncated(self):
        with self.assertRaises(ValueError):
            parse_event(event(start="2027-06-01T09:00:00.123+08:00"))

    def test_identity_fields_required(self):
        for field in ("candidate_id", "event_type"):
            for value in (None, "", " ", 7):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    parse_event(event(**{field: value}))
        with self.assertRaises(ValueError):
            parse_event(None)


class CalendarTests(unittest.TestCase):
    def test_calendar_has_required_fields_utc_times_and_crlf(self):
        ics = render_ics([event()], "申请日程")
        self.assertTrue(ics.startswith("BEGIN:VCALENDAR\r\n"))
        self.assertTrue(ics.endswith("END:VCALENDAR\r\n"))
        for line in ("VERSION:2.0", "PRODID:-//graduate-pathfinder//EN",
                     "X-WR-CALNAME:申请日程", "BEGIN:VEVENT", "END:VEVENT",
                     "DTSTART:20270601T010000Z", "DTEND:20270601T020000Z",
                     "DTSTAMP:20270601T010000Z"):
            self.assertIn(line + "\r\n", ics)
        self.assertNotIn("\n", ics.replace("\r\n", ""))

    def test_text_escaping_prevents_property_injection(self):
        ics = unfolded(render_ics([event(summary="a,b;c\\d\r\n伪造:值",
                                       description="line1\nline2", location="楼,室;1")],
                                  "名,称;\\\nEND:VCALENDAR"))
        self.assertIn("SUMMARY:a\\,b\\;c\\\\d\\n伪造:值\r\n", ics)
        self.assertIn("DESCRIPTION:line1\\nline2\r\n", ics)
        self.assertIn("LOCATION:楼\\,室\\;1\r\n", ics)
        self.assertIn("X-WR-CALNAME:名\\,称\\;\\\\\\nEND:VCALENDAR\r\n", ics)
        self.assertEqual(ics.count("\r\nEND:VCALENDAR\r\n"), 1)

    def test_uid_is_stable_across_offset_spelling_and_content_changes(self):
        def uid(record):
            return re.search(r"^UID:(.*)$", unfolded(render_ics([record], "x")), re.M)[1].strip()
        original = uid(event())
        self.assertEqual(original, uid(event(summary="edited")))
        self.assertEqual(original, uid(event(start="2027-06-01T01:00:00Z")))
        for changed in (event("b"), event(event_type="interview"),
                        event(start="2027-06-01T09:01:00+08:00")):
            self.assertNotEqual(original, uid(changed))

    def test_rendering_is_deterministic_even_if_input_order_changes(self):
        records = [event("b"), event("a")]
        self.assertEqual(render_ics(records, "x"), render_ics(list(reversed(records)), "x"))

    def test_utf8_folding_keeps_octet_limit_and_codepoints(self):
        summary = "中🙂文" * 80
        ics = render_ics([event(summary=summary)], "x")
        for line in ics.encode("utf-8").split(b"\r\n"):
            self.assertLessEqual(len(line), 75)
            line.decode("utf-8")
        self.assertIn("\r\n ", ics)
        self.assertIn("SUMMARY:" + summary + "\r\n", unfolded(ics))

    def test_ascii_boundary_folding_keeps_content(self):
        for length in (66, 67, 68, 140, 141):
            summary = "x" * length
            ics = render_ics([event(summary=summary)], "x")
            self.assertIn("SUMMARY:" + summary + "\r\n", unfolded(ics))
            self.assertTrue(all(len(line.encode()) <= 75 for line in ics.split("\r\n")))

    def test_renderer_rejects_unresolved_events(self):
        for record in (event(precision="unknown"), event(start="2027-06-01"),
                       event(end="2027-06-01T10:00:00")):
            with self.subTest(record=record), self.assertRaises(ValueError):
                render_ics([record], "x")

    def test_empty_calendar_valid_and_parsed_events_supported(self):
        self.assertNotIn("BEGIN:VEVENT", render_ics([], "x"))
        self.assertEqual(render_ics([event()], "x"), render_ics([parse_event(event())], "x"))

    def test_control_characters_and_nontext_values_rejected(self):
        for value in ("bad\x00text", "bad\x7ftext", 123, None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                render_ics([event(summary=value)], "x")

    def test_duplicate_calendar_identity_is_rejected(self):
        with self.assertRaises(ValueError):
            render_ics([event(), event(summary="duplicate")], "x")


if __name__ == "__main__":
    unittest.main()
