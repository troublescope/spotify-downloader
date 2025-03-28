"""
Genius Lyrics module.
"""

from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from spotdl.providers.lyrics.base import LyricsProvider
from spotdl.utils.config import GlobalConfig

__all__ = ["Genius"]


class Genius(LyricsProvider):
    """
    Genius lyrics provider class.
    """

    def __init__(self, access_token: str):
        """
        Init the lyrics provider search and set headers.
        """

        super().__init__()

        self.access_token = access_token

        self.headers.update(
            {
                "Authorization": f"Bearer {self.access_token}",
            }
        )

        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def get_results(self, name: str, artists: List[str], **_) -> Dict[str, str]:
        """
        Returns the results for the given song.

        ### Arguments
        - name: The name of the song.
        - artists: The artists of the song.
        - kwargs: Additional arguments.

        ### Returns
        - A dictionary with the results. (The key is the title and the value is the url.)
        """

        artists_str = ", ".join(artists)
        title = f"{name} - {artists_str}"

        search_response = self.session.get(
            "https://api.genius.com/search",
            params={"q": title},
            headers=self.headers,
            timeout=10,
            proxies=GlobalConfig.get_parameter("proxies"),
        )

        results: Dict[str, str] = {}
        for hit in search_response.json()["response"]["hits"]:
            results[hit["result"]["full_title"]] = hit["result"]["id"]

        return results

    def extract_lyrics(self, url: str, **_) -> Optional[str]:
        """
        Extracts the lyrics from the given url.

        ### Arguments
        - url: The url to extract the lyrics from.
        - kwargs: Additional arguments.

        ### Returns
        - The lyrics of the song or None if no lyrics were found.
        """

        url = f"https://api.genius.com/songs/{url}"
        song_response = self.session.get(
            url,
            headers=self.headers,
            timeout=10,
            proxies=GlobalConfig.get_parameter("proxies"),
        )
        url = song_response.json()["response"]["song"]["url"]

        soup = None
        counter = 0
        while counter < 4:
            genius_page_response = self.session.get(
                url,
                headers=self.headers,
                timeout=10,
                proxies=GlobalConfig.get_parameter("proxies"),
            )

            if not genius_page_response.ok:
                counter += 1
                continue

            soup = BeautifulSoup(
                genius_page_response.text.replace("<br/>", "\n"), "html.parser"
            )

            break

        if soup is None:
            return None

        lyrics_div = soup.select_one("div.lyrics")
        lyrics_containers = soup.select("div[class^=Lyrics__Container]")
        lyrics_container = soup.find("div", {"data-lyrics-container": "true"})

        # Get lyrics
        if lyrics_div:
            lyrics = lyrics_div.get_text()
        elif lyrics_containers:
            lyrics = "\n".join(con.get_text() for con in lyrics_containers)
        elif lyrics_container: 
            lyrics = lyrics_container.get_text("\n")
        else:
            return None

        if not lyrics:
            return None

        # Clean lyrics
        lyrics = lyrics.strip()

        # Remove desc at the beginning if it exists
        for to_remove in ["desc", "Desc"]:
            lyrics.replace(to_remove, "", 1)

        return lyrics
