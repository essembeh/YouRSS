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
- on a page with several channels, you can choose to show/hide one or another, you can sort videos by published date
- you can mark videos as read so that on the next visit, you quickly see the new videos
- you can have *user* pages and you can configure which associated channels 
- support *Redis* for caching and speeding up the webapp
- support *light* and *dark* themes
- you can choose the behavior when you click on the video thumbnail:
  - open a modal dialog with the player (default)
  - the player will replace the thumbnail
  - open a new tab with the video

# Install

## From the source

First, you need [Poetry](https://python-poetry.org/), see [installation documentation](https://python-poetry.org/docs/#installation):

```sh
$ git clone https://github.com/essembeh/YouRSS
$ cd YouRSS
$ poetry install
$ poetry run -- dotenv run fastapi dev yourss/main.py
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

- `YOURSS_DEFAULT_CHANNELS`: defines the default channels to display
- `YOURSS_REDIS_URL`: you can use a redis instance to cache RSS feeds and avatars (for example: `redis://localhost:6379/0`)
- `YOURSS_TTL_METADATA`: the TTL of cached metadata, used for avatars urls... (default is `24 * 3600`, 24 hours)
- `YOURSS_TTL_RSS`: the TTL of cached RSS feeds (default is `3600`, 1 hour)
- `YOURSS_CLEAN_TITLES`: if set to `true`, videos titles are cleaned to prevent UPPERCASE TITLES 
- `YOURSS_THEME`: choose between `dark` and `light` Bootstrap themes (default is `light`)
- `YOURSS_OPEN_PRIMARY`: choose the action when you click on a thumbnail, can be `openEmbedded`, `openTab` or `openModal`, default is `openModal`
- `YOURSS_OPEN_SECONDARY`: choose the action when you click on the bottom right icon, can be `openEmbedded`, `openTab` or `openModal`, default is `openTab`
- `LOGURU_LEVEL` for logging level

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

- you can browse a single channel with: `http://my-yourss-instance/@jonnygiger`
- you can browse multiple channels in a single page: `http://my-yourss-instance/@jonnygiger,@berrics`
- the original *RSS* feed can be access at `http://my-yourss-instance/api/rss/@jonnygiger`
- you will be redirected to the channel avatar with `http://my-yourss-instance/api/avatar/@jonnygiger`
- if you defined somes *users*, for example `demo`, the page can be accessed at `http://my-yourss-instance/u/demo`


# Extenal links

Special thanks to the amazing python frameworks: [FastAPI](https://fastapi.tiangolo.com/), [asyncio](https://docs.python.org/fr/3/library/asyncio.html), [httpx](https://www.python-httpx.org/) and [Redis](https://redis.io/)


- Youtube player API: https://developers.google.com/youtube/player_parameters