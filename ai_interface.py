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
    if not response_json or "candidates" not in response_json or not response_json["candidates"]:
        logging.error("Invalid or empty LLM response received.")
        return None

    try:
        content = response_json["candidates"][0].get("content", {}).get("parts", [{}])[0].get("text", "")
        
        if not content:
            logging.warning("LLM response content is empty.")
            return None

        # Try to parse content as JSON if it looks like JSON
        content_stripped = content.strip()
        if content_stripped.startswith('{') and content_stripped.endswith('}') or \
           content_stripped.startswith('[') and content_stripped.endswith(']'):
            try:
                # Handle potential markdown code blocks around JSON
                if "```json" in content_stripped:
                    content_stripped = content_stripped.split("```json")[1].split("```")[0].strip()
                elif "```" in content_stripped:
                    content_stripped = content_stripped.split("```")[1].split("```")[0].strip()
                
                parsed_json = json.loads(content_stripped)
                
                # Validate expected structure if keys are provided
                if expected_keys and isinstance(parsed_json, dict):
                    missing_keys = [key for key in expected_keys if key not in parsed_json]
                    if missing_keys:
                        logging.warning(f"JSON response missing expected keys: {missing_keys}")
                
                return parsed_json
            except json.JSONDecodeError:
                logging.info("Response content is not valid JSON, returning as plain text.")
                return content
        
        return content

    except Exception as e:
        logging.error(f"Error parsing LLM response: {e}")
        return None

# --- Core AI Interface Class ---

class AIInterface:
    """Manages interactions with AI models for circuit generation and analysis."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initializes the AI interface.
        
        Args:
            api_key: Optional API key for the Gemini API.
        """
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            logging.warning("No Gemini API key provided. AI features will be limited.")
        
        self.gemini_api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
        self.gemini_vision_api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-vision:generateContent"
        self.model = "gemini-2.5-pro-exp-03-25"
        
    def _call_gemini_api(self, prompt: str, image_data: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Calls the Gemini API with the given prompt and optional image.
        
        Args:
            prompt: The text prompt to send to the model.
            image_data: Optional base64-encoded image data.
            
        Returns:
            The JSON response from the API or None if an error occurs.
        """
        if not self.api_key:
            logging.error("Gemini API key not available")
            return None
            
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key
        }
        
        parts = [{"text": prompt}]
        
        if image_data:
            api_url = self.gemini_vision_api_url
            parts.append({
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": image_data
                }
            })
        else:
            api_url = self.gemini_api_url
            
        payload = {
            "contents": [{
                "parts": parts
            }],
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": 2048
            }
        }
        
        try:
            response = requests.post(
                f"{api_url}?key={self.api_key}", 
                headers=headers, 
                json=payload, 
                timeout=60
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Gemini API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logging.error(f"API Response Status Code: {e.response.status_code}")
                logging.error(f"API Response Body: {e.response.text}")
            return None
        except Exception as e:
            logging.error(f"An unexpected error occurred during Gemini API call: {e}")
            return None
    
    def prompt_to_circuit(self, prompt: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Converts a natural language description into circuit data and Arduino code.
        
        Args:
            prompt: User's natural language description of the desired circuit.
            
        Returns:
            A tuple containing:
            - Circuit data structure (dictionary) or None if generation failed
            - Arduino code string or None if generation failed
        """
        logging.info(f"Generating circuit from prompt: '{prompt}'")
        
        # Craft a structured prompt that helps the AI generate useful output
        structured_prompt = f"""
        As J.A.R.V.I.S. Jr., I need you to design an Arduino circuit based on this description:
        
        "{prompt}"
        
        Please respond with a JSON object containing these two parts:
        1. A "circuit_data" object describing components and connections
        2. An "arduino_code" string with complete, functional Arduino code
        
        The circuit_data should follow this format:
        {{
            "components": [
                {{
                    "id": "unique_id",
                    "type": "component_type", 
                    "properties": {{"key": "value"}},
                    "connections": {{"pin_name": "arduino_pin"}}
                }}
            ]
        }}
        
        Valid component types include: arduinouno, led, button, resistor, potentiometer, servo, motor, motor_driver, ultrasonic, bluetooth, lcd, buzzer.
        
        Use standard Arduino pin identifiers (0-13, A0-A5, GND, 5V, 3.3V).
        """
        
        response_json = self._call_gemini_api(structured_prompt)
        if not response_json:
            return None, None
            
        parsed_response = parse_llm_response(response_json)
        if not parsed_response or not isinstance(parsed_response, dict):
            logging.error("Failed to parse AI response to structured format")
            return None, None
            
        try:
            if isinstance(parsed_response, str):
                # Try to extract JSON from the text response
                circuit_data_match = re.search(r'```json(.*?)```', parsed_response, re.DOTALL)
                if circuit_data_match:
                    try:
                        circuit_data = json.loads(circuit_data_match.group(1).strip())
                    except json.JSONDecodeError:
                        circuit_data = None
                else:
                    circuit_data = None
                    
                # Extract Arduino code
                code_match = re.search(r'```(?:arduino|cpp)(.*?)```', parsed_response, re.DOTALL)
                arduino_code = code_match.group(1).strip() if code_match else None
            else:
                # Response is already JSON
                circuit_data = parsed_response.get("circuit_data")
                arduino_code = parsed_response.get("arduino_code")
                
            if not circuit_data or not arduino_code:
                logging.error("AI response missing required circuit data or Arduino code")
                return None, None
                
            return circuit_data, arduino_code
                
        except Exception as e:
            logging.error(f"Error extracting circuit data and code from AI response: {e}")
            return None, None
    
    def analyze_image(self, image_path: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Analyzes an image of a circuit and attempts to generate matching circuit data and code.
        
        Args:
            image_path: Path to the image file.
            
        Returns:
            A tuple containing:
            - Circuit data structure (dictionary) or None if analysis failed
            - Arduino code string or None if analysis failed
        """
        logging.info(f"Analyzing circuit image: {image_path}")
        
        # Encode the image
        image_data = _encode_image_to_base64(image_path)
        if not image_data:
            logging.error("Failed to encode image")
            return None, None
            
        prompt = """
        Analyze this Arduino circuit image carefully. Identify all components, their connections to the Arduino, and the circuit's purpose.
        
        Return a JSON object with:
        1. A "circuit_data" object describing the components and connections
        2. An "arduino_code" string with functional Arduino code that implements the circuit's behavior
        
        Format the circuit_data as:
        {
            "components": [
                {
                    "id": "unique_id",
                    "type": "component_type", 
                    "properties": {"key": "value"},
                    "connections": {"pin_name": "arduino_pin"}
                }
            ]
        }
        """
        
        response_json = self._call_gemini_api(prompt, image_data)
        if not response_json:
            return None, None
            
        parsed_response = parse_llm_response(response_json)
        if not parsed_response:
            logging.error("Failed to parse AI image analysis response")
            return None, None
            
        try:
            if isinstance(parsed_response, str):
                # Try to extract JSON from the text response
                circuit_data_match = re.search(r'```json(.*?)```', parsed_response, re.DOTALL)
                if circuit_data_match:
                    try:
                        circuit_data = json.loads(circuit_data_match.group(1).strip())
                    except json.JSONDecodeError:
                        circuit_data = None
                else:
                    circuit_data = None
                    
                # Extract Arduino code
                code_match = re.search(r'```(?:arduino|cpp)(.*?)```', parsed_response, re.DOTALL)
                arduino_code = code_match.group(1).strip() if code_match else None
            else:
                # Response is already JSON
                circuit_data = parsed_response.get("circuit_data")
                arduino_code = parsed_response.get("arduino_code")
                
            if not circuit_data or not arduino_code:
                logging.error("AI image analysis missing required circuit data or Arduino code")
                return None, None
                
            return circuit_data, arduino_code
                
        except Exception as e:
            logging.error(f"Error extracting circuit data and code from AI image analysis: {e}")
            return None, None
    
    def get_suggestions(self, circuit_data: Dict[str, Any]) -> str:
        """
        Analyzes a circuit configuration and returns J.A.R.V.I.S. Jr. style improvement suggestions.
        
        Args:
            circuit_data: Dictionary containing the current circuit configuration.
            
        Returns:
            A string containing suggestions for improving the circuit.
        """
        logging.info("Generating suggestions for current circuit")
        
        prompt = f"""
        As J.A.R.V.I.S. Jr., analyze this Arduino circuit and provide 1-2 witty but useful suggestions for improvements:
        
        {json.dumps(circuit_data, indent=2)}
        
        Focus on:
        - Energy efficiency
        - Circuit protection
        - Component alternatives
        - Circuit simplification
        - Performance improvements
        
        Keep your response short, direct, and with an Iron Man-inspired touch.
        """
        
        response_json = self._call_gemini_api(prompt)
        if not response_json:
            return "Unable to generate suggestions at this time."
            
        parsed_response = parse_llm_response(response_json)
        if not parsed_response:
            return "Circuit analysis complete, but no specific suggestions to offer."
            
        # Clean up the response to make it concise
        suggestions = parsed_response
        if isinstance(suggestions, str):
            # Remove any markdown formatting
            suggestions = suggestions.replace('#', '').strip()
            # Keep it brief
            if len(suggestions) > 150:
                sentences = suggestions.split('.')
                suggestions = '.'.join(sentences[:2]) + '.'
                
        return suggestions
