import unittest

from coleta import IsThereAnyDealScraper


class FakeResponse:
    status = 200
    headers = {"Content-Type": "application/json"}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return False

    async def json(self, content_type=None):
        return {"list": []}


class FakeSession:
    def __init__(self):
        self.request = None

    def get(self, url, **kwargs):
        self.request = (url, kwargs)
        return FakeResponse()


class DealRankingTests(unittest.IsolatedAsyncioTestCase):
    async def test_requests_trending_active_steam_deals(self):
        scraper = IsThereAnyDealScraper()
        scraper.key = "test-key"
        scraper.session = FakeSession()

        await scraper.fetch_featured()

        url, request = scraper.session.request
        self.assertEqual(url, scraper.BASE_URL)
        self.assertEqual(request["params"]["shops"], str(scraper.SHOP_STEAM))
        self.assertEqual(request["params"]["sort"], "-trending")
        self.assertEqual(request["params"]["nondeals"], "false")
        self.assertEqual(request["params"]["limit"], "20")


if __name__ == "__main__":
    unittest.main()
