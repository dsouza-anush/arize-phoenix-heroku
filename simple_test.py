#!/usr/bin/env python3
import os
import sys
import requests
import json

print("Starting simple test script")
print(f"INFERENCE_URL: {os.environ.get('INFERENCE_URL')}")
print(f"INFERENCE_KEY: {os.environ.get('INFERENCE_KEY', '***')[:5]}...")

api_url = f"{os.environ.get('INFERENCE_URL', 'https://us.inference.heroku.com')}/v1/chat/completions"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {os.environ.get('INFERENCE_KEY', '')}"
}

payload = {
    "model": "claude-4-sonnet",
    "messages": [
        {"role": "user", "content": "Say hello in JSON format"}
    ],
    "max_tokens": 50
}

print(f"Sending request to {api_url}...")
try:
    response = requests.post(api_url, headers=headers, json=payload, timeout=30)
    print(f"Status code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")

print("Test completed")