import pygame
import pygame.gfxdraw
import sys
import os
import math
import json
import re
import google.generativeai as genai
from typing import List, Dict, Tuple, Optional

# Initialize pygame
pygame.init()

# Constants
WIDTH, HEIGHT = 1200, 800
FPS = 60
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
LIGHT_GRAY = (230, 230, 230)
DARK_GRAY = (100, 100, 100)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)

# Set up your Gemini API key
GEMINI_API_KEY = "YOUR_API_KEY_HERE"  # Replace with your actual API key
genai.configure(api_key=GEMINI_API_KEY)

class Component:
    def __init__(self, name, x, y, width, height, image_path=None):
        self.name = name
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.pins = []
        self.dragging = False
        self.drag_offset = (0, 0)
        self.selected = False
        self.properties = {}
        
        if image_path and os.path.exists(image_path):
            self.image = pygame.image.load(image_path)
            self.image = pygame.transform.scale(self.image, (width, height))
        else:
            self.image = None
    
    def add_pin(self, name, x_offset, y_offset, pin_type="digital"):
        self.pins.append({
            "name": name,
            "x_offset": x_offset,
            "y_offset": y_offset,
            "absolute_x": self.x + x_offset,
            "absolute_y": self.y + y_offset,
            "type": pin_type,
            "connected_to": []
        })
    
    def update_pin_positions(self):
        for pin in self.pins:
            pin["absolute_x"] = self.x + pin["x_offset"]
            pin["absolute_y"] = self.y + pin["y_offset"]
    
    def render(self, screen):
        if self.selected:
            pygame.draw.rect(screen, BLUE, (self.x - 5, self.y - 5, self.width + 10, self.height + 10), 2)
        
        if self.image:
            screen.blit(self.image, (self.x, self.y))
        else:
            pygame.draw.rect(screen, WHITE, (self.x, self.y, self.width, self.height))
            pygame.draw.rect(screen, BLACK, (self.x, self.y, self.width, self.height), 2)
            font = pygame.font.SysFont('Arial', 14)
            text = font.render(self.name, True, BLACK)
            screen.blit(text, (self.x + self.width//2 - text.get_width()//2, 
                              self.y + self.height//2 - text.get_height()//2))
        
        for pin in self.pins:
            pygame.draw.circle(screen, BLACK, (pin["absolute_x"], pin["absolute_y"]), 4)
            pygame.draw.circle(screen, RED if pin["type"] == "power" else 
                              GREEN if pin["type"] == "digital" else 
                              YELLOW, (pin["absolute_x"], pin["absolute_y"]), 3)
    
    def contains_point(self, x, y):
        return self.x <= x <= self.x + self.width and self.y <= y <= self.y + self.height
    
    def get_pin_at(self, x, y, radius=10):
        for i, pin in enumerate(self.pins):
            dx = pin["absolute_x"] - x
            dy = pin["absolute_y"] - y
            if dx*dx + dy*dy <= radius*radius:
                return i
        return None
    
    def start_drag(self, x, y):
        self.dragging = True
        self.drag_offset = (x - self.x, y - self.y)
    
    def drag_to(self, x, y):
        if self.dragging:
            self.x = x - self.drag_offset[0]
            self.y = y - self.drag_offset[1]
            self.update_pin_positions()
    
    def stop_drag(self):
        self.dragging = False


class Wire:
    def __init__(self, start_component, start_pin_idx, end_component=None, end_pin_idx=None):
        self.start_component = start_component
        self.start_pin_idx = start_pin_idx
        self.end_component = end_component
        self.end_pin_idx = end_pin_idx
        self.temp_end = None
        self.color = BLACK
    
    def update(self):
        if self.start_component and self.end_component:
            start_pin = self.start_component.pins[self.start_pin_idx]
            end_pin = self.end_component.pins[self.end_pin_idx]
            
            # Register connection in pins
            if {"component": self.end_component, "pin_idx": self.end_pin_idx} not in start_pin["connected_to"]:
                start_pin["connected_to"].append({"component": self.end_component, "pin_idx": self.end_pin_idx})
            
            if {"component": self.start_component, "pin_idx": self.start_pin_idx} not in end_pin["connected_to"]:
                end_pin["connected_to"].append({"component": self.start_component, "pin_idx": self.start_pin_idx})
    
    def render(self, screen):
        if self.start_component:
            start_pin = self.start_component.pins[self.start_pin_idx]
            start_pos = (start_pin["absolute_x"], start_pin["absolute_y"])
            
            if self.end_component:
                end_pin = self.end_component.pins[self.end_pin_idx]
                end_pos = (end_pin["absolute_x"], end_pin["absolute_y"])
            elif self.temp_end:
                end_pos = self.temp_end
            else:
                return
            
            # Bezier curve parameters
            control_x = (start_pos[0] + end_pos[0]) / 2
            control_y1 = start_pos[1]
            control_y2 = end_pos[1]
            
            # Draw wire as a bezier curve
            points = []
            for t in range(0, 101, 5):
                t = t / 100
                # Cubic Bezier formula
                x = (1-t)**3 * start_pos[0] + 3*(1-t)**2*t * control_x + 3*(1-t)*t**2 * control_x + t**3 * end_pos[0]
                y = (1-t)**3 * start_pos[1] + 3*(1-t)**2*t * control_y1 + 3*(1-t)*t**2 * control_y2 + t**3 * end_pos[1]
                points.append((int(x), int(y)))
            
            if len(points) > 1:
                pygame.draw.lines(screen, self.color, False, points, 2)


class Button:
    def __init__(self, x, y, width, height, text, color, hover_color, action=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.action = action
        self.font = pygame.font.SysFont('Arial', 16)
    
    def render(self, screen):
        mouse_pos = pygame.mouse.get_pos()
        current_color = self.hover_color if self.rect.collidepoint(mouse_pos) else self.color
        
        pygame.draw.rect(screen, current_color, self.rect)
        pygame.draw.rect(screen, BLACK, self.rect, 2)
        
        text_surf = self.font.render(self.text, True, BLACK)
        screen.blit(text_surf, (
            self.rect.x + (self.rect.width - text_surf.get_width()) // 2,
            self.rect.y + (self.rect.height - text_surf.get_height()) // 2
        ))
    
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos) and self.action:
                return self.action()
        return False


class ComponentPalette:
    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)
        self.components = []
        self.font = pygame.font.SysFont('Arial', 16)
        self.scroll_offset = 0
        self.max_scroll = 0
    
    def add_component_template(self, name, width, height, image_path=None, setup_func=None):
        self.components.append({
            "name": name,
            "width": width,
            "height": height,
            "image_path": image_path,
            "setup_func": setup_func
        })
        
        # Update max scroll
        total_height = sum(c["height"] + 10 for c in self.components)
        self.max_scroll = max(0, total_height - self.rect.height)
    
    def render(self, screen):
        pygame.draw.rect(screen, LIGHT_GRAY, self.rect)
        pygame.draw.rect(screen, BLACK, self.rect, 2)
        
        title = self.font.render("Component Palette", True, BLACK)
        screen.blit(title, (self.rect.x + 10, self.rect.y + 10))
        
        y_offset = self.rect.y + 40 - self.scroll_offset
        for component in self.components:
            if y_offset + component["height"] > self.rect.y and y_offset < self.rect.y + self.rect.height:
                pygame.draw.rect(screen, WHITE, (self.rect.x + 10, y_offset, self.rect.width - 20, component["height"]))
                pygame.draw.rect(screen, BLACK, (self.rect.x + 10, y_offset, self.rect.width - 20, component["height"]), 1)
                
                text = self.font.render(component["name"], True, BLACK)
                screen.blit(text, (self.rect.x + 20, y_offset + component["height"]//2 - text.get_height()//2))
            
            y_offset += component["height"] + 10
    
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                if event.button == 4:  # Scroll up
                    self.scroll_offset = max(0, self.scroll_offset - 20)
                elif event.button == 5:  # Scroll down
                    self.scroll_offset = min(self.max_scroll, self.scroll_offset + 20)
                else:
                    # Check if a component was clicked
                    mouse_y = event.pos[1] + self.scroll_offset
                    y_offset = self.rect.y + 40
                    
                    for component in self.components:
                        if (y_offset <= mouse_y <= y_offset + component["height"] and
                            self.rect.x + 10 <= event.pos[0] <= self.rect.x + self.rect.width - 10):
                            # Create a new component
                            new_component = Component(
                                component["name"],
                                self.rect.width + 50,  # Place it just outside the palette
                                300,
                                component["width"],
                                component["height"],
                                component["image_path"]
                            )
                            
                            # Apply setup function if available
                            if component["setup_func"]:
                                component["setup_func"](new_component)
                            
                            return new_component
                        
                        y_offset += component["height"] + 10
        
        return None


class ArduinoSimulator:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Arduino Circuit Simulator")
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Components and wires
        self.components = []
        self.wires = []
        self.selected_component = None
        self.dragging_wire = None
        self.active_wire = None
        
        # UI elements
        self.palette = ComponentPalette(0, 0, 200, HEIGHT)
        self.setup_component_palette()
        
        self.buttons = [
            Button(WIDTH - 150, 10, 140, 40, "Generate Code", GRAY, LIGHT_GRAY, self.generate_code),
            Button(WIDTH - 150, 60, 140, 40, "Simulate", GREEN, (200, 255, 200), self.simulate_circuit),
            Button(WIDTH - 150, 110, 140, 40, "Clear All", RED, (255, 200, 200), self.clear_all),
        ]
        
        # Code and simulation
        self.generated_code = ""
        self.simulation_active = False
        self.code_view_active = False
    
    def setup_component_palette(self):
        # Arduino UNO
        def setup_arduino(component):
            component.add_pin("5V", 10, 10, "power")
            component.add_pin("GND", 10, 30, "ground")
            component.add_pin("D2", 10, 50, "digital")
            component.add_pin("D3", 10, 70, "digital")
            component.add_pin("D4", 10, 90, "digital")
            component.add_pin("D5", 10, 110, "digital")
            component.add_pin("D6", 10, 130, "digital")
            component.add_pin("D7", 10, 150, "digital")
            component.add_pin("D8", 10, 170, "digital")
            component.add_pin("D9", 130, 10, "digital")
            component.add_pin("D10", 130, 30, "digital")
            component.add_pin("D11", 130, 50, "digital")
            component.add_pin("D12", 130, 70, "digital")
            component.add_pin("D13", 130, 90, "digital")
            component.add_pin("A0", 130, 110, "analog")
            component.add_pin("A1", 130, 130, "analog")
            component.add_pin("A2", 130, 150, "analog")
            component.add_pin("A3", 130, 170, "analog")
            component.properties["type"] = "arduino_uno"
        
        # LED
        def setup_led(component):
            component.add_pin("Anode", 10, 15, "input")
            component.add_pin("Cathode", 10, 35, "output")
            component.properties["type"] = "led"
            component.properties["color"] = "red"
        
        # Resistor
        def setup_resistor(component):
            component.add_pin("Pin1", 0, 10, "passive")
            component.add_pin("Pin2", 50, 10, "passive")
            component.properties["type"] = "resistor"
            component.properties["value"] = "220"
        
        # Button
        def setup_button(component):
            component.add_pin("Pin1", 0, 15, "passive")
            component.add_pin("Pin2", 40, 15, "passive")
            component.properties["type"] = "button"
            component.properties["state"] = "OFF"
        
        # HC-05 Bluetooth Module
        def setup_hc05(component):
            component.add_pin("VCC", 0, 10, "power")
            component.add_pin("GND", 0, 30, "ground")
            component.add_pin("TXD", 0, 50, "digital")
            component.add_pin("RXD", 0, 70, "digital")
            component.add_pin("STATE", 90, 10, "digital")
            component.add_pin("EN", 90, 30, "digital")
            component.properties["type"] = "hc05"
        
        # L298N Motor Driver
        def setup_motor_driver(component):
            component.add_pin("IN1", 0, 10, "digital")
            component.add_pin("IN2", 0, 30, "digital")
            component.add_pin("IN3", 0, 50, "digital")
            component.add_pin("IN4", 0, 70, "digital")
            component.add_pin("ENA", 0, 90, "digital")
            component.add_pin("ENB", 0, 110, "digital")
            component.add_pin("12V", 100, 10, "power")
            component.add_pin("GND", 100, 30, "ground")
            component.add_pin("MOTOR_A1", 100, 50, "output")
            component.add_pin("MOTOR_A2", 100, 70, "output")
            component.add_pin("MOTOR_B1", 100, 90, "output")
            component.add_pin("MOTOR_B2", 100, 110, "output")
            component.properties["type"] = "l298n"
        
        # Ultrasonic Sensor (HC-SR04)
        def setup_ultrasonic(component):
            component.add_pin("VCC", 0, 10, "power")
            component.add_pin("TRIG", 0, 30, "digital")
            component.add_pin("ECHO", 0, 50, "digital")
            component.add_pin("GND", 0, 70, "ground")
            component.properties["type"] = "hcsr04"
        
        # Servo Motor
        def setup_servo(component):
            component.add_pin("VCC", 0, 10, "power")
            component.add_pin("GND", 0, 30, "ground")
            component.add_pin("SIG", 0, 50, "digital")
            component.properties["type"] = "servo"
        
        # IR Sensor
        def setup_ir_sensor(component):
            component.add_pin("VCC", 0, 10, "power")
            component.add_pin("GND", 0, 30, "ground")
            component.add_pin("OUT", 0, 50, "digital")
            component.properties["type"] = "ir_sensor"
        
        # Add all components to the palette
        self.palette.add_component_template("Arduino UNO", 140, 180, None, setup_arduino)
        self.palette.add_component_template("LED", 40, 50, None, setup_led)
        self.palette.add_component_template("Resistor", 50, 20, None, setup_resistor)
        self.palette.add_component_template("Button", 40, 30, None, setup_button)
        self.palette.add_component_template("HC-05 Bluetooth", 90, 80, None, setup_hc05)
        self.palette.add_component_template("L298N Motor Driver", 100, 130, None, setup_motor_driver)
        self.palette.add_component_template("HC-SR04 Ultrasonic", 80, 80, None, setup_ultrasonic)
        self.palette.add_component_template("Servo Motor", 60, 60, None, setup_servo)
        self.palette.add_component_template("IR Sensor", 60, 60, None, setup_ir_sensor)
    
    def run(self):
        while self.running:
            for event in pygame.event.get():
                self.handle_event(event)
            
            self.update()
            self.render()
            self.clock.tick(FPS)
        
        pygame.quit()
        sys.exit()
    
    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False
        
        # Handle button events
        for button in self.buttons:
            if button.handle_event(event):
                continue
        
        # Handle palette events - returns a new component if one was selected
        new_component = self.palette.handle_event(event)
        if new_component:
            self.components.append(new_component)
            self.selected_component = new_component
            for comp in self.components:
                comp.selected = (comp == self.selected_component)
            return
        
        # Handle component interaction
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                # Check if clicked on a pin to start a wire
                for component in self.components:
                    pin_idx = component.get_pin_at(event.pos[0], event.pos[1])
                    if pin_idx is not None:
                        # Start drawing a wire from this pin
                        self.active_wire = Wire(component, pin_idx)
                        self.active_wire.temp_end = event.pos
                        return
                
                # Check if clicked on a component to select or drag
                for component in self.components:
                    if component.contains_point(event.pos[0], event.pos[1]):
                        for comp in self.components:
                            comp.selected = (comp == component)
                        self.selected_component = component
                        component.start_drag(event.pos[0], event.pos[1])
                        return
                
                # Clicked on empty space, deselect all
                self.selected_component = None
                for comp in self.components:
                    comp.selected = False
        
        elif event.type == pygame.MOUSEMOTION:
            # Update active wire endpoint
            if self.active_wire:
                self.active_wire.temp_end = event.pos
            
            # Drag selected component
            for component in self.components:
                if component.dragging:
                    component.drag_to(event.pos[0], event.pos[1])
        
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:  # Left click
                # Stop dragging
                for component in self.components:
                    component.stop_drag()
                
                # Finish wire if connecting to a pin
                if self.active_wire:
                    for component in self.components:
                        if component != self.active_wire.start_component:  # Don't connect to same component
                            pin_idx = component.get_pin_at(event.pos[0], event.pos[1])
                            if pin_idx is not None:
                                self.active_wire.end_component = component
                                self.active_wire.end_pin_idx = pin_idx
                                self.active_wire.update()
                                self.wires.append(self.active_wire)
                                self.active_wire = None
                                return
                    
                    # No valid endpoint found, discard the wire
                    self.active_wire = None
        
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_DELETE and self.selected_component:
                # Remove all wires connected to this component
                self.wires = [w for w in self.wires if w.start_component != self.selected_component and w.end_component != self.selected_component]
                # Remove the component
                self.components.remove(self.selected_component)
                self.selected_component = None
            
            elif event.key == pygame.K_ESCAPE:
                # Cancel active wire
                self.active_wire = None
                # Exit simulation or code view
                if self.simulation_active or self.code_view_active:
                    self.simulation_active = False
                    self.code_view_active = False
    
    def update(self):
        pass
    
    def render(self):
        self.screen.fill(WHITE)
        
        # Draw workspace area
        workspace_rect = pygame.Rect(self.palette.rect.width, 0, WIDTH - self.palette.rect.width, HEIGHT)
        pygame.draw.rect(self.screen, WHITE, workspace_rect)
        
        # Draw components
        for component in self.components:
            component.render(self.screen)
        
        # Draw wires
        for wire in self.wires:
            wire.render(self.screen)
        
        # Draw active wire being placed
        if self.active_wire:
            self.active_wire.render(self.screen)
        
        # Draw UI
        self.palette.render(self.screen)
        for button in self.buttons:
            button.render(self.screen)
        
        # Draw code view or simulation if active
        if self.code_view_active:
            self.render_code_view()
        elif self.simulation_active:
            self.render_simulation()
        
        pygame.display.flip()
    
    def render_code_view(self):
        # Draw semi-transparent overlay
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((255, 255, 255, 220))
        self.screen.blit(overlay, (0, 0))
        
        # Draw code box
        code_rect = pygame.Rect(WIDTH // 8, HEIGHT // 8, WIDTH * 3 // 4, HEIGHT * 3 // 4)
        pygame.draw.rect(self.screen, WHITE, code_rect)
        pygame.draw.rect(self.screen, BLACK, code_rect, 2)
        
        # Draw title
        font_title = pygame.font.SysFont('Arial', 24, bold=True)
        title = font_title.render("Generated Arduino Code", True, BLACK)
        self.screen.blit(title, (code_rect.x + 20, code_rect.y + 20))
        
        # Draw close button
        close_btn = pygame.Rect(code_rect.right - 40, code_rect.y + 20, 30, 30)
        pygame.draw.rect(self.screen, RED, close_btn)
        pygame.draw.rect(self.screen, BLACK, close_btn, 2)
        font_close = pygame.font.SysFont('Arial', 20, bold=True)
        x_text = font_close.render("X", True, BLACK)
        self.screen.blit(x_text, (close_btn.x + 10, close_btn.y + 5))
        
        # Draw code text
        font_code = pygame.font.SysFont('Courier New', 14)
        y_offset = code_rect.y + 70
        line_height = font_code.get_height()
        
        # Split code into lines and render each line
        code_lines = self.generated_code.split('\n')
        visible_lines = (code_rect.height - 100) // line_height
        
        for i, line in enumerate(code_lines[:visible_lines]):
            code_line = font_code.render(line, True, BLACK)
            self.screen.blit(code_line, (code_rect.x + 20, y_offset + i * line_height))
        
        if len(code_lines) > visible_lines:
            more_text = font_code.render("... (more code not shown)", True, DARK_GRAY)
            self.screen.blit(more_text, (code_rect.x + 20, y_offset + visible_lines * line_height))
    
    def render_simulation(self):
        # Draw semi-transparent overlay
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((255, 255, 255, 200))
        self.screen.blit(overlay, (0, 0))
        
        # Draw simulation message
        font = pygame.font.SysFont('Arial', 24, bold=True)
        text = font.render("Simulation active - press ESC to exit", True, BLACK)
        self.screen.blit(text, (WIDTH // 2 - text.get_width() // 2, 20))
        
        # Here we would render the simulated circuit behavior
        # This is just a placeholder animation for now
        sim_rect = pygame.Rect(WIDTH // 4, HEIGHT // 4, WIDTH // 2, HEIGHT // 2)
        pygame.draw.rect(self.screen, WHITE, sim_rect)
        pygame.draw.rect(self.screen, BLACK, sim_rect, 2)
        
        font_sim = pygame.font.SysFont('Arial', 20)
        sim_text = font_sim.render("Interactive Simulation (Placeholder)", True, BLACK)
        self.screen.blit(sim_text, (sim_rect.x + 20, sim_rect.y + 20))
        
        # Draw a blinking LED for effect
        blink_speed = 1000  # milliseconds
        is_on = (pygame.time.get_ticks() % blink_speed) < (blink_speed // 2)
        led_color = RED if is_on else GRAY
        
        pygame.draw.circle(self.screen, led_color, (sim_rect.centerx, sim_rect.centery), 30)
        pygame.draw.circle(self.screen, BLACK, (sim_rect.centerx, sim_rect.centery), 30, 2)
    
    def clear_all(self):
        self.components = []
        self.wires = []
        self.selected_component = None
        self.active_wire = None
        self.generated_code = ""
        self.simulation_active = False
        self.code_view_active = False
        return True
    
    def simulate_circuit(self):
        if not self.components:
            print("No components to simulate")
            return True
        
        self.simulation_active = True
        self.code_view_active = False
        return True
    
    def generate_code(self):
        if not self.components:
            print("No components to generate code for")
            return True
        
        # Extract circuit information
        circuit_info = self.extract_circuit_info()
        prompt = self.create_prompt(circuit_info)
        
        try:
            # Generate code using Gemini
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(prompt)
            
            # Extract code from the response
            self.generated_code = self.extract_code_from_response(response.text)
            self.code_view_active = True
            self.simulation_active = False
        except Exception as e:
            print(f"Error generating code: {e}")
            self.generated_code = f"// Error generating code: {e}"
            self.code_view_active = True
        
        return True
    
    def extract_circuit_info(self):
        """Extract information about components and connections in the circuit"""
        components_info = []
        connections = []
        
        # Find Arduino if present
        arduino = None
        for component in self.components:
            if component.properties.get("type") == "arduino_uno":
                arduino = component
                break
        
        if not arduino:
            return {"error": "No Arduino found in circuit"}
        
        # Extract information about each component
        for component in self.components:
            comp_info = {
                "id": self.components.index(component),
                "type": component.properties.get("type", "unknown"),
                "name": component.name,
                "position": (component.x, component.y),
                "properties": component.properties.copy(),
                "pins": [{
                    "name": pin["name"],
                    "type": pin["type"]
                } for pin in component.pins]
            }
            components_info.append(comp_info)
        
        # Extract wire connections
        for wire in self.wires:
            if wire.start_component and wire.end_component:
                start_component_id = self.components.index(wire.start_component)
                end_component_id = self.components.index(wire.end_component)
                
                start_pin = wire.start_component.pins[wire.start_pin_idx]
                end_pin = wire.end_component.pins[wire.end_pin_idx]
                
                connection = {
                    "from_component": start_component_id,
                    "from_pin": start_pin["name"],
                    "to_component": end_component_id,
                    "to_pin": end_pin["name"]
                }
                connections.append(connection)
        
        return {
            "components": components_info,
            "connections": connections
        }
    
    def create_prompt(self, circuit_info):
        """Create a prompt for the Gemini AI model to generate Arduino code"""
        # Create a description of the circuit
        component_descriptions = []
        pin_connections = []
        
        components = circuit_info["components"]
        connections = circuit_info["connections"]
        
        # Create component descriptions
        for comp in components:
            if comp["type"] != "arduino_uno":  # Skip Arduino itself
                description = f"- {comp['name']} ({comp['type']})"
                if "value" in comp["properties"]:
                    description += f" with value {comp['properties']['value']}"
                if "color" in comp["properties"]:
                    description += f" with color {comp['properties']['color']}"
                component_descriptions.append(description)
        
        # Create connection descriptions
        for conn in connections:
            from_comp = components[conn["from_component"]]
            to_comp = components[conn["to_component"]]
            
            description = f"- {from_comp['name']}'s {conn['from_pin']} is connected to {to_comp['name']}'s {conn['to_pin']}"
            pin_connections.append(description)
        
        # Create the complete prompt
        prompt = f"""
        Generate efficient Arduino code for the following circuit (no comments needed):
        
        Components:
        {chr(10).join(component_descriptions)}
        
        Connections:
        {chr(10).join(pin_connections)}
        
        Include necessary initialization, setup code, and a complete loop that implements appropriate functionality for this circuit.
        Make reasonable assumptions about the intended behavior based on the components used.
        Return ONLY the Arduino code with no explanations or additional text.
        Use minimal syntax, no comments, and efficient coding practices.
        """
        
        return prompt
    
    def extract_code_from_response(self, response_text):
        """Extract the actual code from Gemini's response"""
        # First try to find code blocks
        code_block_pattern = r"```(?:cpp|arduino)?\s*([\s\S]*?)```"
        matches = re.findall(code_block_pattern, response_text)
        
        if matches:
            return matches[0].strip()
        
        # If no code blocks found, just return the raw text
        return response_text.strip()


def main():
    simulator = ArduinoSimulator()
    simulator.run()


if __name__ == "__main__":
    main()
