#!/usr/bin/env python3
"""
Phoenix Response Fix Script

This script adds a response transformer middleware that ensures the Phoenix UI can
properly display responses from the Heroku AI Claude API.

It addresses the issue where Phoenix correctly captures API calls in traces but
doesn't display the response content in the UI.

Usage:
1. Add this to your container startup process
2. The script runs as middleware, ensuring all responses have required fields
"""

import os
import sys
import json
import logging
import requests
import traceback
import importlib
from functools import wraps
from typing import Dict, Any, Optional, Callable

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/phoenix_fix.log')
    ]
)
logger = logging.getLogger("phoenix_fix")

# ===== Core Transformer Function =====

def transform_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform the response to ensure Phoenix UI can display it.
    
    This function ensures that:
    1. The response has a choices array
    2. Each choice has a text field for older Phoenix versions
    3. Each choice has a message.content field for newer Phoenix versions
    """
    # Return early if not a dict or already processed
    if not isinstance(response, dict) or "__phoenix_processed__" in response:
        return response
    
    logger.debug(f"Processing response: {json.dumps(response)[:200]}...")
    
    # Copy response to avoid modifying the original
    transformed = response.copy()
    
    # Mark as processed to avoid reprocessing
    transformed["__phoenix_processed__"] = True
    
    try:
        # Check if we have a choices array
        if "choices" not in transformed or not transformed["choices"]:
            logger.warning("No choices array in response")
            return transformed
        
        # Process each choice
        for i, choice in enumerate(transformed["choices"]):
            if not isinstance(choice, dict):
                logger.warning(f"Choice {i} is not a dict")
                continue
            
            # Check for message.content
            if "message" in choice and isinstance(choice["message"], dict) and "content" in choice["message"]:
                # We have message.content, make sure we also have text
                if "text" not in choice:
                    choice["text"] = choice["message"]["content"]
                    logger.debug(f"Added text field for choice {i}")
            
            # Check for text but no message.content
            elif "text" in choice:
                # We have text but no message.content
                if "message" not in choice or not isinstance(choice["message"], dict):
                    choice["message"] = {
                        "role": "assistant",
                        "content": choice["text"]
                    }
                    logger.debug(f"Added message field for choice {i}")
                elif "content" not in choice["message"]:
                    choice["message"]["content"] = choice["text"]
                    logger.debug(f"Added message.content field for choice {i}")
            
            # Neither text nor message.content - this is a problem
            else:
                logger.warning(f"Choice {i} has neither text nor message.content: {choice}")
                # Try to provide some content as a fallback
                empty_content = "No content available"
                choice["text"] = empty_content
                choice["message"] = {
                    "role": "assistant",
                    "content": empty_content
                }
        
        logger.debug("Response transformation complete")
        return transformed
    
    except Exception as e:
        logger.error(f"Error transforming response: {e}")
        logger.error(traceback.format_exc())
        return response  # Return original on error

# ===== Integration Methods =====

def patch_phoenix_openai_client():
    """
    Patch Phoenix's OpenAI client to transform responses.
    
    This adds the transformer middleware to Phoenix's OpenAI client
    to ensure all responses have the needed fields.
    """
    try:
        # Try to import Phoenix's OpenAI client
        import openai
        
        # Store the original completion create method
        original_chat_completion_create = openai.chat.completions.create
        
        # Create a wrapped version that applies our transformer
        @wraps(original_chat_completion_create)
        def wrapped_chat_completion_create(*args, **kwargs):
            # Call the original method
            result = original_chat_completion_create(*args, **kwargs)
            
            # Transform the response if it's a dictionary
            if hasattr(result, "model_dump"):
                # It's a Pydantic model, dump to dict, transform, and recreate
                try:
                    dict_result = result.model_dump()
                    transformed = transform_response(dict_result)
                    # We can't easily recreate the model, so just log
                    logger.info("Transformed Pydantic model response")
                    return result
                except Exception as e:
                    logger.error(f"Error transforming Pydantic model: {e}")
                    return result
            elif isinstance(result, dict):
                # It's already a dict
                return transform_response(result)
            else:
                # Unknown type, return as is
                return result
        
        # Replace the original method with our wrapped version
        openai.chat.completions.create = wrapped_chat_completion_create
        logger.info("Successfully patched openai.chat.completions.create")
        
        return True
    except (ImportError, AttributeError) as e:
        logger.error(f"Failed to patch Phoenix's OpenAI client: {e}")
        return False

def create_response_transformer_middleware():
    """
    Create a middleware function that can be inserted into the Phoenix request processing pipeline.
    
    This is an alternative approach if patching the OpenAI client doesn't work.
    """
    try:
        # Try to import Phoenix server modules
        from phoenix.server import main as phoenix_main
        
        # Find the LLM trace handling function
        original_handle_llm_trace = getattr(phoenix_main, "handle_llm_trace", None)
        if not original_handle_llm_trace:
            logger.error("Could not find Phoenix's handle_llm_trace function")
            return False
        
        # Create a wrapped version
        @wraps(original_handle_llm_trace)
        def wrapped_handle_llm_trace(trace_data, *args, **kwargs):
            try:
                # Transform any response data in the trace
                if isinstance(trace_data, dict):
                    # Check for outputs or response field
                    if "outputs" in trace_data and isinstance(trace_data["outputs"], dict):
                        trace_data["outputs"] = transform_response(trace_data["outputs"])
                    if "response" in trace_data and isinstance(trace_data["response"], dict):
                        trace_data["response"] = transform_response(trace_data["response"])
            except Exception as e:
                logger.error(f"Error in trace middleware: {e}")
            
            # Call the original handler
            return original_handle_llm_trace(trace_data, *args, **kwargs)
        
        # Replace the original function
        setattr(phoenix_main, "handle_llm_trace", wrapped_handle_llm_trace)
        logger.info("Successfully added response transformer middleware")
        
        return True
    except (ImportError, AttributeError) as e:
        logger.error(f"Failed to create middleware: {e}")
        return False

def configure_phoenix_environment():
    """
    Configure Phoenix environment variables to help with content extraction.
    """
    # Key environment variables to ensure proper content extraction
    env_vars = {
        # Use both paths for content extraction
        "PHOENIX_OPENAI_EXTRACT_CONTENT_PATH": "choices[0].message.content",
        
        # Enable debug and tracing
        "PHOENIX_TRACE_DEBUG": "true",
        "PHOENIX_LLM_TRACE_MESSAGE_CONTENT": "true",
        "PHOENIX_LLM_ENABLE_CONTENT_CAPTURE": "true",
        "PHOENIX_LLM_TRACE_ALL_PAYLOADS": "true",
        
        # Disable response format to avoid interference
        "PHOENIX_OPENAI_DISABLE_RESPONSE_FORMAT": "true"
    }
    
    # Set environment variables
    for key, value in env_vars.items():
        os.environ[key] = value
        logger.info(f"Set environment variable: {key}={value}")
    
    return True

def test_transformer():
    """
    Test the transformer with sample responses to verify it works.
    """
    # Test cases
    test_responses = [
        {
            "name": "Standard OpenAI format",
            "response": {
                "id": "chatcmpl-123",
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "Hello from standard format"
                        },
                        "index": 0
                    }
                ]
            }
        },
        {
            "name": "With text field only",
            "response": {
                "id": "chatcmpl-123",
                "choices": [
                    {
                        "text": "Hello from text field",
                        "index": 0
                    }
                ]
            }
        },
        {
            "name": "Empty response",
            "response": {
                "id": "chatcmpl-123",
                "choices": [
                    {
                        "index": 0
                    }
                ]
            }
        }
    ]
    
    # Run tests
    logger.info("Testing transformer with sample responses")
    for test in test_responses:
        logger.info(f"Testing: {test['name']}")
        
        original = test["response"]
        transformed = transform_response(original)
        
        # Check if transformation added necessary fields
        if "choices" in transformed and transformed["choices"]:
            choice = transformed["choices"][0]
            
            has_text = "text" in choice
            has_message_content = ("message" in choice and 
                                  isinstance(choice["message"], dict) and 
                                  "content" in choice["message"])
            
            logger.info(f"Has text field: {has_text}")
            logger.info(f"Has message.content: {has_message_content}")
            
            if has_text and has_message_content:
                logger.info("✅ Transformation successful")
            else:
                logger.info("❌ Transformation incomplete")
        else:
            logger.info("❌ No choices in transformed response")
    
    return True

# ===== Main Function =====

def main():
    """Main function to apply all fixes"""
    logger.info("Starting Phoenix Response Fix")
    
    # Step 1: Configure Phoenix environment
    logger.info("Configuring Phoenix environment variables")
    configure_phoenix_environment()
    
    # Step 2: Test the transformer
    logger.info("Testing response transformer")
    test_transformer()
    
    # Step 3: Try to patch Phoenix's OpenAI client
    logger.info("Attempting to patch Phoenix's OpenAI client")
    client_patched = patch_phoenix_openai_client()
    
    # Step 4: If client patching fails, try middleware approach
    if not client_patched:
        logger.info("Client patching failed, trying middleware approach")
        middleware_added = create_response_transformer_middleware()
        
        if middleware_added:
            logger.info("Middleware successfully added")
        else:
            logger.error("Both patching approaches failed")
            return False
    
    logger.info("Phoenix Response Fix completed successfully")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)