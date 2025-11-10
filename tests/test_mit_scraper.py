import unittest
from coursecrusader.scrapers.universities.mit import MITScraper

class TestMITScraper(unittest.TestCase):
    def setUp(self):
        self.scraper = MITScraper()

    def test_infer_mit_level(self):
        # Undergraduate
        self.assertEqual(self.scraper._infer_mit_level("6.001"), "Undergraduate")
        self.assertEqual(self.scraper._infer_mit_level("STS.499"), "Undergraduate")
        self.assertEqual(self.scraper._infer_mit_level("4.100"), "Undergraduate")
        self.assertEqual(self.scraper._infer_mit_level("1.00"), "Undergraduate")
        self.assertEqual(self.scraper._infer_mit_level("1.A05"), "Undergraduate")

        # Graduate
        self.assertEqual(self.scraper._infer_mit_level("21A.500"), "Graduate")
        self.assertEqual(self.scraper._infer_mit_level("18.901"), "Graduate")
        self.assertEqual(self.scraper._infer_mit_level("CMS.600"), "Graduate")
        self.assertEqual(self.scraper._infer_mit_level("1.563"), "Graduate")
        self.assertEqual(self.scraper._infer_mit_level("18.S997"), "Graduate")

        # Unknown
        self.assertEqual(self.scraper._infer_mit_level("NoDot"), "Unknown")
        self.assertEqual(self.scraper._infer_mit_level("1.ABC"), "Unknown")
