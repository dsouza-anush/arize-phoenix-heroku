#!/usr/bin/env python3
"""
Compare API response formats with what Phoenix expects.
This script makes requests to the API and analyzes the responses in detail.
"""

import os
import sys
import json
import requests
from pprint import pprint
import re
import time
import logging
import tempfile

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("response_analyzer")

# API Configuration
INFERENCE_URL = os.environ.get("INFERENCE_URL", "https://us.inference.heroku.com")
INFERENCE_KEY = os.environ.get("INFERENCE_KEY", "")

if not INFERENCE_KEY:
    logger.error("INFERENCE_KEY environment variable not set")
    sys.exit(1)

def print_header(title):
    """Print a section header"""
    print("\n" + "="*80)
    print(f" {title}")
    print("="*80)

def make_api_request(prompt="Say hello", model="claude-4-sonnet", options=None):
    """Make an API request with specified parameters"""
    api_url = f"{INFERENCE_URL}/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {INFERENCE_KEY}"
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 50
    }
    
    # Add any additional options
    if options:
        payload.update(options)
    
    logger.info(f"Sending request to {api_url}")
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        logger.info(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Error response: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Exception occurred: {e}")
        return None

def dump_response(response, description):
    """Save response to a temp file for further analysis"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(response, f, indent=2)
        print(f"\nSaved {description} to: {f.name}")

def response_schema_analysis():
    """Analyze the schema of the API response"""
    print_header("RESPONSE SCHEMA ANALYSIS")
    
    response = make_api_request()
    if not response:
        print("Could not get API response for analysis")
        return
    
    # Save raw response for reference
    dump_response(response, "raw API response")
    
    # Identify the structure and key fields
    print("\nResponse structure:")
    keys = list(response.keys())
    print(f"Top-level keys: {keys}")
    
    # Check for expected fields based on OpenAI standard
    expected_fields = ["id", "object", "created", "model", "choices", "usage"]
    print("\nChecking for expected OpenAI-compatible fields:")
    for field in expected_fields:
        if field in response:
            print(f"✅ {field}: {type(response[field])}")
        else:
            print(f"❌ {field}: Missing")
    
    # Analyze the choices array
    if "choices" in response and isinstance(response["choices"], list) and response["choices"]:
        choice = response["choices"][0]
        print("\nFirst choice structure:")
        choice_keys = list(choice.keys())
        print(f"Choice keys: {choice_keys}")
        
        # Check for message field
        if "message" in choice:
            message = choice["message"]
            print(f"Message: {message}")
        else:
            print("❌ No message field in choice")
        
        # Check for text field
        if "text" in choice:
            print(f"Text: {choice['text']}")
        else:
            print("❌ No text field in choice")
    else:
        print("\n❌ No valid choices array found")

def phoenix_request_analysis():
    """Analyze what a Phoenix-initiated request would look like"""
    print_header("PHOENIX REQUEST ANALYSIS")
    
    # Extract Phoenix configuration from environment
    model = os.environ.get("PHOENIX_MODEL_NAME", "claude-4-sonnet")
    extract_path = os.environ.get("PHOENIX_OPENAI_EXTRACT_CONTENT_PATH", "choices[0].message.content")
    disable_response_format = os.environ.get("PHOENIX_OPENAI_DISABLE_RESPONSE_FORMAT", "").lower() == "true"
    
    # Construct Phoenix-style request
    options = {}
    if not disable_response_format:
        options["response_format"] = {"type": "text"}
    
    print(f"Using model: {model}")
    print(f"Using extract path: {extract_path}")
    print(f"Disable response format: {disable_response_format}")
    print(f"Additional options: {options}")
    
    # Make the request
    response = make_api_request(model=model, options=options)
    
    if not response:
        print("Could not get API response")
        return
    
    # Extract content based on Phoenix path
    try:
        parts = extract_path.replace(']', '').replace('[', '.').split('.')
        content = response
        path_trace = []
        
        print("\nContent extraction trace:")
        for part in parts:
            path_trace.append(part)
            print(f"Processing path part: {part}")
            try:
                if part.isdigit():
                    idx = int(part)
                    if isinstance(content, list) and idx < len(content):
                        content = content[idx]
                        print(f"  Found list item at index {idx}")
                    else:
                        print(f"  ❌ Error: Cannot access index {idx} in {content}")
                        content = None
                        break
                else:
                    if isinstance(content, dict) and part in content:
                        content = content[part]
                        print(f"  Found dict key '{part}' with value: {content}")
                    else:
                        print(f"  ❌ Error: Key '{part}' not found in {content}")
                        content = None
                        break
            except Exception as e:
                print(f"  ❌ Error processing path part '{part}': {e}")
                content = None
                break
        
        print("\nExtraction result:")
        if content is not None:
            print(f"✅ Successfully extracted content: {content}")
        else:
            print("❌ Failed to extract content")
            
            # Suggest alternatives
            print("\nAlternative paths to try:")
            alt_paths = [
                "choices[0].text",
                "choices[0].message",
                "choices[0].message.content"
            ]
            
            for alt_path in alt_paths:
                if alt_path == extract_path:
                    continue
                    
                parts = alt_path.replace(']', '').replace('[', '.').split('.')
                alt_content = response
                success = True
                
                for part in parts:
                    try:
                        if part.isdigit():
                            alt_content = alt_content[int(part)]
                        else:
                            alt_content = alt_content.get(part)
                            if alt_content is None:
                                success = False
                                break
                    except (KeyError, IndexError, TypeError):
                        success = False
                        break
                
                if success:
                    print(f"✅ {alt_path}: {alt_content}")
                else:
                    print(f"❌ {alt_path}: Not found")
    
    except Exception as e:
        print(f"Error during content extraction: {e}")

def test_response_format_options():
    """Test how different response_format options affect the response"""
    print_header("TESTING RESPONSE FORMAT OPTIONS")
    
    format_options = [
        {"name": "No response_format (default)", "options": {}},
        {"name": "response_format: text", "options": {"response_format": {"type": "text"}}},
        {"name": "response_format: json_object", "options": {"response_format": {"type": "json_object"}}}
    ]
    
    for option in format_options:
        print(f"\nTesting: {option['name']}")
        response = make_api_request(
            prompt="Please respond with a simple hello.",
            options=option["options"]
        )
        
        if not response:
            print("No response received")
            continue
        
        # Check choices structure
        if "choices" in response and response["choices"]:
            choice = response["choices"][0]
            
            # Print choice structure
            print(f"Choice keys: {list(choice.keys())}")
            
            # Check for content
            content = None
            if "message" in choice and "content" in choice["message"]:
                content = choice["message"]["content"]
                print(f"Found content in choices[0].message.content: {content}")
            elif "text" in choice:
                content = choice["text"]
                print(f"Found content in choices[0].text: {content}")
            else:
                print("No content field found")
                print(f"Full choice object: {choice}")
        else:
            print("No choices array or it's empty")
        
        print("-" * 40)

def trace_phoenix_extraction_steps():
    """Emulate Phoenix's content extraction steps"""
    print_header("PHOENIX CONTENT EXTRACTION SIMULATION")
    
    # Make API request
    response = make_api_request(prompt="Say hello")
    if not response:
        print("Could not get API response")
        return
    
    # Get configuration that Phoenix would use
    extract_path = os.environ.get("PHOENIX_OPENAI_EXTRACT_CONTENT_PATH", "choices[0].message.content")
    
    # Define the extraction flow
    extraction_steps = [
        "1. Phoenix receives API response",
        f"2. Checks for content at path: {extract_path}",
        "3. If content is found, it's used for rendering",
        "4. If not found, falls back to other fields like 'text'",
        "5. If still not found, may return empty response"
    ]
    
    print("Phoenix content extraction flow:")
    for step in extraction_steps:
        print(f"  {step}")
    
    print("\nSimulating extraction process:")
    print("Response received ✓")
    
    # Try primary extraction path
    try:
        parts = extract_path.replace(']', '').replace('[', '.').split('.')
        content = response
        for part in parts:
            if part.isdigit():
                content = content[int(part)]
            else:
                content = content.get(part)
                if content is None:
                    break
        
        if content is not None:
            print(f"✅ Primary path successful: {extract_path} = {content}")
        else:
            print(f"❌ Primary path failed: {extract_path}")
            
            # Try fallback to text
            if ("choices" in response and response["choices"] and 
                isinstance(response["choices"][0], dict) and
                "text" in response["choices"][0]):
                text = response["choices"][0]["text"]
                print(f"✅ Fallback successful: choices[0].text = {text}")
            else:
                print("❌ Fallback to text failed")
                print("❌ Content extraction failed completely")
                
                # Detailed dump of response structure for debugging
                print("\nResponse structure:")
                if "choices" in response and response["choices"]:
                    print(f"choices[0] keys: {list(response['choices'][0].keys())}")
                    if "message" in response["choices"][0]:
                        print(f"message keys: {list(response['choices'][0]['message'].keys())}")
                else:
                    print("No choices array found")
    except Exception as e:
        print(f"❌ Error during extraction: {e}")
        
    # Finally, show what would be displayed
    try:
        display_content = None
        # Try primary path
        try:
            parts = extract_path.replace(']', '').replace('[', '.').split('.')
            content = response
            for part in parts:
                if part.isdigit():
                    content = content[int(part)]
                else:
                    content = content.get(part)
                    if content is None:
                        break
            display_content = content
        except:
            pass
        
        # Try fallbacks if primary failed
        if display_content is None:
            if ("choices" in response and response["choices"] and
                isinstance(response["choices"][0], dict)):
                # Try text field
                if "text" in response["choices"][0]:
                    display_content = response["choices"][0]["text"]
                # Try message
                elif "message" in response["choices"][0]:
                    message = response["choices"][0]["message"]
                    if isinstance(message, dict) and "content" in message:
                        display_content = message["content"]
        
        print("\nFinal rendering result:")
        if display_content is not None:
            print(f"✅ Content displayed: {display_content}")
        else:
            print("❌ No content to display")
    except Exception as e:
        print(f"❌ Error determining display content: {e}")

if __name__ == "__main__":
    print("API Response Format Analyzer")
    
    # Run analysis functions
    response_schema_analysis()
    phoenix_request_analysis()
    test_response_format_options()
    trace_phoenix_extraction_steps()
    
    print("\nAnalysis completed")