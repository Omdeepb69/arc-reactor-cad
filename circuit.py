# circuit.py
# Defines core data structures for representing electronic circuits.

import uuid
from typing import List, Dict, Tuple, Optional, Any, Union
import pygame
import logging

# --- Constants ---
PIN_TYPE_DIGITAL = "digital"
PIN_TYPE_ANALOG = "analog"
PIN_TYPE_POWER = "power"
PIN_TYPE_GND = "gnd"
PIN_TYPE_COMPONENT = "component_terminal"  # For generic component pins like LEDs, resistors

PIN_STATE_HIGH = 1
PIN_STATE_LOW = 0
PIN_STATE_UNKNOWN = None
PIN_STATE_CONFLICT = -1  # Represents a direct connection between HIGH and LOW or incompatible states

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
            position_offset: The (x, y) offset relative to the component's top-left corner, used for drawing connection points.
                           Needs refinement based on UI visuals.
        """
        self.id = f"pin_{component_id}_{name}"  # Unique identifier for the pin instance
        self.name = name
        self.pin_type = pin_type
        self.component_id = component_id
        self.position_offset = position_offset
        self.connected_to: List['Connection'] = []  # List of Connection objects attached to this pin
        self.state = PIN_STATE_UNKNOWN  # Current electrical state
        
    def __repr__(self):
        return f"Pin(name='{self.name}', type='{self.pin_type}', component='{self.component_id}')"
    
    def get_absolute_position(self, component_position: Tuple[int, int]) -> Tuple[int, int]:
        """Calculate absolute position based on component position and pin offset"""
        return (component_position[0] + self.position_offset[0],
                component_position[1] + self.position_offset[1])
    
    def add_connection(self, connection: 'Connection'):
        """Add a connection to this pin"""
        if connection not in self.connected_to:
            self.connected_to.append(connection)
    
    def remove_connection(self, connection: 'Connection'):
        """Remove a connection from this pin"""
        if connection in self.connected_to:
            self.connected_to.remove(connection)


class Connection:
    """Represents a wire connection between two pins."""
    
    def __init__(self, pin1_id: str, pin2_id: str):
        """
        Initializes a Connection.
        
        Args:
            pin1_id: The ID of the first pin.
            pin2_id: The ID of the second pin.
        """
        self.id = str(uuid.uuid4())
        self.pin1_id = pin1_id
        self.pin2_id = pin2_id
        self.path_points: List[Tuple[int, int]] = []  # For drawing wire paths
        self.color = (0, 0, 255)  # Default blue wire
        
    def __repr__(self):
        return f"Connection('{self.pin1_id}' to '{self.pin2_id}')"


class Component:
    """Represents a single component in the circuit."""
    
    def __init__(self, id: Optional[str] = None, type: str = "", 
                 position: Tuple[int, int] = (0, 0),
                 properties: Optional[Dict[str, Any]] = None, 
                 connections: Optional[Dict[str, Any]] = None):
        """
        Initializes a Component.
        
        Args:
            id: A unique identifier for the component. If None, a UUID will be generated.
            type: The type of the component (e.g., 'LED', 'Resistor', 'Button', 'ArduinoUno'). Case-insensitive.
            position: The (x, y) position of the component on the workspace.
            properties: Component-specific properties (e.g., {'color': 'red'}).
            connections: Mapping of component pin names to Arduino pins or other connections.
                       e.g., {'anode': 13, 'cathode': 'GND'}
        """
        self.id = id if id else str(uuid.uuid4())
        self.type = type.lower()  # Normalize type to lowercase
        self.position = position
        self.properties = properties or {}
        
        # Convert connection values to strings for consistency
        self.connections = {k: str(v) for k, v in (connections or {}).items()}
        
        # Size depends on component type - these would normally be defined based on images
        self.width, self.height = self._get_default_size()
        
        # Pins depend on component type
        self.pins: Dict[str, Pin] = self._create_pins()
        
        # Pygame rect for UI interactions
        self.rect = pygame.Rect(position[0], position[1], self.width, self.height)
        
        # Visual properties
        self.selected = False
        self.color = self._get_default_color()
        self.image = None  # For future: Add sprite images for components
        
    def _get_default_size(self) -> Tuple[int, int]:
        """Get default size based on component type."""
        sizes = {
            "arduinouno": (100, 160),
            "led": (30, 30),
            "button": (40, 40),
            "resistor": (60, 20),
            "potentiometer": (50, 40),
            "servo": (60, 40),
            "motor": (50, 50),
            "motor_driver": (70, 70),
            "ultrasonic": (60, 30),
            "bluetooth": (50, 40),
            "lcd": (80, 40),
            "buzzer": (30, 30)
        }
        return sizes.get(self.type, (40, 40))  # Default size if type not found
    
    def _get_default_color(self) -> Tuple[int, int, int]:
        """Get default color based on component type."""
        colors = {
            "arduinouno": (0, 120, 0),  # Green
            "led": (255, 100, 100),  # Red
            "button": (100, 100, 100),  # Gray
            "resistor": (200, 180, 0),  # Gold/Yellow
            "potentiometer": (150, 150, 0),  # Olive
            "servo": (100, 100, 200),  # Light blue
            "motor": (150, 50, 150),  # Purple
            "motor_driver": (50, 150, 150),  # Teal
            "ultrasonic": (0, 150, 200),  # Blue
            "bluetooth": (0, 0, 150),  # Dark blue
            "lcd": (100, 200, 200),  # Light teal
            "buzzer": (200, 100, 0)  # Orange
        }
        return colors.get(self.type, (150, 150, 150))  # Default gray
    
    def _create_pins(self) -> Dict[str, Pin]:
        """Create pins based on component type."""
        pins = {}
        
        # Standard pin definitions based on component type
        pin_configs = {
            "arduinouno": {
                "D0": (PIN_TYPE_DIGITAL, (0, 20)),
                "D1": (PIN_TYPE_DIGITAL, (0, 30)),
                "D2": (PIN_TYPE_DIGITAL, (0, 40)),
                "D3": (PIN_TYPE_DIGITAL, (0, 50)),
                "D4": (PIN_TYPE_DIGITAL, (0, 60)),
                "D5": (PIN_TYPE_DIGITAL, (0, 70)),
                "D6": (PIN_TYPE_DIGITAL, (0, 80)),
                "D7": (PIN_TYPE_DIGITAL, (0, 90)),
                "D8": (PIN_TYPE_DIGITAL, (0, 100)),
                "D9": (PIN_TYPE_DIGITAL, (0, 110)),
                "D10": (PIN_TYPE_DIGITAL, (0, 120)),
                "D11": (PIN_TYPE_DIGITAL, (0, 130)),
                "D12": (PIN_TYPE_DIGITAL, (0, 140)),
                "D13": (PIN_TYPE_DIGITAL, (0, 150)),
                "A0": (PIN_TYPE_ANALOG, (100, 20)),
                "A1": (PIN_TYPE_ANALOG, (100, 30)),
                "A2": (PIN_TYPE_ANALOG, (100, 40)),
                "A3": (PIN_TYPE_ANALOG, (100, 50)),
                "A4": (PIN_TYPE_ANALOG, (100, 60)),
                "A5": (PIN_TYPE_ANALOG, (100, 70)),
                "5V": (PIN_TYPE_POWER, (100, 90)),
                "3.3V": (PIN_TYPE_POWER, (100, 100)),
                "GND": (PIN_TYPE_GND, (100, 110)),
                "GND2": (PIN_TYPE_GND, (100, 120)),
                "VIN": (PIN_TYPE_POWER, (100, 130))
            },
            "led": {
                "anode": (PIN_TYPE_COMPONENT, (15, 0)),
                "cathode": (PIN_TYPE_COMPONENT, (15, 30))
            },
            "button": {
                "pin1": (PIN_TYPE_COMPONENT, (0, 20)),
                "pin2": (PIN_TYPE_COMPONENT, (40, 20))
            },
            "resistor": {
                "pin1": (PIN_TYPE_COMPONENT, (0, 10)),
                "pin2": (PIN_TYPE_COMPONENT, (60, 10))
            },
            "potentiometer": {
                "wiper": (PIN_TYPE_COMPONENT, (25, 0)),
                "pin1": (PIN_TYPE_COMPONENT, (0, 20)),
                "pin2": (PIN_TYPE_COMPONENT, (50, 20))
            },
            "servo": {
                "signal": (PIN_TYPE_COMPONENT, (30, 0)),
                "power": (PIN_TYPE_POWER, (15, 40)),
                "ground": (PIN_TYPE_GND, (45, 40))
            },
            "motor": {
                "plus": (PIN_TYPE_COMPONENT, (0, 25)),
                "minus": (PIN_TYPE_COMPONENT, (50, 25))
            },
            "motor_driver": {
                "in1": (PIN_TYPE_COMPONENT, (0, 10)),
                "in2": (PIN_TYPE_COMPONENT, (0, 25)),
                "in3": (PIN_TYPE_COMPONENT, (0, 40)),
                "in4": (PIN_TYPE_COMPONENT, (0, 55)),
                "ena": (PIN_TYPE_COMPONENT, (35, 0)),
                "enb": (PIN_TYPE_COMPONENT, (55, 0)),
                "out1": (PIN_TYPE_COMPONENT, (70, 10)),
                "out2": (PIN_TYPE_COMPONENT, (70, 25)),
                "out3": (PIN_TYPE_COMPONENT, (70, 40)),
                "out4": (PIN_TYPE_COMPONENT, (70, 55)),
                "vcc": (PIN_TYPE_POWER, (35, 70)),
                "gnd": (PIN_TYPE_GND, (55, 70))
            },
            "ultrasonic": {
                "trig": (PIN_TYPE_COMPONENT, (10, 0)),
                "echo": (PIN_TYPE_COMPONENT, (30, 0)),
                "vcc": (PIN_TYPE_POWER, (10, 30)),
                "gnd": (PIN_TYPE_GND, (30, 30))
            },
            "bluetooth": {
                "tx": (PIN_TYPE_COMPONENT, (0, 10)),
                "rx": (PIN_TYPE_COMPONENT, (0, 25)),
                "vcc": (PIN_TYPE_POWER, (50, 10)),
                "gnd": (PIN_TYPE_GND, (50, 25))
            },
            "lcd": {
                "rs": (PIN_TYPE_COMPONENT, (10, 0)),
                "en": (PIN_TYPE_COMPONENT, (25, 0)),
                "d4": (PIN_TYPE_COMPONENT, (40, 0)),
                "d5": (PIN_TYPE_COMPONENT, (55, 0)),
                "d6": (PIN_TYPE_COMPONENT, (70, 0)),
                "d7": (PIN_TYPE_COMPONENT, (85, 0)),
                "vcc": (PIN_TYPE_POWER, (10, 40)),
                "gnd": (PIN_TYPE_GND, (25, 40))
            },
            "buzzer": {
                "plus": (PIN_TYPE_COMPONENT, (15, 0)),
                "minus": (PIN_TYPE_COMPONENT, (15, 30))
            }
        }
        
        # Create pins based on component type
        if self.type in pin_configs:
            for pin_name, (pin_type, offset) in pin_configs[self.type].items():
                pins[pin_name] = Pin(pin_name, pin_type, self.id, offset)
        
        return pins
    
    def __repr__(self):
        return f"Component(id='{self.id}', type='{self.type}', pos={self.position})"
    
    def move_to(self, position: Tuple[int, int]):
        """Move the component to a new position."""
        self.position = position
        self.rect.topleft = position
    
    def contains_point(self, point: Tuple[int, int]) -> bool:
        """Check if a point is within the component's rect."""
        return self.rect.collidepoint(point)
    
    def get_pin_at_position(self, point: Tuple[int, int], threshold: int = 10) -> Optional[Pin]:
        """Get a pin at or near the specified position."""
        for pin_name, pin in self.pins.items():
            pin_pos = (self.position[0] + pin.position_offset[0], 
                       self.position[1] + pin.position_offset[1])
            # Check if point is within threshold distance of pin position
            if (abs(pin_pos[0] - point[0]) <= threshold and 
                abs(pin_pos[1] - point[1]) <= threshold):
                return pin
        return None
    
    def draw(self, surface: pygame.Surface):
        """Draw the component on the given surface."""
        # Draw component body
        if self.selected:
            # Draw selection highlight
            highlight_rect = pygame.Rect(self.rect.left - 2, self.rect.top - 2,
                                         self.rect.width + 4, self.rect.height + 4)
            pygame.draw.rect(surface, (255, 255, 0), highlight_rect, 2)  # Yellow highlight
        
        # Draw component body
        pygame.draw.rect(surface, self.color, self.rect)
        pygame.draw.rect(surface, (0, 0, 0), self.rect, 1)  # Black outline
        
        # Draw component label
        font = pygame.font.SysFont(None, 18)
        label = font.render(self.type.upper(), True, (0, 0, 0))
        label_rect = label.get_rect(center=self.rect.center)
        surface.blit(label, label_rect)
        
        # Draw component ID below
        id_label = font.render(self.id[:8], True, (50, 50, 50))
        id_rect = id_label.get_rect(midbottom=(self.rect.centerx, self.rect.bottom + 12))
        surface.blit(id_label, id_rect)
        
        # Draw pins
        for pin_name, pin in self.pins.items():
            pin_pos = (self.position[0] + pin.position_offset[0], 
                      self.position[1] + pin.position_offset[1])
            # Draw pin circle
            pin_color = {
                PIN_TYPE_DIGITAL: (0, 0, 255),    # Blue
                PIN_TYPE_ANALOG: (255, 0, 255),   # Purple
                PIN_TYPE_POWER: (255, 0, 0),      # Red
                PIN_TYPE_GND: (0, 0, 0),          # Black
                PIN_TYPE_COMPONENT: (0, 150, 0)   # Green
            }.get(pin.pin_type, (100, 100, 100))  # Gray fallback
            
            pygame.draw.circle(surface, pin_color, pin_pos, 3)
            pygame.draw.circle(surface, (0, 0, 0), pin_pos, 3, 1)  # Black outline
            
            # Draw pin label for larger components or specific pin types
            if (self.width >= 60 or self.height >= 60 or 
                self.type == "arduinouno" or pin.pin_type in [PIN_TYPE_POWER, PIN_TYPE_GND]):
                small_font = pygame.font.SysFont(None, 14)
                pin_label = small_font.render(pin.name, True, (0, 0, 0))
                # Adjust label position based on pin position
                if pin.position_offset[0] <= 0:  # Left edge
                    label_pos = (pin_pos[0] + 5, pin_pos[1] - 5)
                elif pin.position_offset[0] >= self.width:  # Right edge
                    label_rect = pin_label.get_rect(right=pin_pos[0] - 5, top=pin_pos[1] - 5)
                    label_pos = label_rect.topleft
                elif pin.position_offset[1] <= 0:  # Top edge
                    label_rect = pin_label.get_rect(centerx=pin_pos[0], bottom=pin_pos[1] - 5)
                    label_pos = label_rect.topleft
                else:  # Bottom edge
                    label_rect = pin_label.get_rect(centerx=pin_pos[0], top=pin_pos[1] + 5)
                    label_pos = label_rect.topleft
                
                surface.blit(pin_label, label_pos)


class Circuit:
    """Represents the entire circuit design."""
    
    def __init__(self, components: Optional[List[Component]] = None, 
                 connections: Optional[List[Connection]] = None):
        """
        Initializes a Circuit.
        
        Args:
            components: A list of components in the circuit.
            connections: A list of connections between component pins.
        """
        self.components = components or []
        self.connections = connections or []
        self.selected_component = None
        self.simulation_state = {}  # For tracking pin states during simulation
    
    def add_component(self, component_type: str, position: Tuple[int, int]) -> Component:
        """Add a new component to the circuit at the specified position."""
        component = Component(
            id=f"{component_type}_{len(self.components)}",
            type=component_type,
            position=position
        )
        self.components.append(component)
        return component
    
    def remove_component(self, component_id: str):
        """Remove a component and all its connections."""
        # Find component by ID
        component = next((c for c in self.components if c.id == component_id), None)
        if not component:
            return
        
        # Get all pins from this component
        component_pin_ids = [pin.id for pin in component.pins.values()]
        
        # Find and remove all connections that use these pins
        connections_to_remove = [
            conn for conn in self.connections
            if conn.pin1_id in component_pin_ids or conn.pin2_id in component_pin_ids
        ]
        
        for conn in connections_to_remove:
            self.connections.remove(conn)
        
        # Remove the component
        self.components.remove(component)
        
        if self.selected_component and self.selected_component.id == component_id:
            self.selected_component = None
    
    def add_connection(self, pin1_id: str, pin2_id: str) -> Optional[Connection]:
        """Create a connection between two pins."""
        # Check if connection already exists
        for conn in self.connections:
            if ((conn.pin1_id == pin1_id and conn.pin2_id == pin2_id) or
                (conn.pin1_id == pin2_id and conn.pin2_id == pin1_id)):
                return None  # Connection already exists
        
        # Create new connection
        connection = Connection(pin1_id, pin2_id)
        self.connections.append(connection)
        
        # Update the pins to reference this connection
        pin1 = self.get_pin_by_id(pin1_id)
        pin2 = self.get_pin_by_id(pin2_id)
        
        if pin1 and pin2:
            pin1.add_connection(connection)
            pin2.add_connection(connection)
        
        return connection
    
    def remove_connection(self, connection_id: str):
        """Remove a connection by its ID."""
        connection = next((c for c in self.connections if c.id == connection_id), None)
        if not connection:
            return
        
        # Remove connection from pins
        pin1 = self.get_pin_by_id(connection.pin1_id)
        pin2 = self.get_pin_by_id(connection.pin2_id)
        
        if pin1:
            pin1.remove_connection(connection)
        if pin2:
            pin2.remove_connection(connection)
        
        # Remove connection from circuit
        self.connections.remove(connection)
    
    def get_component_by_id(self, component_id: str) -> Optional[Component]:
        """Find a component by its ID."""
        return next((c for c in self.components if c.id == component_id), None)
    
    def get_pin_by_id(self, pin_id: str) -> Optional[Pin]:
        """Find a pin by its ID."""
        for component in self.components:
            for pin in component.pins.values():
                if pin.id == pin_id:
                    return pin
        return None
    
    def get_component_at_position(self, position: Tuple[int, int]) -> Optional[Component]:
        """Find the component at the given position."""
        # Check in reverse order to handle overlapping components (last added on top)
        for component in reversed(self.components):
            if component.contains_point(position):
                return component
        return None
    
    def get_pin_at_position(self, position: Tuple[int, int], threshold: int = 10) -> Optional[Tuple[Component, Pin]]:
        """Find a pin at or near the given position."""
        for component in self.components:
            pin = component.get_pin_at_position(position, threshold)
            if pin:
                return (component, pin)
        return None
    
    def update_from_data(self, data: Dict[str, Any]):
        """Update circuit from structured data (e.g., from AI generation)."""
        # Clear current circuit
        self.components = []
        self.connections = []
        
        # Process components
        if "components" in data:
            spacing_x, spacing_y = 100, 80  # Default spacing between components
            
            for i, comp_data in enumerate(data["components"]):
                # Calculate position in a grid layout
                row = i // 3  # 3 components per row
                col = i % 3
                position = (50 + col * spacing_x, 50 + row * spacing_y)
                
                component = Component(
                    id=comp_data.get("id", f"comp_{i}"),
                    type=comp_data.get("type", "unknown"),
                    position=position,
                    properties=comp_data.get("properties", {}),
                    connections=comp_data.get("connections", {})
                )
                self.components.append(component)
        
        # Process implicit connections from component.connections data
        self._create_connections_from_components()
    
    def _create_connections_from_components(self):
        """Create connections based on component.connections data."""
        # Find Arduino component first
        arduino = next((c for c in self.components if c.type == "arduinouno"), None)
        if not arduino:
            # If no Arduino in components, create one
            arduino = Component(
                id="arduino_main",
                type="arduinouno",
                position=(50, 50)
            )
            self.components.append(arduino)
        
        # Process each component's connections to Arduino
        for component in self.components:
            if component.id == arduino.id:
                continue  # Skip the Arduino itself
            
            for comp_pin_name, arduino_pin_name in component.connections.items():
                # Skip non-Arduino connections like GND-to-GND
                if arduino_pin_name not in arduino.pins and not arduino_pin_name.isdigit():
                    if arduino_pin_name not in ["GND", "5V", "3.3V", "VIN"]:
                        continue
                
                # Normalize arduino_pin_name format (e.g., "13" -> "D13")
                if arduino_pin_name.isdigit():
                    arduino_pin_name = f"D{arduino_pin_name}"
                
                # Get component pin
                if comp_pin_name in component.pins:
                    comp_pin = component.pins[comp_pin_name]
                    
                    # For special pins like GND, 5V that might appear multiple times
                    if arduino_pin_name == "GND" and "GND" in arduino.pins:
                        arduino_pin = arduino.pins["GND"]
                    elif arduino_pin_name == "GND" and "GND2" in arduino.pins:
                        arduino_pin = arduino.pins["GND2"]
                    elif arduino_pin_name in arduino.pins:
                        arduino_pin = arduino.pins[arduino_pin_name]
                    else:
                        continue  # Skip if pin not found
                    
                    # Create connection
                    self.add_connection(comp_pin.id, arduino_pin.id)
    
    def get_data(self) -> Dict[str, Any]:
        """Get structured data representation of the circuit."""
        component_data = []
        
        for component in self.components:
            # Extract connections data
            connections = {}
            for pin_name, pin in component.pins.items():
                for connection in pin.connected_to:
                    # Find the other pin in this connection
                    other_pin_id = connection.pin2_id if connection.pin1_id == pin.id else connection.pin1_id
                    other_pin = self.get_pin_by_id(other_pin_id)
                    if other_pin:
                        other_component = self.get_component_by_id(other_pin.component_id)
                        if other_component and other_component.type == "arduinouno":
                            # Connection to Arduino - store Arduino pin name
                            connections[pin_name] = other_pin.name
            
            # Build component data
            comp_data = {
                "id": component.id,
                "type": component.type,
                "properties": component.properties.copy()
            }
            
            if connections:
                comp_data["connections"] = connections
            
            component_data.append(comp_data)
        
        return {
            "components": component_data
        }
    
    def draw(self, surface: pygame.Surface):
        """Draw the entire circuit on the given surface."""
        # Draw connections first (so they appear behind components)
        for connection in self.connections:
            pin1 = self.get_pin_by_id(connection.pin1_id)
            pin2 = self.get_pin_by_id(connection.pin2_id)
            
            if pin1 and pin2:
                comp1 = self.get_component_by_id(pin1.component_id)
                comp2 = self.get_component_by_id(pin2.component_id)
                
                if comp1 and comp2:
                    # Get absolute positions of pins
                    pos1 = (comp1.position[0] + pin1.position_offset[0],
                           comp1.position[1] + pin1.position_offset[1])
                    pos2 = (comp2.position[0] + pin2.position_offset[0],
                           comp2.position[1] + pin2.position_offset[1])
                    
                    # Determine wire color based on pin types
                    wire_color = (0, 0, 255)  # Default blue
                    if pin1.pin_type == PIN_TYPE_POWER or pin2.pin_type == PIN_TYPE_POWER:
                        wire_color = (255, 0, 0)  # Red for power
                    elif pin1.pin_type == PIN_TYPE_GND or pin2.pin_type == PIN_TYPE_GND:
                        wire_color = (0, 0, 0)  # Black for ground
                    
                    # Draw wire with rounded corners if possible
                    if connection.path_points:
                        # Draw path with segments
                        points = [pos1] + connection.path_points + [pos2]
                        for i in range(len(points) - 1):
                            pygame.draw.line(surface, wire_color, points[i], points[i+1], 2)
                    else:
                        # Simple straight line
                        pygame.draw.line(surface, wire_color, pos1, pos2, 2)
        
        # Now draw components
        for component in self.components:
            component.draw(surface)
    
    def simulate_step(self):
        """Perform one step of circuit simulation."""
        # Reset all pin states
        for component in self.components:
            for pin in component.pins.values():
                pin.state = PIN_STATE_UNKNOWN
        
        # Set known states for power and ground pins
        for component in self.components:
            for pin_name, pin in component.pins.items():
                if pin.pin_type == PIN_TYPE_POWER:
                    pin.state = PIN_STATE_HIGH
                elif pin.pin_type == PIN_TYPE_GND:
                    pin.state = PIN_STATE_LOW
        
        # Propagate states through connections (simple approach)
        # Do this several times to handle chains of connections
        for _ in range(5):  # 5 iterations should be enough for most simple circuits
            for connection in self.connections:
                pin1 = self.get_pin_by_id(connection.pin1_id)
                pin2 = self.get_pin_by_id(connection.pin2_id)
                
                if pin1 and pin2:
                    # If one pin has a known state, propagate to the other
                    if pin1.state is not PIN_STATE_UNKNOWN and pin2.state is PIN_STATE_UNKNOWN:
                        pin2.state = pin1.state
                    elif pin2.state is not PIN_STATE_UNKNOWN and pin1.state is PIN_STATE_UNKNOWN:
                        pin1.state = pin2.state
                    # Check for conflicting states (e.g., HIGH connected to LOW)
                    elif (pin1.state is not PIN_STATE_UNKNOWN and 
                          pin2.state is not PIN_STATE_UNKNOWN and 
                          pin1.state != pin2.state):
                        pin1.state = PIN_STATE_CONFLICT
                        pin2.state = PIN_STATE_CONFLICT
        
        # Handle special component behaviors based on pin states
        for component in self.components:
            # LEDs (anode->cathode: HIGH->LOW = ON)
            if component.type == "led":
                if "anode" in component.pins and "cathode" in component.pins:
                    anode = component.pins["anode"]
                    cathode = component.pins["cathode"]
                    if anode.state == PIN_STATE_HIGH and cathode.state == PIN_STATE_LOW:
                        component.properties["state"] = "on"
                    else:
                        component.properties["state"] = "off"
            
            # Buttons (when pressed, connect pin1 to pin2)
            elif component.type == "button":
                if component.properties.get("pressed", False) and "pin1" in component.pins and "pin2" in component.pins:
                    pin1 = component.pins["pin1"]
                    pin2 = component.pins["pin2"]
                    # Make pin states match
                    if pin1.state is not PIN_STATE_UNKNOWN and pin2.state is PIN_STATE_UNKNOWN:
                        pin2.state = pin1.state
                    elif pin2.state is not PIN_STATE_UNKNOWN and pin1.state is PIN_STATE_UNKNOWN:
                        pin1.state = pin2.state
            
            # Motor (plus->minus: HIGH->LOW = running)
            elif component.type == "motor":
                if "plus" in component.pins and "minus" in component.pins:
                    plus = component.pins["plus"]
                    minus = component.pins["minus"]
                    if plus.state == PIN_STATE_HIGH and minus.state == PIN_STATE_LOW:
                        component.properties["state"] = "running"
                    else:
                        component.properties["state"] = "stopped"
            
            # Add other component-specific behaviors here as needed
        
        # Store simulation results
        self.simulation_state = {
            "components": {
                comp.id: {
                    "type": comp.type,
                    "properties": comp.properties.copy(),
                    "pin_states": {
                        pin_name: pin.state for pin_name, pin in comp.pins.items()
                    }
                } for comp in self.components
            }
        }
        
        # Return simulation state for external use if needed
        return self.simulation_state
    
    def save_to_file(self, filename: str) -> bool:
        """Save the circuit to a file."""
        try:
            import json
            data = self.get_data()
            with open(filename, "w") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            logging.error(f"Error saving circuit to file: {e}")
            return False
    
    def load_from_file(self, filename: str) -> bool:
        """Load the circuit from a file."""
        try:
            import json
            with open(filename, "r") as f:
                data = json.load(f)
            self.update_from_data(data)
            return True
        except Exception as e:
            logging.error(f"Error loading circuit from file: {e}")
            return False
    
    def get_component_count(self) -> Dict[str, int]:
        """Return a count of each component type in the circuit."""
        counts = {}
        for component in self.components:
            if component.type in counts:
                counts[component.type] += 1
            else:
                counts[component.type] = 1
        return counts
    
    def export_to_image(self, filename: str, scale: float = 1.0) -> bool:
        """Export the circuit as an image (requires pygame)."""
        try:
            # Create a surface with the right size
            max_x = max([c.position[0] + c.width for c in self.components] + [800])
            max_y = max([c.position[1] + c.height for c in self.components] + [600])
            
            # Add some padding
            width = int((max_x + 50) * scale)
            height = int((max_y + 50) * scale)
            
            # Create surface and fill with white background
            surface = pygame.Surface((width, height))
            surface.fill((255, 255, 255))
            
            # Scale the surface if needed
            if scale != 1.0:
                # Create a transform to scale everything
                def scaled_position(pos):
                    return (int(pos[0] * scale), int(pos[1] * scale))
                
                # Draw connections
                for connection in self.connections:
                    pin1 = self.get_pin_by_id(connection.pin1_id)
                    pin2 = self.get_pin_by_id(connection.pin2_id)
                    
                    if pin1 and pin2:
                        comp1 = self.get_component_by_id(pin1.component_id)
                        comp2 = self.get_component_by_id(pin2.component_id)
                        
                        if comp1 and comp2:
                            # Get absolute positions of pins and scale them
                            pos1 = scaled_position((comp1.position[0] + pin1.position_offset[0],
                                        comp1.position[1] + pin1.position_offset[1]))
                            pos2 = scaled_position((comp2.position[0] + pin2.position_offset[0],
                                        comp2.position[1] + pin2.position_offset[1]))
                            
                            # Determine wire color based on pin types
                            wire_color = (0, 0, 255)  # Default blue
                            if pin1.pin_type == PIN_TYPE_POWER or pin2.pin_type == PIN_TYPE_POWER:
                                wire_color = (255, 0, 0)  # Red for power
                            elif pin1.pin_type == PIN_TYPE_GND or pin2.pin_type == PIN_TYPE_GND:
                                wire_color = (0, 0, 0)  # Black for ground
                            
                            # Draw wire
                            pygame.draw.line(surface, wire_color, pos1, pos2, max(1, int(2 * scale)))
                
                # Draw components (with scaled positions and sizes)
                for component in self.components:
                    # Create a scaled rectangle
                    scaled_rect = pygame.Rect(
                        int(component.position[0] * scale),
                        int(component.position[1] * scale),
                        int(component.width * scale),
                        int(component.height * scale)
                    )
                    
                    # Draw component body
                    pygame.draw.rect(surface, component.color, scaled_rect)
                    pygame.draw.rect(surface, (0, 0, 0), scaled_rect, max(1, int(scale)))  # Black outline
                    
                    # Draw component label
                    font = pygame.font.SysFont(None, max(10, int(18 * scale)))
                    label = font.render(component.type.upper(), True, (0, 0, 0))
                    label_rect = label.get_rect(center=scaled_rect.center)
                    surface.blit(label, label_rect)
                    
                    # Draw pins
                    for pin_name, pin in component.pins.items():
                        pin_pos = scaled_position((component.position[0] + pin.position_offset[0],
                                    component.position[1] + pin.position_offset[1]))
                        
                        # Determine pin color
                        pin_color = {
                            PIN_TYPE_DIGITAL: (0, 0, 255),    # Blue
                            PIN_TYPE_ANALOG: (255, 0, 255),   # Purple
                            PIN_TYPE_POWER: (255, 0, 0),      # Red
                            PIN_TYPE_GND: (0, 0, 0),          # Black
                            PIN_TYPE_COMPONENT: (0, 150, 0)   # Green
                        }.get(pin.pin_type, (100, 100, 100))  # Gray fallback
                        
                        # Draw pin
                        pygame.draw.circle(surface, pin_color, pin_pos, max(1, int(3 * scale)))
                        pygame.draw.circle(surface, (0, 0, 0), pin_pos, max(1, int(3 * scale)), 1)  # Black outline
            else:
                # No scaling needed, draw directly
                self.draw(surface)
            
            # Save to file
            pygame.image.save(surface, filename)
            return True
        except Exception as e:
            logging.error(f"Error exporting circuit to image: {e}")
            return False
    
    def verify_circuit(self) -> List[str]:
        """Verify circuit for common errors and return a list of issues."""
        issues = []
        
        # Check for components without connections
        for component in self.components:
            if component.type == "arduinouno":
                continue  # Skip Arduino itself
            
            connected_pins = []
            for pin_name, pin in component.pins.items():
                if pin.connected_to:
                    connected_pins.append(pin_name)
            
            if not connected_pins:
                issues.append(f"Component {component.id} ({component.type}) has no connections.")
            elif len(connected_pins) < len(component.pins):
                unconnected = [p for p in component.pins.keys() if p not in connected_pins]
                issues.append(f"Component {component.id} ({component.type}) has unconnected pins: {', '.join(unconnected)}")
        
        # Check for power/ground connections
        has_power = False
        has_ground = False
        for component in self.components:
            for pin_name, pin in component.pins.items():
                if pin.pin_type == PIN_TYPE_POWER and pin.connected_to:
                    has_power = True
                elif pin.pin_type == PIN_TYPE_GND and pin.connected_to:
                    has_ground = True
        
        if not has_power:
            issues.append("Circuit has no connected power source.")
        if not has_ground:
            issues.append("Circuit has no connected ground.")
        
        # Check for Arduino
        has_arduino = any(c.type == "arduinouno" for c in self.components)
        if not has_arduino:
            issues.append("Circuit has no Arduino board.")
        
        return issues
