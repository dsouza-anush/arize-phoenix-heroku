#!/usr/bin/env python3
"""
Comprehensive API debugging script for Arize Phoenix + Heroku AI integration.
This script tests multiple aspects of the API integration to isolate issues.
"""

import os
import sys
import json
import time
import requests
from pprint import pprint
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("debug_api")

# API Configuration
INFERENCE_URL = os.environ.get("INFERENCE_URL", "https://us.inference.heroku.com")
INFERENCE_KEY = os.environ.get("INFERENCE_KEY", "")

if not INFERENCE_KEY:
    logger.error("INFERENCE_KEY environment variable not set")
    sys.exit(1)

def print_separator(title):
    """Print a section separator with title"""
    print("\n" + "="*80)
    print(f" {title}")
    print("="*80)

def direct_curl_equivalent():
    """Generate and show equivalent curl command for debugging"""
    print_separator("CURL COMMAND EQUIVALENT")
    
    curl_cmd = f"""curl -X POST \\
    {INFERENCE_URL}/v1/chat/completions \\
    -H "Content-Type: application/json" \\
    -H "Authorization: Bearer {INFERENCE_KEY[:5]}..." \\
    -d '{{
        "model": "claude-4-sonnet",
        "messages": [
            {{"role": "user", "content": "Say hello in plain text"}}
        ],
        "max_tokens": 50
    }}'"""
    
    print(curl_cmd)

def test_direct_api_call():
    """Make a direct API call to the Heroku AI endpoint"""
    print_separator("DIRECT API CALL")
    
    api_url = f"{INFERENCE_URL}/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {INFERENCE_KEY}"
    }
    
    payload = {
        "model": "claude-4-sonnet",
        "messages": [
            {"role": "user", "content": "Say hello in plain text"}
        ],
        "max_tokens": 50
    }
    
    logger.info(f"Sending request to {api_url}")
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        logger.info(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            logger.info("Response received successfully")
            
            # Pretty print the full response
            print("\nFull response:")
            pprint(data)
            
            # Extract and print specific fields that Phoenix might be looking for
            print("\nKey fields Phoenix might be using:")
            
            # Try different potential paths for content
            content_paths = [
                ("choices[0].message.content", extract_content_path(data, "choices[0].message.content")),
                ("choices[0].text", extract_content_path(data, "choices[0].text")),
                ("choices[0].message", extract_content_path(data, "choices[0].message"))
            ]
            
            for path, content in content_paths:
                print(f"{path}: {content}")
            
            return data
        else:
            logger.error(f"Error response: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Exception occurred: {e}")
        return None

def extract_content_path(data, path):
    """Extract content from a response using a path string like 'choices[0].message.content'"""
    try:
        parts = path.replace(']', '').replace('[', '.').split('.')
        result = data
        for part in parts:
            if part.isdigit():
                result = result[int(part)]
            else:
                result = result.get(part)
                if result is None:
                    return None
        return result
    except (KeyError, IndexError, TypeError, AttributeError) as e:
        return f"Error accessing path: {e}"

def verify_phoenix_expectations():
    """Check if the API response meets Phoenix expectations"""
    print_separator("PHOENIX EXPECTATIONS")
    
    # First get a real response
    response = test_direct_api_call()
    if not response:
        logger.error("Could not get API response to verify")
        return
    
    # Phoenix expected fields and formats based on documentation
    print("\nPhoenix might be looking for:")
    
    # Check for content field in various places
    content_found = False
    
    if response.get("choices") and len(response["choices"]) > 0:
        choice = response["choices"][0]
        
        # Check for message.content (standard OpenAI format)
        if "message" in choice and "content" in choice["message"]:
            print("✅ Found standard content at: choices[0].message.content")
            content_found = True
        else:
            print("❌ Missing standard content at: choices[0].message.content")
        
        # Check for text field (older format)
        if "text" in choice:
            print("✅ Found text field at: choices[0].text")
            content_found = True
        else:
            print("❌ Missing text field at: choices[0].text")
        
        # Check for full message object
        if "message" in choice:
            print(f"ℹ️ Message object: {choice['message']}")
        else:
            print("❌ Missing message object at: choices[0].message")
    else:
        print("❌ No choices array or it's empty")
    
    # Overall assessment
    if content_found:
        print("\n✅ API response contains content that Phoenix should be able to render")
    else:
        print("\n❌ API response is missing content fields that Phoenix might need")
        print("   Suggestion: Add response transformer to add required fields")

def suggest_phoenix_config():
    """Suggest Phoenix configuration based on API response analysis"""
    print_separator("SUGGESTED PHOENIX CONFIGURATION")
    
    # Test the API first
    response = test_direct_api_call()
    if not response:
        logger.error("Could not get API response to make suggestions")
        return
    
    # Generate suggestions based on the response format
    has_message_content = (response.get("choices") and len(response["choices"]) > 0 and 
                          "message" in response["choices"][0] and
                          "content" in response["choices"][0]["message"])
    
    print("\nSuggested environment variables:")
    
    # Basic configuration
    print("# Basic API configuration")
    print(f"export OPENAI_API_KEY=\"Bearer {INFERENCE_KEY[:5]}...\"")
    print(f"export OPENAI_BASE_URL=\"{INFERENCE_URL}/v1\"")
    print("export PHOENIX_MODEL_NAME=\"claude-4-sonnet\"")
    
    # Content extraction path
    print("\n# Content extraction configuration")
    if has_message_content:
        print("export PHOENIX_OPENAI_EXTRACT_CONTENT_PATH=\"choices[0].message.content\"")
    else:
        print("# Non-standard response format detected")
        print("export PHOENIX_OPENAI_EXTRACT_CONTENT_PATH=\"choices[0].text\"")
        print("# And possible transformer needed - see suggested transformer below")
    
    # Additional useful settings
    print("\n# Additional helpful settings")
    print("export PHOENIX_LLM_TRACE_MESSAGE_CONTENT=true")
    print("export PHOENIX_LLM_ENABLE_CONTENT_CAPTURE=true")
    print("export PHOENIX_TRACE_DEBUG=true")
    
    # Transformer suggestion if needed
    if not has_message_content:
        print("\n# Suggested response transformer in PHOENIX_OPENAI_CONFIG_FILE:")
        print(json.dumps({
            "api_base": "${INFERENCE_URL}/v1",
            "api_key": "Bearer ${INFERENCE_KEY}",
            "model": "${INFERENCE_MODEL_ID:-claude-4-sonnet}",
            "transformers": {
                "response": """
                if (response.choices && response.choices.length > 0) {
                  const choice = response.choices[0];
                  if (choice.message && choice.message.content) {
                    // Already has content in standard location
                    if (!choice.text) {
                      choice.text = choice.message.content;
                    }
                  } else if (choice.text) {
                    // Has text but not message.content
                    choice.message = {
                      role: "assistant",
                      content: choice.text
                    };
                  } else {
                    // Has neither - create empty values
                    const content = "";
                    choice.text = content;
                    choice.message = {
                      role: "assistant",
                      content: content
                    };
                  }
                }
                return response;
                """
            }
        }, indent=2))

def test_specific_request_formats():
    """Test various request formats to see which ones work"""
    print_separator("TESTING VARIOUS REQUEST FORMATS")
    
    test_cases = [
        {
            "name": "Standard OpenAI format",
            "payload": {
                "model": "claude-4-sonnet",
                "messages": [
                    {"role": "user", "content": "Say hello"}
                ],
                "max_tokens": 50
            }
        },
        {
            "name": "With response_format: text",
            "payload": {
                "model": "claude-4-sonnet",
                "messages": [
                    {"role": "user", "content": "Say hello"}
                ],
                "max_tokens": 50,
                "response_format": {"type": "text"}
            }
        },
        {
            "name": "With stream: true",
            "payload": {
                "model": "claude-4-sonnet",
                "messages": [
                    {"role": "user", "content": "Say hello"}
                ],
                "max_tokens": 50,
                "stream": True
            }
        }
    ]
    
    api_url = f"{INFERENCE_URL}/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {INFERENCE_KEY}"
    }
    
    for test_case in test_cases:
        print(f"\n\nTesting: {test_case['name']}")
        print("-" * 40)
        
        try:
            response = requests.post(
                api_url, 
                headers=headers, 
                json=test_case['payload'],
                timeout=30,
                stream=test_case['payload'].get('stream', False)
            )
            
            print(f"Status code: {response.status_code}")
            
            if response.status_code == 200:
                if test_case['payload'].get('stream', False):
                    print("Streaming response (first few chunks):")
                    chunk_count = 0
                    for chunk in response.iter_lines():
                        if chunk:
                            print(f"Chunk: {chunk.decode('utf-8')}")
                            chunk_count += 1
                            if chunk_count >= 3:
                                print("... (more chunks available)")
                                break
                else:
                    data = response.json()
                    print("Response excerpt:")
                    if "choices" in data and len(data["choices"]) > 0:
                        choice = data["choices"][0]
                        if "message" in choice and "content" in choice["message"]:
                            print(f"Content: {choice['message']['content']}")
                        else:
                            print("No content found in response")
                            print(f"Full choice object: {choice}")
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    print("Arize Phoenix + Heroku AI Debug Script")
    print(f"Testing API: {INFERENCE_URL}")
    
    # Run the test functions
    direct_curl_equivalent()
    verify_phoenix_expectations()
    suggest_phoenix_config()
    test_specific_request_formats()
    
    print("\nDebug script completed")