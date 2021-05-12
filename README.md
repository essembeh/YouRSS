![Github](https://img.shields.io/github/tag/essembeh/youtube-rss-viewer.svg)
![PyPi](https://img.shields.io/pypi/v/youtube-rss-viewer.svg)
![Python](https://img.shields.io/pypi/pyversions/youtube-rss-viewer.svg)


# Youtube RSS viewer

> TL;DR; a minimal Youtube RSS feed viewer in your browser

Youtube RSS viewer is a simple service to browse in a single page the latest videos from Youtube channels you want.
You don't need a Youtube account to suscribe to channels, simply browse the latest videos by fetching the RSS feeds in a single page. No adds, no suggested videos, just the content you choose.

In social medias like Youtube, the keyword is *share*, I personnally think RSS feeds are a pretty good way to share content. Youtube RSS feeds let *users* choose how they want to see videos, with the app they want.

I simply wrote a minimal RSS client for web browsers.


# Install

## From Pypi

Install the latest release from [PyPI](https://pypi.org/project/youtube-rss-viewer/)
```sh
$ pip3 install --user -U youtube-rss-viewer
# run the webserver
$ FLASK_APP=youtube_rss_viewer flask run
# then open the page in your browser
$ xdg-open http://127.0.0.1:5000
```

## From Github

Install the latest version from the sources:

> This project uses [Poetry](https://python-poetry.org), ensure you have *Poetry* installed

```sh
$ pip3 install --user -U poetry
$ pip3 install --user git+https://github.com/essembeh/youtube-rss-viewer
# run the webserver
$ FLASK_APP=youtube_rss_viewer flask run
# then open the page in your browser
$ xdg-open http://127.0.0.1:5000
```

## From the sources

Install from the source
Clone the project
```sh
# ensure you have poetry installed
$ pip3 install --user -U poetry

# clone the repository
$ git clone https://github.com/essembeh/youtube-rss-viewer
$ cd youtube-rss-viewer

# create the virtualenv
$ poetry install

# run the app
$ poetry shell
(.venv) $ helloworld --help

# run the webserver
$ FLASK_APP=youtube_rss_viewer flask run
# then open the page in your browser
$ xdg-open http://127.0.0.1:5000

# to run the tests:
$ poetry run pytest tests
```

## From docker

Using Docker you can run the latest image build on the latest commit
```sh
$ docker run --name youtube -p 8000:8000 essembeh/youtube-rss-viewer
# then open the page in your browser
$ xdg-open http://127.0.0.1:5000
```