![Github](https://img.shields.io/github/tag/essembeh/yourss.svg)


# Youtube RSS viewer

> TL;DR; a minimal Youtube RSS feed viewer in your browser. There is no adds, no cookie*, no registration, no authentication, only the RSS content.

See [YouRSS on Desktop](./images/yourss_desktop.png) and [YouRSS on Mobile](./images/yourss_mobile.png)

Youtube RSS viewer is a simple service to browse the latest videos from Youtube channels you want.
You don't need a Youtube account to suscribe to channels, simply browse the latest videos by fetching the RSS feeds in a single page. No adds, no suggested videos, just the content you choose.

In social medias like Youtube, the keyword is *share*, I personnally think RSS feeds are a pretty good way to share content, it has been for decades. Youtube RSS feeds let *users* choose how they want to see videos, with the app they want.

I simply wrote a minimal RSS client webapp for web browsers.

## Features

- view the last 15 videos published by channels you like in a minimal page
- no account needed, simply add the channels you like to the *URL* (example https://yourss.domain.tld/@jonnygiger,@berrics)
- you can have *user* pages and you can configure which associated channels
- browse a channel homepage with its recent videos, videos, shorts and streams
- videos you played for a few seconds are marked as watched so that on the next visit you quickly see the new ones, with a count of new videos per channel (stored in your browser only, and it can be turned off in the settings)
- click a thumbnail to play in the page: the player takes the whole row, and docks as a mini player when you scroll away; a second action opens a fullscreen modal with links to YouTube and the RSS feed
- optional autoplay of the next video, instant search, keyboard shortcuts (arrows move in the grid, `n`/`p` play the next/previous video, `Shift`+`↑`/`↓` change channel…, press `?` for the list)
- three density levels, works on desktop and mobile
- three themes (neon, dark, light) to pick in the settings, no CSS framework

# Install

## From the source

First, you need [uv](https://docs.astral.sh/uv/), see [installation documentation](https://docs.astral.sh/uv/getting-started/installation/):

```sh
$ git clone https://github.com/essembeh/YouRSS
$ cd YouRSS
$ uv sync
$ uv run -- dotenv run fastapi dev yourss/main.py

# or if you use just
$ just run
```

Then visit [http://localhost:8000/](http://localhost:8000/)

## From docker

Using Docker you can run the latest image build on the latest commit:

```sh
$ docker run -d --name yourss -p 8000:8000 ghcr.io/essembeh/yourss:main
```

Then visit [http://localhost:8000/](http://localhost:8000/)

## Install Helm Chart for Kubernetes

You need an access to a Kubernetes cluster and `helm` tool installed.
```sh
# add the helm repository
$ helm repo add yourss https://essembeh.github.io/YouRSS/ 
# get the values.yaml
$ helm show values yourss/yourss > myvalues.yaml
# edit the values for your needs
$ vim myvalues.yaml
# install release
$ helm install my-yourss yourss/yourss -f myvalues.yaml
```

> Note: you need to add an *Ingress* to access the *Service* from outside your cluster.

You can then forward the service to test it:

```sh
$ kubectl port-forward service/my-yourss 8000:http
```

Then visit [http://localhost:8000/](http://localhost:8000/)

# Configuration

*YouRSS* can be configured using environment variables.

| VARIABLE | DEFAULT | HELM VALUE | DESCRIPTION |
|----------|---------|------------|-------------|
| YOURSS_DEFAULT_CHANNELS | `@JonnyGiger` | `yourss.defaultChannels` | Channels of the home page, you can set multiple channels using `,` as separator (a list in the Helm values) |
| YOURSS_API_DOCS_ENABLED | `False` | `yourss.apiDocsEnabled` | If set to `true`, the generated API documentation is served at `/docs`, `/redoc` and `/openapi.json`. Meant for development: it is off in the docker image and in the Helm chart |
| YOURSS_USERS_FILE |  | `yourss.users` | You can declare user pages in a dedicated file (the Helm chart builds it from the values and stores it in a *Secret*) |
| YOURSS_CLEAN_TITLES | `False` | `yourss.cleanTitles` | If set to `true`, videos titles are cleaned to prevent UPPERCASE TITLES |
| YOURSS_CACHE_FOLDER |  | `yourss.cacheEnabled` | If set, the last successful RSS response is stored on disk in this folder (created at startup) to survive Youtube's daily transient `404` windows. Feeds are **always** fetched live; this is a fallback, not a cache. If unset, a `404` is propagated as-is |
| YOURSS_CACHE_MAX_AGE | `PT24H` | `yourss.cacheMaxAge` | Max age of the fallback file served when Youtube returns a `404` (ISO-8601 duration, e.g. `PT24H`, or a number of seconds). Older files are deleted and the `404` is propagated |
| YOURSS_CHANNEL_CACHE_TTL | `PT1H` | `yourss.channelCacheTtl` | How long the name and avatar of a channel are kept in memory (ISO-8601 duration or seconds, `0` disables). Only these few strings are cached, at most 1024 channels; feeds and video lists are always fetched live |

> Note: channels can be Youtube username (like `@JonnyGiger`) or directly a *channel_id* (24 alnum chars) like `UCa_Dlwrwv3ktrhCy91HpVRw`, to provide a list, use a coma between channels

See [`.env`](./.env) for example.

## Configure user pages

You can create *user* pages with as many *channels* as you want, *user* pages are easier to type or remember.
For example you can have http://my-yourss-instance/u/skate with some *channels* configured instead of bookmarking http://my-yourss-instance/@jonnygiger,@berrics 

To configure users:
- set `YOURSS_USERS_FILE` and point to a *YAML* file where you'll declare your *users*
- see [sample `users.yaml`](./samples/users.yaml) for example
- *user* page can be protected by a *password* (configurable using plain text passwords or argon2 hash)

# Usage

- you can browse a single channel with: `http://yourss.local/@jonnygiger`
- you can browse multiple channels in a single page: `http://yourss.local/@jonnygiger,@berrics`
- you can browse the homepage of a channel (recent videos, videos, shorts, streams): `http://yourss.local/c/@jonnygiger`
- the original *RSS* feed can be access at `http://yourss.local/proxy/rss/@jonnygiger`
- you will be redirected to the channel avatar with `http://yourss.local/proxy/avatar/@jonnygiger`
- if you defined somes *users*, for example `demo`, the page can be accessed at `http://yourss.local/u/demo`

> Note: replace `yourss.local` with the URL of your *YouRSS* instance.

# External links

Special thanks to the amazing python frameworks: [FastAPI](https://fastapi.tiangolo.com/), [asyncio](https://docs.python.org/fr/3/library/asyncio.html), [httpx](https://www.python-httpx.org/) and [Pydantic](https://docs.pydantic.dev/) ♥️


- Youtube player API: https://developers.google.com/youtube/player_parameters
