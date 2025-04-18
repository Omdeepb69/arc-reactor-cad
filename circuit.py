```python
# circuit.py
# Defines core data structures for representing electronic circuits.

import uuid
from typing import List, Dict, Tuple, Optional, Any, Union
import pygame # Used for Rect type hints and potentially position/dimension data

# --- Constants ---
PIN_TYPE_DIGITAL = "digital"
PIN_TYPE_ANALOG = "analog"
PIN_TYPE_POWER = "power"
PIN_TYPE_GND = "gnd"
PIN_TYPE_COMPONENT = "component_terminal" # For generic component pins like LEDs, resistors

PIN_STATE_HIGH = 1
PIN_STATE_LOW = 0
PIN_STATE_UNKNOWN = None
PIN_STATE_CONFLICT = -1 # Represents a direct connection between HIGH and LOW or incompatible states

# --- Component Pin Definition ---
class Pin:
    """Represents a single connection point (pin or terminal) on a component."""
    def __init__(self, name: str, pin_type: str, component_id: str, position_offset: Tuple[int, int] = (0, 0)):
        """
        Initializes a Pin.

        Args:
            name: The identifier for the pin (e.g., "D13", "A0", "VIN", "GND", "anode", "pin1").
            pin_type: The type of the pin (e.g., PIN_TYPE_DIGITAL, PIN_TYPE_POWER).
            component_id: The ID of the component this pin belongs to.
            position_offset: The (x, y) offset relative to the component's top-left corner,
                             used for drawing connection points. Needs refinement based on UI visuals.
        """
        self.id = f"pin_{component_id}_{name}" # Unique identifier for the pin instance
        self.name = name
        self.pin_type = pin_type
        self.component_id = component_id
        self.position_offset = position_offset
        self.connected_to: List['Connection'] = [] # List of Connection objects attached to this pin

    def __repr