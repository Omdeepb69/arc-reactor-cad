```python
# -*- coding: utf-8 -*-
"""
code_generator.py

Generates functional Arduino (.ino) code based on structured circuit data
for the ARC Reactor CAD project.
"""

import logging
from typing import List, Dict, Any, Optional, Set

# --- Placeholder for circuit.py structures ---
# In a real project, these would be imported from circuit.py
# from circuit import Component, Circuit

# Using placeholder classes here to make the file self-contained and runnable,
# assuming circuit.py might define similar structures.
class Component:
    """Represents a single component in the circuit."""
    def __init__(self, id: str, type: str, properties: Optional[Dict[str, Any]] = None, connections: Optional[Dict[str, Any]] = None):
        """
        Initializes a Component.

        Args:
            id (str): A unique identifier for the component.
            type (str): The type of the component (e.g., 'LED', 'Resistor', 'Button', 'ArduinoUno'). Case-insensitive.
            properties (Optional[Dict[str, Any]]): Component-specific properties (e.g., {'color': 'red'}).
            connections (Optional[Dict[str, Any]]): Mapping of component pin names to Arduino pins or other connections.
                                                    e.g., {'anode': 13, 'cathode': 'GND'}
                                                    e.g., {'pin1': 2, 'pin2': 'GND'}
                                                    e.g., {'wiper': 'A0', 'pin1': '5V', 'pin2': 'GND'}
                                                    e.g., {'signal': 9}
        """
        self.id = id
        self.type = type.lower() # Normalize type to lowercase
        self.properties = properties or {}
        # Ensure connections values are processed consistently (e.g., pin numbers as strings)
        self.connections = {k: str(v) for k, v in (connections or {}).items()}

class Circuit:
    """Represents the entire circuit design."""
    def __init__(self, components: Optional[List[Component]] = None):
        """
        Initializes a Circuit.

        Args:
            components (Optional[List[Component]]): A list of components in the circuit.
        """
        self.components = components or []

# --- End Placeholder ---


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')

# --- Constants ---
PIN_MODES = {
    "OUTPUT": "OUTPUT",
    "INPUT": "INPUT",
    "INPUT_PULLUP": "INPUT_PULLUP"
}
ARDUINO_PINS_ANALOG = {f"A{i}" for i in range(6)} # Typical Uno analog pins
ARDUINO_PINS_DIGITAL = {str(i) for i in range(14)} # Typical Uno digital pins
RESERVED_PINS = {'0', '1'} # Usually used for Serial RX/TX

# --- Helper Functions ---

def _sanitize_id_for_variable(component_id: str) -> str:
    """Creates a more C++ variable-friendly name from a component ID."""
    # Remove non-alphanumeric characters, ensure it doesn't start with a number
    sanitized = ''.join(filter(str.isalnum, component_id))
    if not sanitized:
        return "comp" # Default if ID is weird
    if sanitized[0].isdigit():
        return f"id_{sanitized}"
    return sanitized

def _get_arduino_pin(component: Component, component_pin_name: str) -> Optional[str]:
    """
    Extracts and validates the Arduino pin number/name connected to a component's specific pin.
    Normalizes pin representations (e.g., 'D13' -> '13').

    Args:
        component (Component): The component object.
        component_pin_name (str): The name of the component's pin (e.g., 'anode', 'pin1', 'wiper').

    Returns:
        Optional[str]: The validated and normalized Arduino pin name (e.g., '13', 'A0') or None if invalid/not found.
    """
    connection = component.connections.get(component_pin_name)
    if connection is None:
        logging.debug(f"Component '{component.id}' ({component.type}): No connection found for pin '{component_pin_name}'.")
        return None

    pin_str = str(connection).strip().upper()

    # Normalize 'D' prefix for digital pins
    if pin_str.startswith('D') and pin_str[1:].isdigit():
        pin_str = pin_str[1:]

    # Validate against known Arduino pins
    if pin_str in ARDUINO_PINS_ANALOG or pin_str in ARDUINO_PINS_DIGITAL:
        # Check for RX/TX usage warning
        if pin_str in RESERVED_PINS:
             logging.warning(f"Component '{component.id}' ({component.type}) uses pin {pin_str}, which is often reserved for Serial communication (RX/TX).")
        return pin_str
    else:
        # Allow common power/ground connections without logging warnings
        if pin_str not in ('GND', '5V', '3.3V', 'VIN'):
             logging.warning(f"Component '{component.id}' ({component.type}): Connection '{connection}' for pin '{component_pin_name}' is not a standard Arduino Uno pin (0-13, A0-A5). Treating as non-pin connection.")
        return None # Not a direct connection to an Arduino I/O pin

# --- Core Code Generation Logic ---

def generate_arduino_code(circuit_data: Circuit) -> str:
    """
    Generates Arduino (.ino) code based on the structured circuit data.

    Attempts to create basic functional code for common components like LEDs,
    buttons, potentiometers, and servos. Includes setup and simple loop logic.

    Args:
        circuit_data: A Circuit object containing components and their connections.

    Returns:
        A string containing the generated Arduino code. Returns a basic template
        with an error comment if generation fails or input is invalid.
    """
    if not isinstance(circuit_data, Circuit) or not circuit_data.components:
        logging.warning("generate_arduino_code called with empty or invalid circuit data.")
        return "// ARC Reactor CAD: No valid circuit data provided.\n\nvoid setup() {\n  // Setup code here\n}\n\nvoid loop() {\n  // Main logic here\n}\n"

    includes: Set[str] = set()
    pin_definitions: List[str] = []
    global_vars: List[str] = []
    setup_code: List[str] = []
    loop_code: List[str] = []
    processed_pins: Dict[str, str] = {} # Maps Arduino Pin -> C++ Variable Name
    needs_serial: bool = False

    try:
        # --- Component Processing ---
        arduino_present = any(comp.type == 'arduinouno' for comp in circuit_data.components)
        if not arduino_present:
            logging.warning("No 'ArduinoUno' component found in the circuit data. Code generation might be incomplete.")
            # Proceed anyway, assuming pins connect to *some* Arduino implicitly

        for component in circuit_data.components:
            comp_type = component.type
            comp_id = component.id
            sanitized_id = _sanitize_id_for_variable(comp_id)

            logging.info(f"Processing component: ID='{comp_id}', Type='{comp_type}'")

            # --- LED ---
            if comp_type == 'led':
                pin = _get_arduino_pin(component, 'anode') # Assume anode connects to Arduino pin for control
                if pin:
                    if pin in processed_pins:
                        var_name = processed_pins[pin]
                        logging.info(f"LED '{comp_id}' reusing pin {pin} (variable: {var_name}).")
                    else:
                        var_name = f"led_{sanitized_id}_Pin"
                        pin_definitions.append(f"const int {var_name} = {pin}; // LED '{comp_id}'")
                        processed_pins[pin] = var_name
                    setup_code.append(f"  pinMode({var_name}, OUTPUT);")
                    # Basic blink example
                    loop_code.append(f"  // Blink LED '{comp_id}'")
                    loop_code.append(f"  digitalWrite({var_name}, HIGH);")
                    loop_code.append(f"  delay(500);")
                    loop_code.append(f"  digitalWrite({var_name}, LOW);")
                    loop_code.append(f"  delay(500);")
                    loop_code.append("") # Add blank line for readability
                else:
                    logging.warning(f"LED component '{comp_id}' has no valid Arduino pin connection defined for 'anode'. Skipping code generation for it.")

            # --- Button ---
            elif comp_type == 'button':
                # Assume pin1 connects to Arduino, pin2 to GND (use INPUT_PULLUP) or 5V (use INPUT)
                pin = _get_arduino_pin(component, 'pin1')
                pin2_connection = component.connections.get('pin2', '').upper()

                if pin:
                    mode = PIN_MODES["INPUT_PULLUP"] if pin2_connection == 'GND'