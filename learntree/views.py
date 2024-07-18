from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework import status

import requests
import html
import html.parser

import re
import logging
import json

import google.generativeai as genai
class GeminiLLM:
    _isConfigured: bool = False

    def __init__(self) -> None:
        if GeminiLLM._isConfigured:
            self.model = genai.GenerativeModel(model_name='gemini-pro')
            return
        
        with open('gemini_api_key.txt') as keyFile:
            key = keyFile.read().strip()

        genai.configure(api_key=key)
        GeminiLLM._isConfigured = True

        self.model = genai.GenerativeModel(model_name='gemini-pro')
    
    def prompt(self, prompt: str) -> str:
        return self.model.generate_content(prompt).text

def get_captions_url(responseText: str) -> str:
    CAPTIONS_KEY = 'captionTracks'
    URL_KEY = 'baseUrl'

    captionsTextIdx = responseText.index(CAPTIONS_KEY)
    captionsUrlIdx = responseText.index(URL_KEY, captionsTextIdx + len(CAPTIONS_KEY))
    captionsUrlIdx = responseText.index("\"", captionsUrlIdx + len(URL_KEY) + 1)

    captionsUrl = ""
    for char in responseText[captionsUrlIdx + 1:]:
        if char == "\"":
            break

        captionsUrl += char

    return captionsUrl.strip().encode().decode("unicode-escape")

def parse_captions(responseText: str, textConnector: str = " ") -> str:
    class CaptionsResponseParser(html.parser.HTMLParser):
        def __init__(self, *, convert_charrefs: bool = True) -> None:
            super().__init__(convert_charrefs=convert_charrefs)
            self.captions = ""

        def handle_data(self, data: str) -> None:
            self.captions += data + textConnector

    parser = CaptionsResponseParser()
    parser.feed(responseText)

    # slice operation removes textConnector appended to string at the very end
    return html.unescape(parser.captions[:len(parser.captions) - len(textConnector)])

def create_video_prompt(captions: str, isJson: bool = True) -> str:
    prompt = "List 4 to 5 topics that must be understood before watching this video. "\
             "Only include topics that aren't learned during this video. "\
             
    if isJson:
        prompt += "Format the responses in JSON so that the topics to learn beforehand "\
                  "are in a topics property, which is a list of strings. However, do not "\
                  "include ```json and ``` at the start and end of your response respectively. "
                  
    else:
        prompt += "Format the responses as bullet points so that the topics to learn beforehand are "\
                  "included in the list. "

    prompt += 'Each topic is limited to 20 characters.\n Video Captions: ' + captions

    return prompt

model = GeminiLLM()

logging.basicConfig(filename='internal_errors.txt', filemode='a')
logger = logging.getLogger(__name__)

@api_view(['GET'])
def generate_topics(request):
    if 'url' not in request.GET:
        return JsonResponse({'error': 'no URL provided as url query parameter'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        url = request.GET.get('url')

        youtubeVidUrlRegex = re.compile(r'(https:\/\/)?(www\.)?youtube\.com\/watch\?v=.+')
        if not bool(youtubeVidUrlRegex.match(url)):
            return JsonResponse({'error': 'URL provided is invalid'}, status=status.HTTP_400_BAD_REQUEST)
        
        httpsRegex = re.compile(r'https:\/\/')
        if not bool(httpsRegex.match(url)):
            url = 'https://' + url

        captionsUrl = get_captions_url(requests.get(url).text)
        parsedCaptions = parse_captions(requests.get(captionsUrl).text)

        response = model.prompt(create_video_prompt(parsedCaptions, isJson=True))
        response = json.loads(response)

        return JsonResponse({'topics': response['topics']}, status=status.HTTP_200_OK)

    except requests.exceptions.MissingSchema as e:
        return JsonResponse({'error': 'URL provided is invalid'}, status=status.HTTP_400_BAD_REQUEST)
    
    except ValueError as e:
        return JsonResponse({'error': 'youtube video is invalid'}, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        with open('internal_errors.txt', 'a') as errorsFile:
            errorsFile.write('-----------EXCEPTION-----------\n')
        logger.exception(e)
        with open('internal_errors.txt', 'a') as errorsFile:
            errorsFile.write('-----------END EXCEPTION-----------\n\n')

        return JsonResponse({'error': 'an internal error occurred'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)