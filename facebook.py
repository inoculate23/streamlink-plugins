import logging
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents
from streamlink.stream import DASHStream, HTTPStream
from streamlink.utils import parse_json

log = logging.getLogger(__name__)


class Facebook(Plugin):
    pattern = r'https?://(?:www\.)?facebook\.com/[^/]+/(posts|videos)'

    _src_re = re.compile(r'''(sd|hd)_src["']?\s*:\s*(?P<quote>["'])(?P<url>.+?)(?P=quote)''')
    _playlist_re = re.compile(r'''video:\[({url:".+?}\])''')
    _plurl_re = re.compile(r'''url:"(.*?)"''')

    def _get_streams(self):
        res = self.session.http.get(self.url, headers={"User-Agent": useragents.CHROME})

        streams = {}
        vod_urls = set([])

        for match in self._src_re.finditer(res.text):
            stream_url = match.group("url")
            if "\\/" in stream_url:
                # if the URL is json encoded, decode it
                stream_url = parse_json("\"{}\"".format(stream_url))
            if ".mpd" in stream_url:
                streams.update(DASHStream.parse_manifest(self.session, stream_url))
            elif ".mp4" in stream_url:
                streams[match.group(1)] = HTTPStream(self.session, stream_url)
                vod_urls.add(stream_url)
            else:
                log.debug("Non-dash/mp4 stream: {0}".format(stream_url))

        if streams:
            return streams

        # fallback on to playlist
        log.debug("Falling back to playlist regex")
        match = self._playlist_re.search(res.text)
        playlist = match and match.group(1)
        if playlist:
            for url in dict(url.group(1) for url in self._plurl_re.finditer(playlist)):
                if url not in vod_urls:
                    streams["sd"] = HTTPStream(self.session, url)

        return streams


__plugin__ = Facebook

