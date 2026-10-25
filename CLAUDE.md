# YouRSS

## Philosophy

YouRSS is an alternative front-end to YouTube built on the **RSS feeds** YouTube publishes for
every channel and playlist. RSS is an open and stable way to share content: it lets people choose
how, and with which application, they follow what they like. YouRSS is a small RSS client for the
browser, nothing more.

What it gives: the latest videos of the channels you chose, on one page. No account, no
registration, no ads, no recommendations, no tracking.

Principles, in order of importance when they conflict:

1. **RSS first.** What a feed provides is read from the feed. Feeds are fetched live, unless the
   disk cache holds a copy younger than a few minutes.
2. **Pass through, never proxy.** The browser loads thumbnails, avatars and the player straight
   from YouTube, and every link (RSS feed, channel page) points to YouTube. The server never
   relays media.
3. **Stateless server.** No database, no session. One cookie only: the signed login of a user
   behind a password, checked without any server state (`docs/specs/login.md`). What belongs to a
   visitor (theme, density, watched videos) lives in the browser, in `localStorage`.
4. **Cache as little as possible.** No cache by default. One server cache, on disk, can be turned
   on: the feeds for a few minutes (and up to two days when YouTube fails) and the channel names
   and avatars for a week. Nothing else, and never media.
5. **Stay light.** One small FastAPI application, server-rendered templates, htmx for the dynamic
   parts, vanilla CSS and JavaScript. No front-end framework, no build step.
6. **Everything is a URL.** `/UC…,PL…` (channel and playlist ids in the URL), `/p/<page>` (a
   list configured by the administrator), `/u/<user>/<page>` (a user aggregates pages, its
   folders); a channel opened inside a page is `<page>?c=<id>`. A page can be bookmarked and
   shared as is. A visitor builds a page by adding and removing channels: its address is the
   subscription list, the home page explains it.

Not goals: accounts, comments, searching videos, recommendations, downloads, relaying or storing
media.

## Stack

Python 3.13, FastAPI, Jinja2, Pydantic (settings, models, `pydantic-xml` for the feeds),
`rapid-api-client` for every HTTP call, loguru. Front: htmx, one CSS file, five JavaScript modules
(ES modules resolved by an import map, no build step).

## Layout

| Path | Content |
| --- | --- |
| `src/yourss/main.py` | the FastAPI application |
| `src/yourss/schema.py`, `settings.py` | settings (`YOURSS_*`) and the pages and users file model |
| `src/yourss/warmup.py` | the background refresh of every page, started by the `lifespan` of the application |
| `src/yourss/routers/` | pages (`web`), htmx fragments (`htmx`), `api` |
| `src/yourss/youtube/` | HTTP client, RSS feed models, video and channel models |
| `src/yourss/templates/`, `static/` | Jinja templates, `yourss.css`, the `yourss*.js` modules, icons |
| `charts/yourss/` | Helm chart, one value per setting, same defaults as the application |
| `samples/users.yaml` | example of a pages and users file, also used by the development `.env` |
| `tests/` | pytest suite, its RSS fixtures are in `tests/data/` |

## Commands

The `Justfile` is the interface of the project:

- `just check`: ruff format, ruff check, mypy strict on `src` and `tests`
- `just test`: pytest with coverage, offline: Youtube is a fake transport replaying the answers recorded
  under `tests/data/youtube/` (`docs/specs/youtube-fake.md`)
- `just test-live`: the same suite against the real Youtube; `just test-record`: refresh the recorded answers
- `just webapp`: development server on http://localhost:8000
- `just format`, `just audit`, `just update-dependencies`, `just release`, `just publish`

`just check` and `just test` must both pass before a change is considered done.

## Conventions

- Python follows the `seb-python` skill: `uv` for everything, ruff at 120 columns, mypy strict,
  comments of one or two lines, code and documentation in English.
- A setting is a `YOURSS_*` variable declared in `AppSettings`, documented in the README table and
  mirrored by a Helm value with the same default.
- Front-end: every command is a `[data-action]` element handled in `yourss.js` (the entry module;
  `yourss-core.js`, `yourss-watched.js`, `yourss-player.js` and `yourss-listen.js` are its imports), CSS classes are
  prefixed `yourss-`, themes are sets of CSS variables selected by `<html data-theme>`. Anything
  a visitor can tune is a browser setting, not a server one.
- Front-end state lives in two places only: the URL (what is shown, bookmarkable) and
  `localStorage` (what belongs to the visitor). Everything else is read from the DOM when needed,
  never mirrored in a script variable that has to be kept in sync. A copy made for a reason (the
  feed kept for the counters) carries what it was taken from and is rebuilt from the page.
- Design notes live in `docs/specs/`, which is ignored by git in this repository.
- Commits use a gitmoji and go to `main`. Commit or push only when asked.
