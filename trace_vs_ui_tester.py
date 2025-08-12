#!/usr/bin/env python3
"""
Test trace capture vs. UI rendering to isolate the issue.
This script creates a Phoenix trace, accesses it via API, and compares what's captured vs displayed.
"""

import os
import sys
import json
import time
import requests
import logging
from pprint import pprint
import argparse
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("trace_tester")

# Default configuration
INFERENCE_URL = os.environ.get("INFERENCE_URL", "https://us.inference.heroku.com")
INFERENCE_KEY = os.environ.get("INFERENCE_KEY", "")
PHOENIX_URL = os.environ.get("PHOENIX_URL", "http://localhost:6006")

def print_header(title):
    """Print a section header"""
    print("\n" + "="*80)
    print(f" {title}")
    print("="*80)

def make_api_request(prompt="Say hello"):
    """Make an API request to the Heroku AI endpoint"""
    api_url = f"{INFERENCE_URL}/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {INFERENCE_KEY}"
    }
    
    payload = {
        "model": "claude-4-sonnet",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 100
    }
    
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

def create_phoenix_trace():
    """Create a trace in Phoenix by making an instrumented API call"""
    print_header("CREATING PHOENIX TRACE")
    
    try:
        # Try to import Phoenix
        from phoenix.trace.openinference import enable_openinference
        from phoenix.trace import init_tracing
        
        # Initialize Phoenix tracing
        print("Initializing Phoenix tracing...")
        enable_openinference()
        init_tracing()
        
        # Import OpenAI client for tracing
        from phoenix.trace import get_tracer
        import openai
        
        # Configure OpenAI client
        openai.api_key = f"Bearer {INFERENCE_KEY}"
        openai.base_url = f"{INFERENCE_URL}/v1"
        
        # Create a Phoenix trace
        with get_tracer(__name__).start_as_current_span("test_trace") as span:
            # Record trace start time
            trace_start = datetime.now()
            span.set_attribute("test.start_time", trace_start.isoformat())
            
            # Make the API call
            print("Making API call with tracing...")
            completion = openai.chat.completions.create(
                model="claude-4-sonnet",
                messages=[
                    {"role": "user", "content": "Say hello, this is a test trace"}
                ],
                max_tokens=100
            )
            
            # Extract response content
            try:
                content = completion.choices[0].message.content
                print(f"Response content: {content}")
            except Exception as e:
                print(f"Error extracting content: {e}")
                content = None
            
            # Record trace end time
            trace_end = datetime.now()
            span.set_attribute("test.end_time", trace_end.isoformat())
            
            return {
                "start_time": trace_start.isoformat(),
                "end_time": trace_end.isoformat(),
                "content": content
            }
    
    except ImportError as e:
        print(f"Failed to import Phoenix: {e}")
        print("Falling back to direct API call without tracing...")
        
        response = make_api_request("Say hello, this is a test trace")
        if response:
            try:
                content = response["choices"][0]["message"]["content"]
                return {
                    "start_time": datetime.now().isoformat(),
                    "end_time": datetime.now().isoformat(),
                    "content": content,
                    "no_tracing": True
                }
            except:
                return {
                    "error": "Could not extract content",
                    "response": response
                }
        else:
            return {"error": "API request failed"}

def query_phoenix_traces(start_time_iso=None):
    """Query Phoenix API for recent traces"""
    print_header("QUERYING PHOENIX TRACES")
    
    # Start time filter (5 minutes before if not provided)
    if not start_time_iso:
        import datetime
        five_min_ago = datetime.datetime.now() - datetime.timedelta(minutes=5)
        start_time_iso = five_min_ago.isoformat()
    
    print(f"Looking for traces since: {start_time_iso}")
    
    # Query Phoenix API
    api_url = f"{PHOENIX_URL}/api/v1/llm-traces"
    params = {
        "timestamp_gte": start_time_iso,
        "limit": 5,
        "skip": 0
    }
    
    try:
        print(f"Querying Phoenix API at {api_url}")
        response = requests.get(api_url, params=params)
        
        if response.status_code == 200:
            traces = response.json()
            print(f"Found {len(traces)} traces")
            return traces
        else:
            print(f"Error querying Phoenix API: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"Exception querying Phoenix API: {e}")
        return None

def get_trace_details(trace_id):
    """Get details for a specific trace"""
    print_header(f"TRACE DETAILS: {trace_id}")
    
    # Query trace endpoint
    api_url = f"{PHOENIX_URL}/api/v1/llm-traces/{trace_id}"
    
    try:
        print(f"Querying trace at {api_url}")
        response = requests.get(api_url)
        
        if response.status_code == 200:
            trace = response.json()
            return trace
        else:
            print(f"Error querying trace: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"Exception querying trace: {e}")
        return None

def compare_response_with_trace(api_response, trace_data):
    """Compare raw API response with what's captured in the trace"""
    print_header("COMPARING API RESPONSE WITH TRACE DATA")
    
    # Extract content from API response
    api_content = None
    if api_response and "choices" in api_response and api_response["choices"]:
        choice = api_response["choices"][0]
        if "message" in choice and "content" in choice["message"]:
            api_content = choice["message"]["content"]
        elif "text" in choice:
            api_content = choice["text"]
    
    # Extract content from trace
    trace_content = None
    if trace_data:
        # Try different paths based on Phoenix trace structure
        if "outputs" in trace_data:
            outputs = trace_data["outputs"]
            if outputs and "content" in outputs:
                trace_content = outputs["content"]
            elif outputs and "choices" in outputs and outputs["choices"]:
                choice = outputs["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    trace_content = choice["message"]["content"]
                elif "text" in choice:
                    trace_content = choice["text"]
        
        # Try metadata for content
        if not trace_content and "metadata" in trace_data:
            metadata = trace_data["metadata"]
            if "output_content" in metadata:
                trace_content = metadata["output_content"]
    
    # Compare content
    print("API Response Content:")
    print(f"{api_content}")
    print("\nTrace Content:")
    print(f"{trace_content}")
    
    if api_content == trace_content:
        print("\n✅ Content matches!")
    else:
        print("\n❌ Content doesn't match!")
        print("\nDifferences:")
        if not api_content:
            print("- API content is missing")
        if not trace_content:
            print("- Trace content is missing")
        else:
            print("- Content differs")

def test_ui_rendering_flow():
    """Test the flow of how the UI renders response content"""
    print_header("TESTING UI RENDERING FLOW")
    
    # Create a trace
    trace_result = create_phoenix_trace()
    if "error" in trace_result:
        print(f"Failed to create trace: {trace_result['error']}")
        return
    
    # Wait a moment for the trace to be processed
    print("Waiting for trace to be processed...")
    time.sleep(2)
    
    # Query recent traces
    traces = query_phoenix_traces(trace_result.get("start_time"))
    if not traces:
        print("No traces found")
        return
    
    # Get the most recent trace
    if traces:
        trace = traces[0]
        trace_id = trace.get("id")
        print(f"Found trace: {trace_id}")
        
        # Get trace details
        trace_details = get_trace_details(trace_id)
        if not trace_details:
            print("Could not get trace details")
            return
        
        # Make the same API call directly
        print("Making direct API call for comparison...")
        api_response = make_api_request("Say hello, this is a test trace")
        
        # Compare response with trace
        compare_response_with_trace(api_response, trace_details)
        
        # Check for UI-specific fields
        print("\nChecking for UI-specific fields:")
        ui_fields = [
            "content", "message", "text", "choices[].text", "choices[].message.content"
        ]
        
        for field in ui_fields:
            print(f"\nChecking field: {field}")
            parts = field.replace("[]", "[0]").replace("]", "").replace("[", ".").split(".")
            
            # Check in trace output
            output_value = trace_details.get("outputs", {})
            for part in parts:
                if part.isdigit():
                    try:
                        output_value = output_value[int(part)]
                    except (IndexError, TypeError):
                        output_value = None
                        break
                else:
                    output_value = output_value.get(part) if isinstance(output_value, dict) else None
                    if output_value is None:
                        break
            
            if output_value is not None:
                print(f"✅ Found in trace outputs: {output_value}")
            else:
                print("❌ Not found in trace outputs")

def test_with_custom_transformer():
    """Test with a custom transformer added to the API response"""
    print_header("TESTING WITH CUSTOM TRANSFORMER")
    
    # Make direct API call
    api_url = f"{INFERENCE_URL}/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {INFERENCE_KEY}"
    }
    
    payload = {
        "model": "claude-4-sonnet",
        "messages": [
            {"role": "user", "content": "Say hello with custom transformer"}
        ],
        "max_tokens": 100
    }
    
    print("Making API call...")
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        if response.status_code != 200:
            print(f"API call failed: {response.status_code}")
            print(response.text)
            return
        
        # Get the response
        api_response = response.json()
        
        # Apply transformer manually
        print("\nApplying transformer to response...")
        transformed = api_response.copy()
        
        # Add text field if needed
        if ("choices" in transformed and transformed["choices"] and 
            "message" in transformed["choices"][0] and 
            "content" in transformed["choices"][0]["message"]):
            content = transformed["choices"][0]["message"]["content"]
            transformed["choices"][0]["text"] = content
            print(f"Added text field: {content}")
        
        # Compare original and transformed
        print("\nOriginal Response Structure:")
        if "choices" in api_response and api_response["choices"]:
            pprint(api_response["choices"][0])
        
        print("\nTransformed Response Structure:")
        if "choices" in transformed and transformed["choices"]:
            pprint(transformed["choices"][0])
        
        # Now try to create a Phoenix trace with this transformed response
        try:
            print("\nCreating Phoenix trace with transformed response...")
            from phoenix.trace.llm import openai as phoenix_openai
            
            # Try to extract content using Phoenix's function
            print("Extracting content from original response:")
            original_content = phoenix_openai.extract_content_from_openai_chat_completion(api_response)
            print(f"Original content: {original_content}")
            
            print("\nExtracting content from transformed response:")
            transformed_content = phoenix_openai.extract_content_from_openai_chat_completion(transformed)
            print(f"Transformed content: {transformed_content}")
            
            return {
                "original": original_content,
                "transformed": transformed_content
            }
        except ImportError:
            print("Phoenix package not found, cannot test with Phoenix functions")
            return {
                "error": "Phoenix package not found"
            }
    except Exception as e:
        print(f"Error testing with custom transformer: {e}")
        return {
            "error": str(e)
        }

if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser(description="Test Phoenix trace capture vs UI rendering")
    parser.add_argument("--phoenix-url", default=PHOENIX_URL, help="Phoenix server URL")
    parser.add_argument("--inference-url", default=INFERENCE_URL, help="Inference API URL")
    args = parser.parse_args()
    
    # Update global variables from args
    PHOENIX_URL = args.phoenix_url
    INFERENCE_URL = args.inference_url
    
    if not INFERENCE_KEY:
        print("INFERENCE_KEY environment variable not set")
        sys.exit(1)
    
    print(f"Phoenix URL: {PHOENIX_URL}")
    print(f"Inference URL: {INFERENCE_URL}")
    
    # Run tests
    test_ui_rendering_flow()
    test_with_custom_transformer()
    
    print("\nTrace vs UI testing completed")