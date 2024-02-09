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


# Install

## From the source

First, you need [Poetry](https://python-poetry.org/), see [installation documentation](https://python-poetry.org/docs/#installation):

```sh
$ git clone https://github.com/essembeh/YouRSS
$ cd YouRSS
$ poetry install
$ poetry run -- dotenv run uvicorn yourss.webapp:app --reload 
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

*YouRSS* can only be configured using environment variables.

- `YOURSS_DEFAULT_CHANNELS`: defines the default channels to display
- `YOURSS_USER_foo`: create a custom page available at *https://yourss.tld/u/foo*, the value of the environment variable is the list of the channels
  - you can add as many users as you need
  - there is no registration nor authentication for users
- `YOURSS_REDIS_URL`: you can use a redis instance to cache RSS feeds and avatars (for example: `redis://localhost:6379/0`)
- `YOURSS_TTL_AVATAR`: the TTL of cached avatars (default is `24 * 3600`, 24 hours)
- `YOURSS_TTL_AVATAR`: the TTL of cached RSS feeds (default is `3600`, 1 hour)
- `YOURSS_CLEAN_TITLES`: if set to `true`, videos titles are cleaned to prevent UPPERCASE TITLES 
- `LOGURU_LEVEL` for logging level

> Note: channels can be Youtube username (like `@JonnyGiger`) or directly a *channel_id* (24 alnum chars) like `UCa_Dlwrwv3ktrhCy91HpVRw`, to provide a list, use a coma between channels

See [`.env`](./.env) for example.


# Usage

- you can browse a single channel with: `http://<your-instance>/@jonnygiger`
- you can browse multiple channels in a single page: `http://<your-instance>/@jonnygiger,@berrics`
- the original *RSS* feed can be access at `http://<your-instance>/api/rss/@jonnygiger`
- you will be redirected to the channel avatar with `http://<your-instance>/api/avatar/@jonnygiger`
- if you defined *users* with `YOURSS_USER_demo`, the pages can be accessed at `http://<your-instance>/u/demo`


# Extenal links

Special thanks to the amazing python frameworks: [FastAPI](https://fastapi.tiangolo.com/), [asyncio](https://docs.python.org/fr/3/library/asyncio.html), [httpx](https://www.python-httpx.org/) and [Redis](https://redis.io/)


- Youtube player API: https://developers.google.com/youtube/player_parameters