import unittest
from audit_media_coverage_v2 import audit_city

class CoverageTests(unittest.TestCase):
    def test_source_image_kept(self):
        e={"event_id":"a","start_date":"2026-12-01","status":"active","image_url":"https://cdn.example.org/a.jpg",
           "image_verified":True,"image_publishable":True}
        self.assertEqual(audit_city([e],[],today="2026-10-10")["counts"]["already_has_source_image"],1)

    def test_missing_photo_is_reported_not_published(self):
        e={"event_id":"a","start_date":"2026-12-01","status":"active","category":"music"}
        report=audit_city([e],[],today="2026-10-10")
        self.assertEqual(report["counts"]["missing_publishable_image"],1)
        self.assertEqual(report["missing"][0]["action"],"collect_or_verify_media")
        self.assertNotIn("image_url",e)

    def test_past_event_ignored(self):
        e={"event_id":"a","start_date":"2026-01-01","status":"active"}
        self.assertEqual(audit_city([e],[],today="2026-10-10")["counts"],{})

if __name__=="__main__": unittest.main()
