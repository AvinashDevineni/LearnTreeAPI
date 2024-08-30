import html
import html.parser

def get_captions_url(ytVideoResponse: str) -> str:
    CAPTIONS_KEY = 'captionTracks'
    URL_KEY = 'baseUrl'

    captionsTextIdx = ytVideoResponse.index(CAPTIONS_KEY)
    captionsUrlIdx = ytVideoResponse.index(URL_KEY, captionsTextIdx + len(CAPTIONS_KEY))
    captionsUrlIdx = ytVideoResponse.index("\"", captionsUrlIdx + len(URL_KEY) + 1)

    captionsUrl = ""
    for char in ytVideoResponse[captionsUrlIdx + 1:]:
        if char == "\"":
            break

        captionsUrl += char

    return captionsUrl.strip().encode().decode("unicode-escape")

def parse_captions(captionsResponse: str, textConnector: str = " ") -> str:
    class CaptionsResponseParser(html.parser.HTMLParser):
        def __init__(self, *, convert_charrefs: bool = True) -> None:
            super().__init__(convert_charrefs=convert_charrefs)
            self.captions = ""

        def handle_data(self, data: str) -> None:
            self.captions += data + textConnector

    parser = CaptionsResponseParser()
    parser.feed(captionsResponse)

    # slice operation removes textConnector appended to string at the very end
    return html.unescape(parser.captions[:len(parser.captions) - len(textConnector)])