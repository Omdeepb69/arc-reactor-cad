# ai_interface.py

"""
Manages all interactions with the AI/LLM API(s). Handles prompt processing,
image analysis (optional), suggestion generation, and parsing AI responses
for the ARC Reactor CAD project.
"""

import os
import base64
import json
import logging
from typing import Dict, List, Any, Optional, Tuple

# Third-party libraries
import requests
from PIL import Image
import cv2  # opencv-python

# --- Configuration ---

# Attempt to load API key from environment variables
# Replace with your preferred configuration method if needed
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
# Use GPT-4o for its multimodal capabilities and strong reasoning
DEFAULT_LLM_MODEL = "gpt-4o"
# Use a specific vision model if needed, though gpt-4o handles vision
VISION_LLM_MODEL = "gpt-4o"
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Helper Functions ---

def _encode_image_to_base64(image_path: str) -> Optional[str]:
    """Encodes an image file to a base64 string."""
    try:
        # Validate image format before encoding
        img = Image.open(image_path)
        img.verify() # Verify the image integrity
        img.close() # Must close after verify

        # Re-open for reading content
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except FileNotFoundError:
        logging.error(f"Error: Image file not found at {image_path}")
        return None
    except Exception as e:
        logging.error(f"Error encoding image {image_path}: {e}")
        return None

def _call_llm_api(messages: List[Dict[str, Any]], model: str = DEFAULT_LLM_MODEL, max_tokens: int = 1500, temperature: float = 0.5) -> Optional[Dict[str, Any]]:
    """
    Sends a request to the OpenAI API and returns the JSON response.

    Args:
        messages: A list of message objects for the chat completion API.
        model: The model to use (e.g., "gpt-4o").
        max_tokens: The maximum number of tokens to generate.
        temperature: Controls randomness (0.0 to 1.0).

    Returns:
        The JSON response from the API or None if an error occurs.
    """
    if not OPENAI_API_KEY:
        logging.error("OpenAI API key not found. Set the OPENAI_API_KEY environment variable.")
        return None

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        # Request JSON output where applicable
        # Note: This works best with newer models like gpt-4o and gpt-4-turbo
        # "response_format": {"type": "json_object"} # Enable if consistently needing JSON
    }

    try:
        response = requests.post(OPENAI_API_URL, headers=headers, json=payload, timeout=60) # Increased timeout
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"API request failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logging.error(f"API Response Status Code: {e.response.status_code}")
            logging.error(f"API Response Body: {e.response.text}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred during API call: {e}")
        return None

def parse_llm_response(response_json: Optional[Dict[str, Any]], expected_keys: Optional[List[str]] = None) -> Optional[Any]:
    """
    Parses the LLM response, attempting to extract content and optionally JSON data.

    Args:
        response_json: The raw JSON response from the LLM API.
        expected_keys: A list of keys expected if the content is JSON.

    Returns:
        The extracted content (string, dict, list) or None if parsing fails.
    """
    if not response_json or "choices" not in response_json or not response_json["choices"]:
        logging.error("Invalid or empty LLM response received.")
        return None

    try:
        message = response_json["choices"][0].get("message", {})
        content = message.get("content")

        if not content:
            logging.warning("LLM response content is empty.")
            return None

        # Try to parse content as JSON if it looks like JSON
        content_stripped = content.strip()
        if content_stripped.startswith('{') and content_stripped.endswith('}') or \
           content_stripped.startswith('[') and content_stripped.endswith(']'):
            try:
                # Handle potential markdown code blocks around JSON
                if content_stripped.startswith("