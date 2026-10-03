# YouRSS

## Philosophy

YouRSS is an alternative front-end to YouTube built on the **RSS feeds** YouTube publishes for
every channel and playlist. RSS is an open and stable way to share content: it lets people choose
how, and with which application, they follow what they like. YouRSS is a small RSS client for the
browser, nothing more.

What it gives: the latest videos of the channels you chose, on one page. No account, no
registration, no ads, no recommendations, no tracking.

Principles, in order of importance when they conflict:

1. **RSS first.** What a feed provides is read from the feed. Feeds are always fetched live.
2. **Pass through, never proxy.** The browser loads thumbnails, avatars and the player straight
   from YouTube. The server never relays media; the `/proxy/*` routes are HTTP redirects.
3. **Stateless server.** No database, no session, no cookie. What belongs to a visitor (theme,
   density, watched videos) lives in the browser, in `localStorage`.
4. **Cache as little as possible.** The only server cache is a small, bounded, in-memory one for
   channel names and avatars. The RSS copy on disk is a fallback for YouTube's transient 404, not a
   cache.
5. **Stay light.** One small FastAPI application, server-rendered templates, htmx for the dynamic
   parts, vanilla CSS and JavaScript. No front-end framework, no build step.
6. **Everything is a URL.** `/@a,@b` (channels in the URL), `/u/<name>` (a configured list),
   `/c/<id>` (one channel). A page can be bookmarked and shared as is. A visitor builds a page by
   adding and removing channels: its address is the subscription list, the home page explains it.

Not goals: accounts, comments, searching videos, recommendations, downloads, relaying or storing
media.

## Stack

Python 3.13, FastAPI, Jinja2, Pydantic (settings, models, `pydantic-xml` for the feeds),
`rapid-api-client` for every HTTP call, loguru. Front: htmx, one CSS file, one JavaScript file.

## Layout

| Path | Content |
| --- | --- |
| `src/yourss/main.py` | the FastAPI application |
| `src/yourss/schema.py`, `settings.py` | settings (`YOURSS_*`) and the users file model |
| `src/yourss/routers/` | pages (`web`), htmx fragments (`htmx`), redirects (`proxy`), `api` |
| `src/yourss/youtube/` | HTTP client, RSS feed models, video and channel models |
| `src/yourss/templates/`, `static/` | Jinja templates, `yourss.css`, `yourss.js`, icons |
| `charts/yourss/` | Helm chart, one value per setting, same defaults as the application |
| `samples/users.yaml` | example of a users file, also used by the development `.env` |
| `tests/` | pytest suite, its RSS fixtures are in `tests/data/` |

## Commands

The `Justfile` is the interface of the project:

- `just check`: ruff format, ruff check, mypy strict on `src` and `tests`
- `just test`: pytest with coverage (the tests call YouTube for real, they need the network)
- `just webapp`: development server on http://localhost:8000
- `just format`, `just audit`, `just outdated`, `just release`, `just publish`

`just check` and `just test` must both pass before a change is considered done.

## Conventions

- Python follows the `seb-python` skill: `uv` for everything, ruff at 120 columns, mypy strict,
  comments of one or two lines, code and documentation in English.
- A setting is a `YOURSS_*` variable declared in `AppSettings`, documented in the README table and
  mirrored by a Helm value with the same default.
- Front-end: every command is a `[data-action]` element handled in `yourss.js`, CSS classes are
  prefixed `yourss-`, themes are sets of CSS variables selected by `<html data-theme>`. Anything
  a visitor can tune is a browser setting, not a server one.
- Design notes live in `docs/specs/`, which is ignored by git in this repository.
- Commits use a gitmoji and go to `main`. Commit or push only when asked.
