import unittest
from media_catalog_v2 import MediaAsset, register_asset, choose_asset, publishable, asset_id_for_url

def asset(kind, subject, rights="verified", reviewer="editor", stored="https://cdn.example.org/image.webp"):
    return MediaAsset("", kind, "https://assets.example.org/"+kind+"-"+subject.replace(":","-")+".jpg",
                      "https://publisher.example.org/event/1",rights_status=rights,
                      reviewer=reviewer, stored_url=stored, subjects=[subject])

class MediaTests(unittest.TestCase):
    def test_idempotent_registration(self):
        catalog={}
        a=asset("artist","artist:42")
        self.assertTrue(register_asset(catalog,a)[1])
        self.assertFalse(register_asset(catalog,a)[1])
        self.assertEqual(len(catalog["assets"]),1)

    def test_unknown_rights_never_auto_published(self):
        self.assertFalse(publishable({"rights_status":"unknown","stored_url":"https://cdn.example.org/a.jpg"}))

    def test_expired_license(self):
        self.assertFalse(publishable({"rights_status":"verified","stored_url":"https://cdn.example.org/a.jpg","licensed_until":"2026-09-01"},on_date="2026-10-10"))

    def test_source_image_subject_precedes_category(self):
        a=asset("event_poster","production:p1")
        b=asset("category","category:music")
        catalog={}
        first,_=register_asset(catalog,a)
        second,_=register_asset(catalog,b)
        result=choose_asset([first,second],{"category":"music","production_id":"p1"},on_date="2026-10-10")
        self.assertEqual(result["asset_id"],first["asset_id"])

    def test_unrelated_artist_not_used(self):
        catalog={}
        value,_=register_asset(catalog,asset("artist","artist:someone-else"))
        self.assertIsNone(choose_asset([value],{"artist_id":"actual","category":"music"}))

    def test_category_fallback(self):
        catalog={}
        value,_=register_asset(catalog,asset("category","category:music"))
        self.assertEqual(choose_asset([value],{"category":"music"})["asset_id"],value["asset_id"])

    def test_requires_reviewer_for_verified_assets(self):
        with self.assertRaises(ValueError):
            asset("category","category:music",reviewer="").validate()

    def test_no_http_sources(self):
        with self.assertRaises(ValueError):
            asset_id_for_url("http://insecure.example.org/a.jpg")

if __name__=="__main__":unittest.main()
