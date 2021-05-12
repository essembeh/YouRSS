import unittest

from youtube_rss_viewer.youtube import get_channel_feed


class TestRss(unittest.TestCase):
    def test_channel(self):
        channel_id = "UCa_Dlwrwv3ktrhCy91HpVRw"
        feed = get_channel_feed(channel_id)
        self.assertIsNotNone(feed)
        self.assertEqual(feed.title, "Jeremy Griffith")
        self.assertEqual(feed.channel_id, channel_id)
        self.assertTrue(feed.link.startswith("https://www.youtube.com/"))
        self.assertGreater(len(feed.entries), 10)
        self.assertGreater(feed.entries[0].updated_date, feed.entries[1].updated_date)
        for entry in feed.entries:
            self.assertIsNotNone(entry.title)
            self.assertEqual(
                entry.link, "https://www.youtube.com/watch?v=" + entry.video_id
            )
            self.assertTrue(entry.thumbnail_url.endswith(".jpg"))

    def test_no_channel(self):
        feed = get_channel_feed("IdontExist")
        self.assertIsNone(feed)