import unittest
from event_taxonomy_aliases import match_label, collect_alias_candidates

TAXONOMY={"primary_categories":[{"id":"music","label":"מוזיקה","subcategories":[{"id":"jazz","label":"ג׳אז"}]},{"id":"theatre","label":"תיאטרון","subcategories":[]}]}

class TaxonomyAliasesTests(unittest.TestCase):
    def test_exact_subcategory(self):
        self.assertEqual(match_label("ג׳אז",TAXONOMY,{"approved":{}})["subcategory"],"jazz")
    def test_external_name_stays_internal(self):
        result=match_label("הופעה חיה",TAXONOMY,{"approved":{}})
        self.assertEqual(result["status"],"needs_review")
    def test_approved_alias(self):
        self.assertEqual(match_label("הופעה חיה",TAXONOMY,{"approved":{"הופעה חיה":{"category":"music"}}})["category"],"music")
    def test_candidate_aggregation(self):
        events=[{"source_category":"הופעה חיה","source_id":"board","title":"A"},{"source_category":"הופעה חיה","source_id":"board","title":"B"}]
        out=collect_alias_candidates(events,TAXONOMY,{"approved":{}})
        self.assertEqual(len(out),1)
        self.assertEqual(out[0]["count"],2)

if __name__=="__main__":unittest.main()
