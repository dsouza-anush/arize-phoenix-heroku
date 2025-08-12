#!/usr/bin/env python3
"""
Direct fix for Phoenix UI rendering issue with Heroku AI Claude API.
This is a simplified solution that focuses on the core issue.
"""

import os
import json

def create_phoenix_config():
    """Create a Phoenix configuration file with a simplified transformer"""
    config_file = "/tmp/phoenix_config.json"
    
    config = {
        "api_base": "${INFERENCE_URL}/v1",
        "api_key": "Bearer ${INFERENCE_KEY}",
        "model": "${INFERENCE_MODEL_ID:-claude-4-sonnet}",
        "headers": {
            "Content-Type": "application/json"
        },
        "timeout": 60000,
        "response_schema": {"type": "text"}  # Force text response format
    }
    
    # Write config to file
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"Created config at {config_file}")
    return config_file

def set_environment_variables(config_file):
    """Set critical Phoenix environment variables"""
    vars_to_set = {
        # Config file
        "PHOENIX_OPENAI_CONFIG_FILE": config_file,
        
        # Content extraction
        "PHOENIX_OPENAI_EXTRACT_CONTENT_PATH": "choices[0].message.content",
        "PHOENIX_LLM_TRACE_MESSAGE_CONTENT": "true",
        "PHOENIX_LLM_ENABLE_CONTENT_CAPTURE": "true",
        
        # Response format
        "PHOENIX_LLM_RESPONSE_FORMAT": "text",
        "PHOENIX_LLM_MESSAGE_TYPE": "text",
        "PHOENIX_LLM_CHAT_RENDER_TYPE": "plain",
        
        # Debug settings
        "PHOENIX_LLM_TRACE_ALL_PAYLOADS": "true",
        "PHOENIX_TRACE_DEBUG": "true",
        
        # React settings
        "PHOENIX_SSR_ENABLED": "false",
        "PHOENIX_DEFAULT_ROUTE_COMPONENT": "true"
    }
    
    # Set environment variables
    for key, value in vars_to_set.items():
        os.environ[key] = value
        print(f"Set {key}={value}")

def create_ui_hook():
    """Create a UI hook to patch Phoenix at runtime"""
    hook_file = "/app/phoenix_ui_hook.js"
    
    hook_content = """
// Phoenix UI hook to ensure response content is displayed
(function() {
    // Wait for UI to load
    const interval = setInterval(() => {
        // Look for response container
        const responseContainer = document.querySelector('.output-container');
        if (responseContainer) {
            // Check if content is missing
            const emptyContent = responseContainer.textContent.includes('click run to see output');
            
            if (emptyContent) {
                // Try to find content in trace data
                fetch('/api/v1/llm-traces')
                    .then(response => response.json())
                    .then(traces => {
                        if (traces && traces.length > 0) {
                            const latestTrace = traces[0];
                            // Get trace details
                            fetch(`/api/v1/llm-traces/${latestTrace.id}`)
                                .then(response => response.json())
                                .then(trace => {
                                    // Extract content from various possible locations
                                    let content = null;
                                    if (trace.outputs) {
                                        if (trace.outputs.choices && trace.outputs.choices.length > 0) {
                                            const choice = trace.outputs.choices[0];
                                            if (choice.message && choice.message.content) {
                                                content = choice.message.content;
                                            } else if (choice.text) {
                                                content = choice.text;
                                            }
                                        }
                                    }
                                    
                                    // If content found, display it
                                    if (content) {
                                        const outputText = document.createElement('div');
                                        outputText.className = 'fixed-output-text';
                                        outputText.textContent = content;
                                        outputText.style.padding = '1rem';
                                        outputText.style.whiteSpace = 'pre-wrap';
                                        
                                        // Find proper insertion point
                                        const insertPoint = responseContainer.querySelector('.output-container') || responseContainer;
                                        
                                        // Clear existing content if it's the empty message
                                        if (emptyContent) {
                                            insertPoint.innerHTML = '';
                                        }
                                        
                                        // Add content
                                        insertPoint.appendChild(outputText);
                                        
                                        console.log('Phoenix UI hook: Inserted content from trace');
                                    }
                                });
                        }
                    });
            }
            
            // Stop checking once we've handled the container
            clearInterval(interval);
        }
    }, 1000);
})();
"""
    
    # Write hook to file
    with open(hook_file, "w") as f:
        f.write(hook_content)
    
    print(f"Created UI hook at {hook_file}")
    return hook_file

def main():
    """Apply all fixes"""
    print("=== APPLYING PHOENIX UI FIX ===")
    
    # Create config file
    config_file = create_phoenix_config()
    
    # Set environment variables
    set_environment_variables(config_file)
    
    # Create UI hook
    create_ui_hook()
    
    print("\nFix applied successfully!")
    print("Please restart Phoenix and try the playground again.")

if __name__ == "__main__":
    main()