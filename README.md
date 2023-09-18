![Github](https://img.shields.io/github/tag/essembeh/yourss.svg)


# Youtube RSS viewer

> TL;DR; a minimal Youtube RSS feed viewer in your browser

Youtube RSS viewer is a simple service to browse in a single page the latest videos from Youtube channels you want.
You don't need a Youtube account to suscribe to channels, simply browse the latest videos by fetching the RSS feeds in a single page. No adds, no suggested videos, just the content you choose.

In social medias like Youtube, the keyword is *share*, I personnally think RSS feeds are a pretty good way to share content. Youtube RSS feeds let *users* choose how they want to see videos, with the app they want.

I simply wrote a minimal RSS client for web browsers.


# Install

## From docker

Using Docker you can run the latest image build on the latest commit
```sh
$ docker run -d --name youtube -p 8000:8000 ghcr.io/essembeh/yourss:main
# then open the page in your browser
$ xdg-open http://127.0.0.1:8000
```

# Configuration

*YouRSS* can be configured using environment variables.

- `YOURSS_DEFAULT_CHANNELS`: defines the default channels to display
- `YOURSS_USER_foo`: create a custom page available at *https://yourss.tld/u/foo*, the value of the environment variable is the list of the channels


> Note: channels can be Youtube username (like `@JonnyGiger`) or directly a *channel_id* (24 alnum chars) like `UCa_Dlwrwv3ktrhCy91HpVRw`, to provide a list, use a coma between channels

Example:
```sh
YOURSS_DEFAULT_CHANNELS=@jonnygiger,UCa_Dlwrwv3ktrhCy91HpVRw
YOURSS_USER_foo=@jonnygiger
YOURSS_USER_bar=@lostangelus52,UCB99aK4f2WaH96joccxLvSQ
```


# Usage

- you can browse a single channel with: `https://your.yourss.instance/@jonnygiger`
- you can browse multiple channels in a single page: `https://your.yourss.instance/@jonnygiger,@lostangelus52`
- the original *RSS* feed can be access at `https://your.yourss.instance/api/rss/@jonnygiger`
- a *json* rss-like can be accessed at `https://your.yourss.instance/api/json/@jonnygiger`
- you will be redirected to the channel avatar with `https://your.yourss.instance/api/avatar/@jonnygiger`
- all your custom pages can be accessed to `https://your.yourss.instance/u/<user>`


# Extenal documentation:

- Youtube player API: https://developers.google.com/youtube/player_parameters