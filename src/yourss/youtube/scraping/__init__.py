"""
Everything that depends on the shape of Youtube's pages lives in this package.

It does no I/O: it receives the HTML of a page or the JSON of an API response
and returns the models of the application. When Youtube changes something, the
fix belongs here and nowhere else:

* ``extract``: find the JSON documents embedded in the HTML
* ``channel``: channel metadata, tabs, continuation (glom specs at the top)
* ``items``: video and short items (one parser per known layout)
* ``walk``: generic search in a JSON payload
"""

from .channel import CHANNEL_TABS as CHANNEL_TABS
from .channel import ChannelPage as ChannelPage
from .channel import ChannelTab as ChannelTab
from .channel import Continuation as Continuation
from .channel import VideoPage as VideoPage
from .channel import parse_channel_page as parse_channel_page
from .channel import parse_continuation as parse_continuation
from .errors import ScrapingError as ScrapingError
