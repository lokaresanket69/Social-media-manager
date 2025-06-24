import requests
import os
import json

def post_to_twitter(account, content):
    # Load bearer token
    with open(account['credential_path']) as f:
        token = f.read().strip()
    tweet_text = (content['description'] or '') + ' ' + (content['hashtags'] or '')
    # Twitter API v2 endpoint for tweet creation
    url = 'https://api.twitter.com/2/tweets'
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    data = {
        'text': tweet_text
    }
    response = requests.post(url, headers=headers, json=data)
    if not response.ok:
        raise Exception('Twitter API error: ' + response.text)
    return response.json() 