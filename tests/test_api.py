from .test_youtube import CHANNEL_ID, SLUG, USER


def test_version(yourss_client):
    resp = yourss_client.get("/api/version")
    resp.raise_for_status()


def test_api_avatar_slug(yourss_client):
    resp = yourss_client.get(f"/api/avatar/{SLUG}", follow_redirects=False)
    assert 300 <= resp.status_code < 400


def test_api_avatar_channel(yourss_client):
    resp = yourss_client.get(f"/api/avatar/{CHANNEL_ID}", follow_redirects=False)
    assert 300 <= resp.status_code < 400


def test_api_avatar_user(yourss_client):
    resp = yourss_client.get(f"/api/avatar/{USER}", follow_redirects=False)
    assert 300 <= resp.status_code < 400


def test_api_rss_slug(yourss_client):
    resp = yourss_client.get(f"/api/rss/{SLUG}", follow_redirects=False)
    assert 300 <= resp.status_code < 400


def test_api_rss_channel(yourss_client):
    resp = yourss_client.get(f"/api/rss/{CHANNEL_ID}", follow_redirects=False)
    assert 300 <= resp.status_code < 400


def test_api_rss_user(yourss_client):
    resp = yourss_client.get(f"/api/rss/{USER}", follow_redirects=False)
    assert 300 <= resp.status_code < 400


def test_homepage(yourss_client):
    resp = yourss_client.get("/")
    assert resp.status_code == 200


def test_page(yourss_client):
    resp = yourss_client.get("/@jonnygiger")
    assert resp.status_code == 200
