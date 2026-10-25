from time import time

from bs4 import BeautifulSoup
from httpx import AsyncClient, BasicAuth
from pydantic import SecretStr
from pytest import mark

from yourss.schema import Password, PasswordMethod, User
from yourss.security import LOGIN_COOKIE, check_login, login_token, read_config
from yourss.settings import current_config

HTMX = {"HX-Request": "true"}


def bob() -> User:
    config = read_config()
    assert config is not None
    (out,) = (user for user in config.users if user.name == "bob")
    return out


@mark.parametrize("path", ["/u/bob", "/u/bob/podcast"])
async def test_form_instead_of_a_challenge(client: AsyncClient, path: str) -> None:
    resp = await client.get(path + "?c=UCxxx")
    assert resp.status_code == 401
    assert "www-authenticate" not in resp.headers
    (form,) = BeautifulSoup(resp.text, "html.parser").select("form.yourss-login")
    # The form posts back to the page it protects, its query string included
    assert form["action"] == path + "?c=UCxxx"
    assert form.select("input[type=password][name=password]")


async def test_login(client: AsyncClient) -> None:
    resp = await client.post("/u/bob/podcast?c=UCxxx", data={"password": "foo"})
    assert resp.status_code == 303
    assert resp.headers["Location"] == "/u/bob/podcast?c=UCxxx"
    cookie = resp.headers["set-cookie"]
    assert cookie.startswith(f"{LOGIN_COOKIE}=")
    assert "Path=/u/bob" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert f"Max-Age={int(current_config.login_ttl.total_seconds())}" in cookie
    # Plain HTTP here: not Secure
    assert "Secure" not in cookie

    # The cookie opens the user, its folders and their htmx fragments
    for path in ("/u/bob", "/u/bob/podcast"):
        resp = await client.get(path)
        assert resp.status_code == 200
    resp = await client.get("/u/bob/fun", headers=HTMX)
    assert resp.status_code == 200


async def test_login_secure_behind_https(client: AsyncClient) -> None:
    resp = await client.post("https://test/u/bob", data={"password": "foo"})
    assert resp.status_code == 303
    assert "Secure" in resp.headers["set-cookie"]


async def test_wrong_password(client: AsyncClient) -> None:
    resp = await client.post("/u/bob", data={"password": "bar"})
    assert resp.status_code == 401
    assert "set-cookie" not in resp.headers
    soup = BeautifulSoup(resp.text, "html.parser")
    assert soup.select("form.yourss-login .yourss-login-error")


async def test_logout(client: AsyncClient) -> None:
    await client.post("/u/bob", data={"password": "foo"})
    resp = await client.get("/u/bob/podcast")
    assert resp.status_code == 200
    # The settings offer to log out of a protected user
    assert BeautifulSoup(resp.text, "html.parser").select("form.yourss-logout[action='/u/bob']")

    resp = await client.post("/u/bob/podcast", data={"logout": "1"})
    assert resp.status_code == 303
    assert resp.headers["Location"] == "/u/bob"
    assert 'yourss-login=""' in resp.headers["set-cookie"]
    assert "Max-Age=0" in resp.headers["set-cookie"]
    resp = await client.get("/u/bob")
    assert resp.status_code == 401


async def test_basic_still_accepted(client: AsyncClient) -> None:
    resp = await client.get("/u/bob", auth=BasicAuth("bob", "foo"))
    assert resp.status_code == 200
    assert "set-cookie" not in resp.headers
    resp = await client.get("/u/bob", auth=BasicAuth("bob", "bar"))
    assert resp.status_code == 401


async def test_htmx_without_login_reloads(client: AsyncClient) -> None:
    resp = await client.get("/u/bob/podcast", headers=HTMX)
    assert resp.status_code == 401
    assert resp.headers["HX-Refresh"] == "true"


@mark.parametrize(
    "token",
    [
        "",
        "garbage",
        "123.abc",
        # Expired
        login_token(bob(), now=time() - 2 * current_config.login_ttl.total_seconds()),
        # Tampered expiry
        "9" + login_token(bob()),
    ],
)
async def test_refused_cookies(client: AsyncClient, token: str) -> None:
    client.cookies.set(LOGIN_COOKIE, token, path="/u/bob")
    resp = await client.get("/u/bob")
    assert resp.status_code == 401


def test_cookie_bound_to_user_and_password() -> None:
    user = bob()
    token = login_token(user)
    assert check_login(user, token)
    # Another user, or the same one with a new password: refused
    other = user.model_copy(update={"name": "carol"})
    assert not check_login(other, token)
    renewed = user.model_copy(update={"password": Password(method=PasswordMethod.CLEAR, value=SecretStr("new"))})
    assert not check_login(renewed, token)
    # A user without a password never logs in
    assert not check_login(user.model_copy(update={"password": None}), token)


async def test_user_without_password(client: AsyncClient) -> None:
    resp = await client.get("/u/alice")
    assert resp.status_code == 200
    assert not BeautifulSoup(resp.text, "html.parser").select("form.yourss-logout")
    resp = await client.post("/u/alice/fun", data={"password": "whatever"})
    assert resp.status_code == 303
    assert "set-cookie" not in resp.headers


async def test_unknown_user(client: AsyncClient) -> None:
    resp = await client.post("/u/unknown", data={"password": "foo"})
    assert resp.status_code == 404
