```python
# -*- coding: utf-8 -*-
"""
ui.py

Handles the Pygame-based user interface for ARC Reactor CAD:
- Visual circuit builder (drag-and-drop)
- Rendering circuit diagrams on the canvas
- Basic simulation visualization
- Handling UI events (mouse clicks, drags)
"""

import pygame
import sys
import os
from typing import List, Tuple, Optional, Dict, Any

# --- Project-Specific Imports ---
# Assume circuit.py exists and defines Circuit and Component classes
# If not, define basic placeholder classes here for ui.py to run standalone.
try:
    from circuit import Circuit, Component, Connection, ComponentType
except ImportError:
    print("Warning: circuit.py not found. Using placeholder classes.", file=sys.stderr)
    # --- Placeholder Classes (if circuit.py is missing) ---
    class ComponentType:
        GENERIC = "GENERIC"
        ARDUINO_UNO = "ARDUINO_UNO"
        LED = "LED"
        RESISTOR = "RESISTOR"
        WIRE = "WIRE" # Although wires are connections, might be useful

    class Component:
        def __init__(self, comp_type: str, x: int, y: int, id: str, properties: Optional[Dict[str, Any]] = None):
            self.type = comp_type
            self.id = id
            self.properties = properties if properties is not None else {}
            # Define default sizes - these should ideally come from config or assets
            width, height = 50, 50
            if self.type == ComponentType.ARDUINO_UNO:
                width, height = 100, 150
            elif self.type == ComponentType.LED:
                width, height = 20, 30
            elif self.type == ComponentType.RESISTOR:
                width, height = 40, 15
            self.rect = pygame.Rect(x, y, width, height)
            self.state = "off" # For simulation visualization
            self.connection_points = self._calculate_connection_points() # Points relative to rect.topleft

        def _calculate_connection_points(self) -> List[Tuple[int, int]]:
            # Placeholder: Define connection points based on type
            cx, cy = self.rect.centerx - self.rect.left, self.rect.centery - self.rect.topleft[1]
            if self.type == ComponentType.LED:
                return [(self.rect.width // 2, 0), (self.rect.width // 2, self.rect.height)] # Top/Bottom center
            elif self.type == ComponentType.RESISTOR:
                return [(0, self.rect.height // 2), (self.rect.width, self.rect.height // 2)] # Left/Right center
            elif self.type == ComponentType.ARDUINO_UNO:
                # Simplified: just a few points
                points = []
                for i in range(5): # Example digital pins
                    points.append((self.rect.width, 10 + i * 15))
                points.append((self.rect.width // 4, self.rect.height)) # GND example
                return points
            else:
                return [(0, cy), (self.rect.width, cy), (cx, 0), (cx, self.rect.height)] # Generic box points

        def get_absolute_connection_points(self) -> List[Tuple[int, int]]:
            return [(self.rect.left + rx, self.rect.top + ry) for rx, ry in self.connection_points]

        def get_closest_connection_point(self, pos: Tuple[int, int]) -> Optional[Tuple[int, int]]:
            abs_points = self.get_absolute_connection_points()
            if not abs_points:
                return None
            closest_point = min(abs_points, key=lambda p: pygame.math.Vector2(p).distance_squared_to(pos))
            # Optional: Add a threshold distance check
            # if pygame.math.Vector2(closest_point).distance_to(pos) > CONNECTION_POINT_RADIUS:
            #     return None
            return closest_point

    class Connection:
        def __init__(self, comp1_id: str, point1: Tuple[int, int], comp2_id: str, point2: Tuple[int, int]):
            self.comp1_id = comp1_id
            self.point1 = point1 # Absolute coordinates
            self.comp2_id = comp2_id
            self.point2 = point2 # Absolute coordinates
            self.id = f"conn_{comp1_id}_{comp2_id}_{pygame.time.get_ticks()}" # Simple unique ID

    class Circuit:
        def __init__(self):
            self.components: Dict[str, Component] = {}
            self.connections: List[Connection] = []
            self._next_comp_id = 0

        def add_component(self, comp_type: str, x: int, y: int, properties: Optional[Dict[str, Any]] = None) -> Component:
            comp_id = f"{comp_type.lower()}_{self._next_comp_id}"
            self._next_comp_id += 1
            component = Component(comp_type, x, y, comp_id, properties)
            self.components[comp_id] = component
            print(f"Added component: {comp_id} at ({x}, {y})")
            return component

        def remove_component(self, component_id: str):
            if component_id in self.components:
                del self.components[component_id]
                # Also remove connections associated with this component
                self.connections = [conn for conn in self.connections if conn.comp1_id != component_id and conn.comp2_id != component_id]
                print(f"Removed component: {component_id}")

        def add_connection(self, comp1_id: str, point1: Tuple[int, int], comp2_id: str, point2: Tuple[int, int]):
            connection = Connection(comp1_id, point1, comp2_id, point2)
            self.connections.append(connection)
            print(f"Added connection: {connection.id}")

        def get_component_at(self, pos: Tuple[int, int]) -> Optional[Component]:
            for component in self.components.values():
                if component.rect.collidepoint(pos):
                    return component
            return None

        def update_component_position(self, component_id: str, dx: int, dy: int):
            if component_id in self.components:
                component = self.components[component_id]
                component.rect.move_ip(dx, dy)
                # Update associated connection points
                for conn in self.connections:
                    if conn.comp1_id == component_id:
                        conn.point1 = (conn.point1[0] + dx, conn.point1[1] + dy)
                    if conn.comp2_id == component_id:
                        conn.point2 = (conn.point2[0] + dx, conn.point2[1] + dy)

        def set_component_state(self, component_id: str, state: str):
            if component_id in self.components:
                self.components[component_id].state = state

        def get_circuit_data(self) -> Dict[str, Any]:
            # Basic serialization for potential saving or analysis
            return {
                "components": [vars(c) for c in self.components.values()],
                "connections": [vars(conn) for conn in self.connections]
            }
# --- End Placeholder Classes ---


# --- Potentially Required Libraries (as per project description) ---
# These might be used in other modules but are included here based on requirements
import requests # For LLM API calls (likely in a different module)
from PIL import Image # For image handling (likely in image analysis module)
# import cv2 # Optional: for OpenCV image analysis
# import schemdraw # Optional: for advanced diagram generation

# --- Constants ---
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
LIGHT_GRAY = (230, 230, 230)
BLUE = (0, 0, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
GRID_COLOR = (220, 220, 220)
CONNECTION_POINT_COLOR = (0, 150, 255)
WIRE_COLOR = (50, 50, 50)
WIRE_DRAW_COLOR = (100, 100, 255)
PALETTE_BG = (240, 240, 240)
CANVAS_BG = (255, 255, 255)

# UI Layout
PALETTE_WIDTH = 150
CANVAS_X = PALETTE_WIDTH
CANVAS_Y = 0
CANVAS_WIDTH = SCREEN_WIDTH - PALETTE_WIDTH
CANVAS_HEIGHT = SCREEN_HEIGHT
GRID_SIZE = 20
CONNECTION_POINT_RADIUS = 5
SNAP_DISTANCE = 10 # Pixels to snap connection points

# Component Palette Items
# In a real app, this might load from a config file or asset discovery
PALETTE_ITEMS = [
    {"type": ComponentType.ARDUINO_UNO, "label": "Arduino Uno", "color": BLUE},
    {"type": ComponentType.LED, "label": "LED", "color": RED},
    {"type": ComponentType.RESISTOR, "label": "Resistor", "color": GRAY},
    # Add more components here
]
PALETTE_ITEM_HEIGHT = 60
PALETTE_PADDING = 10

# --- Asset Loading ---
# Basic placeholder for loading images if available
COMPONENT_ASSETS = {} # Store loaded pygame surfaces

def load_assets():
    """Loads component images (if any). Uses placeholders if not found."""
    # Example: Load an image for Arduino Uno
    # try:
    #     uno_img = pygame.image.load(os.path.join('assets', 'arduino_uno.png')).convert_alpha()
    #     # Scale if necessary
    #     COMPONENT_ASSETS[ComponentType.ARDUINO_UNO] = pygame.transform.scale(uno_img, (100, 150))
    # except pygame.error as e:
    #     print(f"Warning: Could not load arduino_uno.png: {e}", file=sys.stderr)
    #     COMPONENT_ASSETS[ComponentType.ARDUINO_UNO] = None # Will use default drawing

    # Add loading for other assets (LED, Resistor, etc.)
    pass # No assets included in this example, will use colored rects


# --- Helper Functions ---
def draw_text(surface: pygame.Surface, text: str, pos: Tuple[int, int], font: pygame.font.Font, color: Tuple[int, int, int] = BLACK):
    """Renders text onto a surface."""
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect(topleft=pos)
    surface.blit(text_surface, text_rect)

def get_snapped_point(target_pos: Tuple[int, int], circuit: Circuit) -> Optional[Tuple[str, Tuple[int, int]]]:
    """Finds the closest component connection point within SNAP_DISTANCE."""
    closest_dist_sq = SNAP_DISTANCE * SNAP_DISTANCE
    snap_target = None # (component_id, point_coords)

    for comp_id, component in circuit.components.items():
        for point in component.get_absolute_connection_points():
            dist_sq = pygame.math.Vector2(point).distance_squared_to(target_pos)
            if dist_sq < closest_dist_sq:
                closest_dist_sq = dist_sq
                snap_target = (comp_id, point)
    return snap_target


# --- Main UI Class ---
class VisualBuilderUI:
    """Manages the Pygame UI for the visual circuit builder."""

    def __init__(self, circuit: Circuit):
        """Initialize Pygame, screen, fonts, and UI state."""
        pygame.init()
        pygame.font.init()

        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("ARC Reactor CAD - Visual Builder")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 24) # Default font
        self.small_font = pygame.font.SysFont(None, 18)

        self.circuit = circuit
        self.running = True

        # UI State
        self.dragging_component: Optional[Component] = None
        self.drag_offset: Tuple[int, int] = (0, 0)
        self.connecting_state: bool = False
        self.connection_start_info: Optional[Tuple[str, Tuple[int, int]]] = None # (comp_id, point_coords)
        self.current_wire_pos: Optional[Tuple[int, int]] = None
        self.selected_component: Optional[Component] = None # For potential property editing

        # Load assets (or use placeholders)
        load_assets()

        # Define UI areas
        self.palette_rect = pygame.Rect(0, 0, PALETTE_WIDTH, SCREEN_HEIGHT)
        self.canvas_rect = pygame.Rect(CANVAS_X, CANVAS_Y, CANVAS_WIDTH, CANVAS_HEIGHT)

        # Pre-calculate palette item rects for click detection
        self.palette_item_rects: List[Tuple[pygame.Rect, Dict[str, Any]]] = []
        y_offset = PALETTE_PADDING
        for item in PALETTE_ITEMS:
            rect = pygame.Rect(PALETTE_PADDING, y_offset, PALETTE_WIDTH - 2 * PALETTE_PADDING, PALETTE_ITEM_HEIGHT)
            self.palette_item_rects.append((rect, item))
            y_offset += PALETTE_ITEM_HEIGHT + PALETTE_PADDING


    def run(self):
        """Main application loop."""
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()

    def handle_events(self):
        """Process Pygame events (quit, mouse, keyboard)."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self.handle_mouse_down(event.pos, event.button)
            elif event.type == pygame.MOUSEBUTTONUP:
                self.handle_mouse_up(event.pos, event.button)
            elif event.type == pygame.MOUSEMOTION:
                self.handle_mouse_motion(event.pos, event.buttons)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_DELETE or event.key == pygame.K_BACKSPACE:
                    if self.selected_component:
                        self.circuit.remove_component(self.selected_component.id)
                        self.selected_component = None
                elif event.key == pygame.K_ESCAPE:
                    # Cancel current action (dragging new component, connecting)
                    if self.dragging_component and self.dragging_component.id.startswith("temp_"): # Check if it's a temporary drag from palette
                         self.dragging_component = None # Just discard it
                    elif self.connecting_state:
                        self.connecting_state = False
                        self.connection_start_info = None
                        self.current_wire_pos = None


    def handle_mouse_down(self, pos: Tuple[int, int], button: int):
        """Handle mouse button down events."""
        # Left mouse button (button 1)
        if button == 1:
            # Check palette clicks
            if self.palette_rect.collidepoint(pos):
                for rect, item_info in self.palette_item_rects:
                    if rect.collidepoint(pos):
                        # Start dragging a new component from the palette
                        # Create a temporary component to represent the drag
                        temp_id = f"temp_{item_info['type']}_{pygame.time.get_ticks()}"
                        # Create at mouse pos initially, center it later if needed
                        self.dragging_component = Component(item_info['type'], pos[0], pos[1], temp_id)
                        # Center the temp component on the mouse cursor
                        self.drag_offset = (self.dragging_component.rect.width // 2, self.dragging_component.rect.height // 2)
                        self.dragging_component.rect.center = pos
                        self.connecting_state = False # Cancel any connection attempt
                        self.selected_component = None
                        print(f"Dragging new {item_info['type']} from palette")
                        break # Found the clicked item
            # Check canvas clicks
            elif self.canvas_rect.collidepoint(pos):
                snapped_point_info = get_snapped_point(pos, self.circuit)

                if snapped_point_info:
                    # Start drawing a connection
                    comp_id, point_coords = snapped_point_info
                    self.connecting_state = True
                    self.connection_start_info = (comp_id, point_coords)
                    self.current_wire_pos = pos
                    self.dragging_component = None # Ensure not dragging component
                    self.selected_component = None
                    print(f"Starting connection from {comp_id} at {point_coords}")
                else:
                    # Check if clicking on an existing component to drag or select
                    component = self.circuit.get_component_at(pos)
                    if component:
                        self.dragging_component = component
                        self.drag_offset = (pos[0] - component.rect.left, pos[1] - component.rect.top)
                        self.connecting_state = False # Cancel connection attempt
                        self.selected_component = component # Select the component
                        print(f"Dragging existing component: {component.id}")
                    else:
                        # Clicked on empty canvas space
                        self.selected_component = None
                        self.connecting_state = False # Cancel connection attempt

        # Right mouse button (button 3) - Could be used for context menus or deleting
        elif button == 3:
            if self.connecting_state:
                # Cancel connection drawing
                self.connecting_state = False
                self.connection_start_info = None
                self.current_wire_pos = None
                print("Connection cancelled")
            else:
                 # Maybe deselect or open context menu
                 component = self.circuit.get_component_at(pos)
                 if component:
                     print(f"Right-clicked on {component.id}") # Placeholder for context menu
                 else:
                     self.selected_component = None


    def handle_mouse_up(self, pos: Tuple[int, int], button: int):
        """Handle mouse button up events."""
        if button == 1:
            if self.connecting_state and self.connection_start_info:
                # Try to end the connection
                snapped_point_info = get_snapped_point(pos, self.circuit)
                if snapped_point_info:
                    end_comp_id, end_point_coords = snapped_point_info
                    start_comp_id, start_point_coords = self.connection_start_info

                    # Avoid connecting a component to itself at the same point (or maybe at all?)
                    if start_comp_id != end_comp_id: # Allow self-connection for some components? Maybe add check later.
                        # Check if connection already exists? (More complex check needed)
                        self.circuit.add_connection(start_comp_id, start_point_coords, end_comp_id, end_point_coords)
                    else:
                        print("Cannot connect component to itself (currently).")
                else:
                    print("Connection end point not valid.")

                # Reset connection state regardless of success
                self.connecting_state = False
                self.connection_start_info = None
                self.current_wire_pos = None

            elif self.dragging_component:
                # If dragging a new component from the palette
                if self.dragging_component.id.startswith("temp_"):
                    if self.canvas_rect.collidepoint(pos):
                        # Place the new component onto the canvas
                        # Adjust position based on drag offset to center it where mouse was released
                        final_x = pos[0] - self.drag_offset[0]
                        final_y = pos[1] - self.drag_offset[1]
                        # Snap to grid?
                        final_x = round(final_x / GRID_SIZE) * GRID_SIZE
                        final_y = round(final_y / GRID_SIZE) * GRID_SIZE

                        # Add to the actual circuit
                        new_comp = self.circuit.add_component(self.dragging_component.type, final_x, final_y)
                        self.selected_component = new_comp # Select the newly added component
                    else:
                        print("Component dropped outside canvas.")
                # If dragging an existing component, its position is already updated in handle_mouse_motion
                # Snap final position to grid
                elif self.canvas_rect.collidepoint(pos):
                     comp = self.dragging_component
                     final_x = round(comp.rect.left / GRID_SIZE) * GRID_SIZE
                     final_y = round(comp.rect.top / GRID_SIZE) * GRID_SIZE
                     dx = final_x - comp.rect.left
                     dy = final_y - comp.rect.top
                     # Use the circuit's method to update position and connections
                     self.circuit.update_component_position(comp.id, dx, dy)


                # Stop dragging
                self.dragging_component = None
                self.drag_offset = (0, 0)


    def handle_mouse_motion(self, pos: Tuple[int, int], buttons: Tuple[int, int, int]):
        """Handle mouse movement."""
        # If left button is held down
        if buttons[0]:
            if self.dragging_component and not self.connecting_state:
                # Move the component (temporary or existing)
                new_x = pos[0] - self.drag_offset[0]
                new_y = pos[1] - self.drag_offset[1]

                # If dragging an existing component, update its position and related connections directly
                if not self.dragging_component.id.startswith("temp_"):
                    dx = new_x - self.dragging_component.rect.left
                    dy = new_y - self.dragging_component.rect.top
                    # Use the circuit's method to handle position updates and connection adjustments
                    self.circuit.update_component_position(self.dragging_component.id, dx, dy)
                else:
                    # Just move the temporary representation
                     self.dragging_component.rect.topleft = (new_x, new_y)

            elif self.connecting_state:
                # Update the end position of the wire being drawn
                self.current_wire_pos = pos


    def update(self):
        """Update UI state (e.g., animations, simulation state)."""
        # This is where simulation logic could update component states
        # For now, it's handled externally or is static.
        # Example: self.update_simulation_view(simulation_data)
        pass


    def draw(self):
        """Draw all UI elements."""
        self.screen.fill(WHITE) # Clear screen

        # Draw Grid on Canvas
        self.draw_grid()

        # Draw Palette
        self.draw_palette()

        # Draw Canvas Area Separator (optional)
        pygame.draw.line(self.screen, GRAY, (CANVAS_X, 0), (CANVAS_X, SCREEN_HEIGHT), 1)

        # Draw Circuit Elements (Components and Connections)
        self.draw_circuit_elements()

        # Draw Wire being actively drawn
        if self.connecting_state and self.connection_start_info and self.current_wire_pos:
            start_pos = self.connection_start_info[1]
            end_pos = self.current_wire_pos
            # Snap end preview to connection point if close
            snapped_end = get_snapped_point(end_pos, self.circuit)
            if snapped_end:
                end_pos = snapped_end[1]
            pygame.draw.line(self.screen, WIRE_DRAW_COLOR, start_pos, end_pos, 2)
            pygame.draw.circle(self.screen, WIRE_DRAW_COLOR, start_pos, CONNECTION_POINT_RADIUS)
            pygame.draw.circle(self.screen, WIRE_DRAW_COLOR, end_pos, CONNECTION_POINT_RADIUS)


        # Draw Component being dragged from palette
        if self.dragging_component and self.dragging_component.id.startswith("temp_"):
            self.draw_component(self.dragging_component, is_preview=True)

        # Highlight selected component
        if self.selected_component and self.selected_component.id in self.circuit.components:
             # Ensure component still exists before drawing highlight
             highlight_rect = self.selected_component.rect.inflate(6, 6)
             pygame.draw.rect(self.screen, YELLOW, highlight_rect, 2, border_radius=3)


        pygame.display.flip() # Update the full display Surface to the screen


    def draw_grid(self):
        """Draws a grid on the canvas area."""
        for x in range(CANVAS_X, SCREEN_WIDTH, GRID_SIZE):
            pygame.draw.line(self.screen, GRID_COLOR, (x, CANVAS_Y), (x, SCREEN_HEIGHT))
        for y in range(CANVAS_Y, SCREEN_HEIGHT, GRID_SIZE):
            pygame.draw.line(self.screen, GRID_COLOR, (CANVAS_X, y), (SCREEN_WIDTH, y))


    def draw_palette(self):
        """Draws the component palette."""
        pygame.draw.rect(self.screen, PALETTE_BG, self.palette_rect)
        title_font = pygame.font.SysFont(None, 30)
        draw_text(self.screen, "Components", (PALETTE_PADDING, 10), title_font, BLACK)

        y_offset = 50 # Start below title
        for rect, item_info in self.palette_item_rects:
             # Adjust rect position based on current y_offset (precalculated rects were for collision only)
             draw_rect = pygame.Rect(PALETTE_PADDING, y_offset, rect.width, rect.height)

             # Draw item background and border
             pygame.draw.rect(self.screen, WHITE, draw_rect)
             pygame.draw.rect(self.screen, GRAY, draw_rect, 1)

             # Draw a simple representation (color box + label)
             # In a real app, draw icons or small previews
             preview_size = 30
             preview_rect = pygame.Rect(draw_rect.left + 5, draw_rect.centery - preview_size // 2, preview_size, preview_size)
             pygame.draw.rect(self.screen, item_info.get("color", GRAY), preview_rect)

             label_pos = (preview_rect.right + 10, draw_rect.top + 5)
             draw_text(self.screen, item_info["label"], label_pos, self.font, BLACK)
             draw_text(self.screen, f"({item_info['type']})", (label_pos[0], label_pos[1] + 20), self.small_font, GRAY)

             y_offset += PALETTE_ITEM_HEIGHT + PALETTE_PADDING


    def draw_circuit_elements(self):
        """Draws all components and connections from the circuit object."""
        # Draw Connections (Wires) first, so components are drawn on top
        for connection in self.circuit.connections:
            # Ensure connected components still exist
            if connection.comp1_id in self.circuit.components and connection.comp2_id in self.circuit.components:
                 # Draw simple straight lines for now
                 pygame.draw.line(self.screen, WIRE_COLOR, connection.point1, connection.point2, 2)
                 