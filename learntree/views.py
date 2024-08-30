from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework import status

import requests
import urllib
import urllib.parse

import re
import logging
import json

from . import captions
from . import llm

def create_video_prompt(captions: str, shouldFormatInJson: bool = True) -> str:
    prompt = "List 4 to 5 topics that must be understood before watching this video. "\
             "Only include topics that aren't learned during this video. "\
             
    if shouldFormatInJson:
        prompt += "Format the responses in JSON so that the topics to learn beforehand "\
                  "are in a topics property, which is a list of strings. However, do not "\
                  "include ```json and ``` at the start and end of your response respectively. "
                  
    else:
        prompt += "Format the responses as bullet points so that the topics to learn beforehand are "\
                  "included in the list. "

    prompt += 'Each topic is limited to 20 characters.\n Video Captions: ' + captions

    return prompt

model = llm.GeminiLLM()

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

        captionsUrl = captions.get_captions_url(requests.get(url).text)
        if urllib.parse.parse_qs(urllib.parse.urlparse(captionsUrl).query)['lang'][0] != 'en':
            return JsonResponse({'error': 'Video caption language is not English'},
                                status=status.HTTP_501_NOT_IMPLEMENTED)
        
        parsedCaptions = captions.parse_captions(requests.get(captionsUrl).text)
        response = model.prompt(create_video_prompt(parsedCaptions, shouldFormatInJson=True))
        response = json.loads(response)

        return JsonResponse({'topics': response['topics']}, status=status.HTTP_200_OK)

    except requests.exceptions.MissingSchema as e:
        return JsonResponse({'error': 'URL provided is invalid'}, status=status.HTTP_400_BAD_REQUEST)
    
    except ValueError as e:
        return JsonResponse({'error': 'Given YouTube video is invalid (ie. no longer exists, unlisted, etc.)'},
                            status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        with open('internal_errors.txt', 'a') as errorsFile:
            errorsFile.write('-----------EXCEPTION-----------\n')
        logger.exception(e)
        with open('internal_errors.txt', 'a') as errorsFile:
            errorsFile.write('-----------END EXCEPTION-----------\n\n')

        return JsonResponse({'error': 'An internal error occurred'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)