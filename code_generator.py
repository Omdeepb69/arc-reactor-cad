# -*- coding: utf-8 -*-
"""
code_generator.py

Generates functional Arduino (.ino) code using the Gemini API
based on user prompts or circuit descriptions for the ARC Reactor CAD project.
"""

import logging
import os
import json
from typing import List, Dict, Any, Optional, Tuple
import requests

# --- Placeholder for circuit.py structures ---
# In a real project, these would be imported from circuit.py
class Component:
    """Represents a single component in the circuit."""
    def __init__(self, id: str, type: str, properties: Optional[Dict[str, Any]] = None, connections: Optional[Dict[str, Any]] = None):
        self.id = id
        self.type = type.lower() # Normalize type to lowercase
        self.properties = properties or {}
        self.connections = {k: str(v) for k, v in (connections or {}).items()}

class Circuit:
    """Represents the entire circuit design."""
    def __init__(self, components: Optional[List[Component]] = None):
        self.components = components or []

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')

class AICodeGenerator:
    """
    Uses Gemini API to generate Arduino code based on circuit descriptions or user prompts.
    """
    def __init__(self, api_key=None):
        """
        Initialize the AI Code Generator.
        
        Args:
            api_key (str, optional): API key for Gemini. If not provided, looks for GEMINI_API_KEY environment variable.
        """
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            logging.warning("No API key provided for Gemini. Code generation may be limited.")
        self.api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro-exp-03-25:generateContent"
    
    def _create_circuit_prompt(self, circuit: Circuit) -> str:
        """
        Create a prompt for Gemini based on the circuit data.
        
        Args:
            circuit (Circuit): The circuit object containing components and connections
            
        Returns:
            str: A formatted prompt describing the circuit
        """
        prompt = "Generate complete Arduino code for a circuit with the following components:\n\n"
        
        for component in circuit.components:
            prompt += f"Component ID: {component.id}\n"
            prompt += f"Type: {component.type}\n"
            
            if component.properties:
                prompt += "Properties:\n"
                for key, value in component.properties.items():
                    prompt += f"- {key}: {value}\n"
            
            if component.connections:
                prompt += "Connections:\n"
                for pin_name, connection in component.connections.items():
                    prompt += f"- {pin_name} connected to {connection}\n"
            
            prompt += "\n"
        
        prompt += """
Please generate complete, functional Arduino code (.ino) for this circuit. Include:
1. Appropriate #include statements for any required libraries
2. Pin definitions as constants
3. Any necessary global variables
4. A proper setup() function with pinMode configurations
5. A loop() function with basic functionality for the components
6. Simple logic to demonstrate component interactions where appropriate

Make the code clean, well-commented, and ready to compile and upload to an Arduino.
"""
        return prompt
    
    def generate_from_circuit(self, circuit: Circuit) -> Tuple[str, bool]:
        """
        Generate Arduino code from the circuit object using Gemini.
        
        Args:
            circuit (Circuit): The circuit object
            
        Returns:
            Tuple[str, bool]: The generated code and a success flag
        """
        if not self.api_key:
            return "// Error: No API key provided for AI code generation.\n\nvoid setup() {}\nvoid loop() {}", False
        
        if not circuit or not circuit.components:
            return "// Error: No circuit components provided.\n\nvoid setup() {}\nvoid loop() {}", False
        
        try:
            prompt = self._create_circuit_prompt(circuit)
            return self._call_gemini_api(prompt)
        except Exception as e:
            logging.error(f"Error in generate_from_circuit: {e}", exc_info=True)
            return f"// Error generating Arduino code: {str(e)}\n\nvoid setup() {{\n}}\nvoid loop() {{\n}}", False
    
    def generate_from_prompt(self, user_prompt: str) -> Tuple[str, bool]:
        """
        Generate Arduino code directly from a user prompt using Gemini.
        
        Args:
            user_prompt (str): The user's prompt describing what they want
            
        Returns:
            Tuple[str, bool]: The generated code and a success flag
        """
        if not self.api_key:
            return "// Error: No API key provided for AI code generation.\n\nvoid setup() {}\nvoid loop() {}", False
        
        try:
            # Format the user prompt to ensure we get Arduino code
            formatted_prompt = f"""
Based on this request: "{user_prompt}"

Generate complete, functional Arduino code (.ino). Include:
1. Appropriate #include statements for any required libraries
2. Pin definitions as constants
3. Any necessary global variables
4. A proper setup() function with pinMode configurations
5. A loop() function with working functionality
6. Clear comments explaining the code

Make the code clean, well-commented, and ready to compile and upload to an Arduino.
"""
            return self._call_gemini_api(formatted_prompt)
        except Exception as e:
            logging.error(f"Error in generate_from_prompt: {e}", exc_info=True)
            return f"// Error generating Arduino code: {str(e)}\n\nvoid setup() {{\n}}\nvoid loop() {{\n}}", False
    
    def _call_gemini_api(self, prompt: str) -> Tuple[str, bool]:
        """
        Call the Gemini API with the given prompt.
        
        Args:
            prompt (str): The prompt to send to Gemini
            
        Returns:
            Tuple[str, bool]: The generated code and a success flag
        """
        headers = {
            "Content-Type": "application/json",
        }
        
        # Add API key as a URL parameter
        url = f"{self.api_url}?key={self.api_key}"
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.2,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 8192,
                "responseMimeType": "text/plain"
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()  # Raise exception for HTTP errors
            
            result = response.json()
            
            # Extract code from response
            if "candidates" in result and result["candidates"]:
                content = result["candidates"][0].get("content", {})
                parts = content.get("parts", [])
                
                # Extract code from parts
                text = ""
                for part in parts:
                    if "text" in part:
                        text += part["text"]
                
                # Try to extract just the Arduino code if there's explanatory text
                # Look for code blocks in markdown format ```arduino ... ```
                import re
                code_blocks = re.findall(r"```(?:arduino|cpp|ino)?\s*(.*?)```", text, re.DOTALL)
                
                if code_blocks:
                    # Use the first code block found
                    return code_blocks[0].strip(), True
                else:
                    # Return the whole response if no code blocks found
                    return text.strip(), True
            
            # If we couldn't parse the response
            logging.error(f"Unexpected API response format: {result}")
            return "// Error: Unexpected API response format\n\nvoid setup() {}\nvoid loop() {}", False
            
        except requests.exceptions.RequestException as e:
            logging.error(f"API request error: {e}", exc_info=True)
            return f"// Error calling Gemini API: {str(e)}\n\nvoid setup() {{\n}}\nvoid loop() {{\n}}", False


class CodeGenerator:
    """
    Wrapper class that exposes the code generation functionality as expected by main.py.
    Handles both code generation and saving to disk.
    """
    
    def __init__(self, api_key=None):
        """
        Initialize the CodeGenerator.
        
        Args:
            api_key (str, optional): API key for Gemini. If not provided, looks for GEMINI_API_KEY environment variable.
        """
        logging.info("Code Generator initialized")
        self.ai_generator = AICodeGenerator(api_key)
    
    def generate_code(self, circuit_data) -> str:
        """
        Generate Arduino code from the given circuit data using AI.
        
        Args:
            circuit_data: Circuit object or data structure containing component information
            
        Returns:
            String containing the generated Arduino code
        """
        if not circuit_data:
            logging.warning("generate_code called with empty circuit data")
            return "// No circuit data provided.\n\nvoid setup() {}\n\nvoid loop() {}"
        
        try:
            # Check if we received a Circuit object or a data dict
            if isinstance(circuit_data, Circuit):
                code, success = self.ai_generator.generate_from_circuit(circuit_data)
                return code
            elif isinstance(circuit_data, dict):
                # Convert dict to Circuit object if needed
                if 'components' in circuit_data:
                    circuit = Circuit()
                    components = circuit_data.get('components', [])
                    
                    # If components is a list of dicts, convert to Component objects
                    if components and isinstance(components[0], dict):
                        circuit.components = [
                            Component(
                                id=comp.get('id', f"comp_{i}"),
                                type=comp.get('type', 'unknown'),
                                properties=comp.get('properties', {}),
                                connections=comp.get('connections', {})
                            )
                            for i, comp in enumerate(components)
                        ]
                    else:
                        # Components already as Component objects
                        circuit.components = components
                    
                    code, success = self.ai_generator.generate_from_circuit(circuit)
                    return code
                
                # If it's a prompt or description in dict format
                elif 'prompt' in circuit_data:
                    code, success = self.ai_generator.generate_from_prompt(circuit_data['prompt'])
                    return code
                else:
                    logging.error("Invalid circuit data format provided to generate_code")
                    return "// Error: Invalid circuit data format\n\nvoid setup() {}\n\nvoid loop() {}"
            elif isinstance(circuit_data, str):
                # Treat as a direct prompt
                code, success = self.ai_generator.generate_from_prompt(circuit_data)
                return code
            else:
                logging.error(f"Unsupported circuit_data type: {type(circuit_data)}")
                return "// Error: Unsupported circuit data type\n\nvoid setup() {}\n\nvoid loop() {}"
        except Exception as e:
            logging.error(f"Error in generate_code: {e}", exc_info=True)
            return f"// Error generating Arduino code: {str(e)}\n\nvoid setup() {{\n}}\nvoid loop() {{\n}}"
    
    def save_code(self, code: str, filename: str = "output.ino") -> bool:
        """
        Save the generated code to a file.
        
        Args:
            code: String containing the Arduino code
            filename: Path where the code should be saved
            
        Returns:
            bool: True if saving succeeded, False otherwise
        """
        try:
            with open(filename, 'w') as file:
                file.write(code)
            logging.info(f"Successfully saved Arduino code to '{filename}'")
            return True
        except Exception as e:
            logging.error(f"Failed to save Arduino code to '{filename}': {e}", exc_info=True)
            return False


if __name__ == "__main__":
    # Simple test case for the AI code generator
    logging.info("Testing AI code_generator.py...")
    
    # Get API key from environment variable
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logging.warning("No GEMINI_API_KEY environment variable found. Test will not be able to connect to API.")
    
    # Create a simple test circuit with an LED and button
    test_circuit = Circuit([
        Component(
            id="led1",
            type="LED",
            properties={"color": "red"},
            connections={"anode": "13", "cathode": "GND"}
        ),
        Component(
            id="button1",
            type="Button",
            connections={"pin1": "2", "pin2": "GND"}
        )
    ])
    
    # Create the generator
    generator = CodeGenerator(api_key)
    
    # Test circuit-based generation
    code = generator.generate_code(test_circuit)
    print("\nGenerated Arduino Code from Circuit:")
    print("-" * 50)
    print(code)
    print("-" * 50)
    
    # Test prompt-based generation
    prompt_code = generator.generate_code("Create Arduino code for a circuit with one LED on pin 13 and one button on pin 2 that toggles the LED when pressed.")
    print("\nGenerated Arduino Code from Prompt:")
    print("-" * 50)
    print(prompt_code)
    print("-" * 50)
    
    logging.info("Code generation test completed")
