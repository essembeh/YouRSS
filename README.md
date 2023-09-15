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
