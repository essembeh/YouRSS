import unittest

from yourss.youtube import yt_feed_url


class TestRss(unittest.TestCase):
    def test_channel(self):
        channel_id = "UCa_Dlwrwv3ktrhCy91HpVRw"
        feed = yt_feed_url(channel_id)
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
        feed = yt_feed_url("I_do_not_exist")
        self.assertIsNone(feed)
