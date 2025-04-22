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
ORANGE = (255, 165, 0)

# Set up your Gemini API key
GEMINI_API_KEY = "GEMINI_API_KEY"  # Replace with your actual API key
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
        
        # Render pin labels and pins
        font = pygame.font.SysFont('Arial', 10)
        for pin in self.pins:
            pygame.draw.circle(screen, BLACK, (pin["absolute_x"], pin["absolute_y"]), 4)
            
            # Color-code based on pin type
            pin_color = BLACK  # Default
            if pin["type"] == "power":
                pin_color = RED
            elif pin["type"] == "ground":
                pin_color = BLACK
            elif pin["type"] == "digital":
                pin_color = GREEN
            elif pin["type"] == "analog":
                pin_color = BLUE
            elif pin["type"] == "input":
                pin_color = YELLOW
            elif pin["type"] == "output":
                pin_color = ORANGE
            elif pin["type"] == "passive":
                pin_color = GRAY
                
            pygame.draw.circle(screen, pin_color, (pin["absolute_x"], pin["absolute_y"]), 3)
            
            # Render pin name
            text = font.render(pin["name"], True, BLACK)
            # Adjust text position based on component type and pin position
            text_x = pin["absolute_x"] + 5
            text_y = pin["absolute_y"] - 5
            
            # Adjust position if pin is on the right side
            if pin["x_offset"] > self.width / 2:
                text_x = pin["absolute_x"] - text.get_width() - 5
                
            screen.blit(text, (text_x, text_y))
    
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
        self.selected = False
        
        # Determine wire color based on the start pin type
        if start_component and start_pin_idx is not None:
            pin_type = start_component.pins[start_pin_idx]["type"]
            if pin_type == "power":
                self.color = RED
            elif pin_type == "ground":
                self.color = BLACK
            elif pin_type == "digital" or pin_type == "input" or pin_type == "output":
                self.color = GREEN
            elif pin_type == "analog":
                self.color = BLUE
    
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
                if self.selected:
                    # Draw a highlighted wire if selected
                    pygame.draw.lines(screen, RED, False, points, 3)
                else:
                    pygame.draw.lines(screen, self.color, False, points, 2)
    
    def contains_point(self, x, y, threshold=5):
        """Check if a point is close to the wire"""
        if not self.start_component or not self.end_component:
            return False
            
        start_pin = self.start_component.pins[self.start_pin_idx]
        end_pin = self.end_component.pins[self.end_pin_idx]
        
        start_pos = (start_pin["absolute_x"], start_pin["absolute_y"])
        end_pos = (end_pin["absolute_x"], end_pin["absolute_y"])
        
        # Generate points along the bezier curve
        control_x = (start_pos[0] + end_pos[0]) / 2
        control_y1 = start_pos[1]
        control_y2 = end_pos[1]
        
        points = []
        for t in range(0, 101, 5):
            t = t / 100
            # Cubic Bezier formula
            x_point = (1-t)**3 * start_pos[0] + 3*(1-t)**2*t * control_x + 3*(1-t)*t**2 * control_x + t**3 * end_pos[0]
            y_point = (1-t)**3 * start_pos[1] + 3*(1-t)**2*t * control_y1 + 3*(1-t)*t**2 * control_y2 + t**3 * end_pos[1]
            points.append((int(x_point), int(y_point)))
        
        # Check if the given point is close to any point on the curve
        for point in points:
            dx = point[0] - x
            dy = point[1] - y
            if math.sqrt(dx*dx + dy*dy) <= threshold:
                return True
                
        return False


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


class InputDialog:
    def __init__(self, x, y, width, height, title, prompt_text):
        self.rect = pygame.Rect(x, y, width, height)
        self.title = title
        self.prompt_text = prompt_text
        self.input_text = ""
        self.active = True
        self.font = pygame.font.SysFont('Arial', 18)
        self.title_font = pygame.font.SysFont('Arial', 22, bold=True)
        
        # Input box
        self.input_rect = pygame.Rect(x + 20, y + 100, width - 40, 40)
        
        # Buttons
        button_width = 100
        button_height = 40
        button_y = y + height - 60
        
        self.ok_button = Button(
            x + width//2 - button_width - 10, 
            button_y, 
            button_width, 
            button_height, 
            "OK", 
            GREEN, 
            (200, 255, 200),
            self.on_ok
        )
        
        self.cancel_button = Button(
            x + width//2 + 10, 
            button_y, 
            button_width, 
            button_height, 
            "Cancel", 
            RED, 
            (255, 200, 200),
            self.on_cancel
        )
        
        self.result = None
    
    def on_ok(self):
        self.result = self.input_text
        self.active = False
        return True
    
    def on_cancel(self):
        self.active = False
        return True
    
    def handle_event(self, event):
        if not self.active:
            return False
            
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                return self.on_ok()
            elif event.key == pygame.K_ESCAPE:
                return self.on_cancel()
            elif event.key == pygame.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
            else:
                self.input_text += event.unicode
                
        self.ok_button.handle_event(event)
        self.cancel_button.handle_event(event)
        
        return True
    
    def render(self, screen):
        if not self.active:
            return
            
        # Draw semi-transparent overlay
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))
        
        # Draw dialog box
        pygame.draw.rect(screen, WHITE, self.rect)
        pygame.draw.rect(screen, BLACK, self.rect, 2)
        
        # Draw title
        title_text = self.title_font.render(self.title, True, BLACK)
        screen.blit(title_text, (self.rect.x + 20, self.rect.y + 20))
        
        # Draw prompt text
        prompt_text = self.font.render(self.prompt_text, True, BLACK)
        screen.blit(prompt_text, (self.rect.x + 20, self.rect.y + 60))
        
        # Draw input box
        pygame.draw.rect(screen, LIGHT_GRAY, self.input_rect)
        pygame.draw.rect(screen, BLACK, self.input_rect, 2)
        
        # Draw input text
        text_surf = self.font.render(self.input_text, True, BLACK)
        screen.blit(text_surf, (self.input_rect.x + 10, self.input_rect.y + 10))
        
        # Draw cursor
        if (pygame.time.get_ticks() // 500) % 2 == 0:
            cursor_x = self.input_rect.x + 10 + text_surf.get_width()
            pygame.draw.line(screen, BLACK, 
                            (cursor_x, self.input_rect.y + 10),
                            (cursor_x, self.input_rect.y + 30), 2)
        
        # Draw buttons
        self.ok_button.render(screen)
        self.cancel_button.render(screen)


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
        self.selected_wire = None
        self.dragging_wire = None
        self.active_wire = None
        
        # UI elements
        self.palette = ComponentPalette(0, 0, 200, HEIGHT)
        self.setup_component_palette()
        
        self.buttons = [
            Button(WIDTH - 150, 10, 140, 40, "Generate Code", GRAY, LIGHT_GRAY, self.generate_code),
            Button(WIDTH - 150, 60, 140, 40, "Simulate", GREEN, (200, 255, 200), self.simulate_circuit),
            Button(WIDTH - 150, 110, 140, 40, "Clear All", RED, (255, 200, 200), self.clear_all),
            Button(WIDTH - 150, 160, 140, 40, "Create Circuit", BLUE, (200, 200, 255), self.create_circuit_from_prompt),
            Button(WIDTH - 150, 210, 140, 40, "Delete Wire", ORANGE, (255, 220, 180), self.toggle_delete_wire_mode),
        ]
        
        # Code and simulation
        self.generated_code = ""
        self.simulation_active = False
        self.code_view_active = False
        self.delete_wire_mode = False
        
        # Dialog
        self.active_dialog = None
    
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
            component.add_pin("Anode (+)", 10, 15, "input")
            component.add_pin("Cathode (-)", 10, 35, "output")
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
        
        # Battery
        def setup_battery(component):
            component.add_pin("Positive (+)", 0, 15, "power")
            component.add_pin("Negative (-)", 40, 15, "ground")
            component.properties["type"] = "battery"
            component.properties["voltage"] = "9V"
        
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
        self.palette.add_component_template("Battery (9V)", 40, 30, None, setup_battery)
    
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
        
        # Handle active dialog if any
        if self.active_dialog:
            if self.active_dialog.handle_event(event):
                if self.active_dialog.result is not None:
                    self.process_dialog_result(self.active_dialog.result)
                if not self.active_dialog.active:
                    self.active_dialog = None
                return
        
        # Handle button events
        for button in self.buttons:
            if button.handle_event(event):
                continue
        
        # Handle palette events - returns a new component if one was selected
        new_component = self.palette.handle_event(event)
        if new_component:
            self.components.append(new_component)
            self.selected_component = new_component
            self.selected_wire = None
            for comp in self.components:
                comp.selected = (comp == self.selected_component)
            return
        
        # Handle wire deletion mode
        if self.delete_wire_mode and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for wire in self.wires:
                if wire.contains_point(event.pos[0], event.pos[1]):
                    self.delete_wire(wire)
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
                
                # Check if clicked on a component to select it
                for component in reversed(self.components):
                    if component.contains_point(event.pos[0], event.pos[1]):
                        component.start_drag(event.pos[0], event.pos[1])
                        self.selected_component = component
                        self.selected_wire = None
                        for comp in self.components:
                            comp.selected = (comp == self.selected_component)
                        return
                
                # Check if clicked on a wire to select it
                for wire in self.wires:
                    if wire.contains_point(event.pos[0], event.pos[1]):
                        self.selected_wire = wire
                        self.selected_component = None
                        for wire in self.wires:
                            wire.selected = (wire == self.selected_wire)
                        return
                
                # If clicked on empty space, deselect everything
                self.selected_component = None
                self.selected_wire = None
                for component in self.components:
                    component.selected = False
                for wire in self.wires:
                    wire.selected = False
            
            elif event.button == 3:  # Right click
                if self.active_wire:
                    # Cancel wire creation
                    self.active_wire = None
        
        elif event.type == pygame.MOUSEMOTION:
            # Update component dragging
            if self.selected_component and self.selected_component.dragging:
                self.selected_component.drag_to(event.pos[0], event.pos[1])
            
            # Update active wire end point
            if self.active_wire:
                self.active_wire.temp_end = event.pos
        
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:  # Left button release
                # End component dragging
                if self.selected_component and self.selected_component.dragging:
                    self.selected_component.stop_drag()
                
                # Check if completing a wire
                if self.active_wire:
                    for component in self.components:
                        pin_idx = component.get_pin_at(event.pos[0], event.pos[1])
                        if pin_idx is not None:
                            # Don't connect a pin to itself
                            if (component == self.active_wire.start_component and 
                                pin_idx == self.active_wire.start_pin_idx):
                                self.active_wire = None
                                return
                            
                            # Complete the wire connection
                            self.active_wire.end_component = component
                            self.active_wire.end_pin_idx = pin_idx
                            self.active_wire.update()
                            self.wires.append(self.active_wire)
                            self.active_wire = None
                            return
                    
                    # If no valid end pin was found, cancel the wire
                    self.active_wire = None
        
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_DELETE:
                # Delete selected component or wire
                if self.selected_component:
                    self.delete_component(self.selected_component)
                elif self.selected_wire:
                    self.delete_wire(self.selected_wire)
    
    def delete_component(self, component):
        # Remove all wires connected to this component
        wires_to_remove = []
        for wire in self.wires:
            if wire.start_component == component or wire.end_component == component:
                wires_to_remove.append(wire)
                
        for wire in wires_to_remove:
            self.delete_wire(wire)
            
        # Remove the component
        if component in self.components:
            self.components.remove(component)
            
        self.selected_component = None
    
    def delete_wire(self, wire):
        if wire in self.wires:
            # Remove references in the pins
            if wire.start_component and wire.end_component:
                start_pin = wire.start_component.pins[wire.start_pin_idx]
                end_pin = wire.end_component.pins[wire.end_pin_idx]
                
                # Remove connection references
                for conn in start_pin["connected_to"]:
                    if conn["component"] == wire.end_component and conn["pin_idx"] == wire.end_pin_idx:
                        start_pin["connected_to"].remove(conn)
                        break
                        
                for conn in end_pin["connected_to"]:
                    if conn["component"] == wire.start_component and conn["pin_idx"] == wire.start_pin_idx:
                        end_pin["connected_to"].remove(conn)
                        break
            
            # Remove the wire
            self.wires.remove(wire)
            
        if self.selected_wire == wire:
            self.selected_wire = None
    
    def update(self):
        if self.simulation_active:
            # Update simulation state - this would update LED states, etc.
            pass
    
    def render(self):
        # Clear screen
        self.screen.fill(WHITE)
        
        # Draw grid
        for x in range(0, WIDTH, 20):
            pygame.draw.line(self.screen, LIGHT_GRAY, (x, 0), (x, HEIGHT))
        for y in range(0, HEIGHT, 20):
            pygame.draw.line(self.screen, LIGHT_GRAY, (0, y), (WIDTH, y))
        
        # Draw wires first (so they appear behind components)
        for wire in self.wires:
            wire.render(self.screen)
        
        # Draw active wire being created
        if self.active_wire:
            self.active_wire.render(self.screen)
        
        # Draw components
        for component in self.components:
            component.render(self.screen)
        
        # Draw UI elements
        self.palette.render(self.screen)
        for button in self.buttons:
            button.render(self.screen)
        
        # Draw status information
        font = pygame.font.SysFont('Arial', 16)
        
        status_text = ""
        if self.delete_wire_mode:
            status_text = "Delete Wire Mode: ON (Click on a wire to delete it)"
        
        if status_text:
            text_surf = font.render(status_text, True, RED)
            self.screen.blit(text_surf, (250, 20))
        
        # Draw code view if active
        if self.code_view_active and self.generated_code:
            self.render_code_view()
        
        # Draw active dialog on top if any
        if self.active_dialog:
            self.active_dialog.render(self.screen)
        
        pygame.display.flip()
    
    def render_code_view(self):
        # Draw semi-transparent overlay
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))
        
        # Draw code window
        code_rect = pygame.Rect(WIDTH//2 - 400, HEIGHT//2 - 300, 800, 600)
        pygame.draw.rect(self.screen, WHITE, code_rect)
        pygame.draw.rect(self.screen, BLACK, code_rect, 2)
        
        # Draw title
        font_title = pygame.font.SysFont('Arial', 24, bold=True)
        title = font_title.render("Generated Arduino Code", True, BLACK)
        self.screen.blit(title, (code_rect.x + 20, code_rect.y + 20))
        
        # Draw close button
        close_btn = Button(
            code_rect.x + code_rect.width - 100, 
            code_rect.y + 20, 
            80, 
            30, 
            "Close", 
            RED, 
            (255, 200, 200),
            self.toggle_code_view
        )
        close_btn.render(self.screen)
        
        # Draw code content with syntax highlighting
        font_code = pygame.font.SysFont('Courier New', 14)
        lines = self.generated_code.split('\n')
        y_offset = code_rect.y + 70
        
        for line in lines:
            # Basic syntax highlighting (very simplified)
            if line.strip().startswith("//"):
                text_color = DARK_GRAY
            elif any(keyword in line for keyword in ["void", "int", "float", "boolean", "setup()", "loop()"]):
                text_color = BLUE
            elif any(keyword in line for keyword in ["pinMode", "digitalWrite", "digitalRead", "analogWrite", "analogRead"]):
                text_color = GREEN
            elif "=" in line or "+" in line or "-" in line or "*" in line or "/" in line:
                text_color = ORANGE
            else:
                text_color = BLACK
                
            line_surf = font_code.render(line, True, text_color)
            self.screen.blit(line_surf, (code_rect.x + 20, y_offset))
            y_offset += 20
            
            # Stop rendering if we go beyond the code window
            if y_offset > code_rect.y + code_rect.height - 20:
                break
    
    def toggle_code_view(self):
        self.code_view_active = not self.code_view_active
        return True
    
    def toggle_delete_wire_mode(self):
        self.delete_wire_mode = not self.delete_wire_mode
        return True
    
    def generate_code(self):
        if not self.components:
            self.show_dialog("Error", "No components placed in the circuit!")
            return True
        
        # Find Arduino component
        arduino = None
        for component in self.components:
            if component.properties.get("type") == "arduino_uno":
                arduino = component
                break
        
        if not arduino:
            self.show_dialog("Error", "Arduino board is required!")
            return True
        
        # Generate code based on components and connections
        code = "// Arduino Circuit Simulator - Generated Code\n\n"
        
        # Add includes and defines
        self.add_includes_and_defines(code)
        
        # Add global variables and pin definitions
        self.add_global_variables(code)
        
        # Add setup function
        self.add_setup_function(code)
        
        # Add loop function
        self.add_loop_function(code)
        
        # Add helper functions
        self.add_helper_functions(code)
        
        # Store and display the generated code
        self.generated_code = code
        self.code_view_active = True
        return True
    
    def add_includes_and_defines(self, code):
        # This is a stub that should be expanded with actual code generation logic
        includes = set()
        defines = []
        
        # Check for components that require libraries
        for component in self.components:
            comp_type = component.properties.get("type", "")
            
            if comp_type == "servo":
                includes.add("#include <Servo.h>")
            elif comp_type == "hcsr04":
                includes.add("#include <NewPing.h>")
            elif comp_type == "hc05":
                includes.add("#include <SoftwareSerial.h>")
        
        # Add all includes
        for include in sorted(includes):
            self.generated_code += include + "\n"
        
        if includes:
            self.generated_code += "\n"
        
        # Add defines
        for define in defines:
            self.generated_code += define + "\n"
        
        if defines:
            self.generated_code += "\n"
    
    def add_global_variables(self, code):
        # This is a stub that should be expanded with actual code generation logic
        self.generated_code += "// Pin definitions\n"
        
        # Find Arduino component
        arduino = None
        for component in self.components:
            if component.properties.get("type") == "arduino_uno":
                arduino = component
                break
        
        if not arduino:
            return
        
        # Track used pins and their connections
        used_pins = {}
        
        # Analyze connections and create pin definitions
        for wire in self.wires:
            if wire.start_component == arduino:
                pin_name = arduino.pins[wire.start_pin_idx]["name"]
                connected_comp = wire.end_component
                comp_type = connected_comp.properties.get("type", "unknown")
                comp_pin = connected_comp.pins[wire.end_pin_idx]["name"]
                
                pin_var_name = f"{comp_type}_{pin_name}"
                used_pins[pin_name] = {"component": comp_type, "pin": comp_pin, "var_name": pin_var_name}
                
                self.generated_code += f"const int {pin_var_name} = {pin_name}; // Connected to {comp_type} {comp_pin}\n"
            
            elif wire.end_component == arduino:
                pin_name = arduino.pins[wire.end_pin_idx]["name"]
                connected_comp = wire.start_component
                comp_type = connected_comp.properties.get("type", "unknown")
                comp_pin = connected_comp.pins[wire.start_pin_idx]["name"]
                
                pin_var_name = f"{comp_type}_{pin_name}"
                used_pins[pin_name] = {"component": comp_type, "pin": comp_pin, "var_name": pin_var_name}
                
                self.generated_code += f"const int {pin_var_name} = {pin_name}; // Connected to {comp_type} {comp_pin}\n"
        
        self.generated_code += "\n// Component variables\n"
        
        # Add component-specific variables
        for component in self.components:
            comp_type = component.properties.get("type", "")
            
            if comp_type == "servo":
                self.generated_code += "Servo myServo;\n"
            elif comp_type == "hcsr04":
                self.generated_code += "NewPing sonar(TRIGGER_PIN, ECHO_PIN, 200); // MaxDistance = 200cm\n"
            elif comp_type == "hc05":
                self.generated_code += "SoftwareSerial bluetooth(RX_PIN, TX_PIN);\n"
        
        self.generated_code += "\n"
    
    def add_setup_function(self, code):
        self.generated_code += "void setup() {\n"
        self.generated_code += "  Serial.begin(9600);\n"
        
        # Find Arduino component
        arduino = None
        for component in self.components:
            if component.properties.get("type") == "arduino_uno":
                arduino = component
                break
        
        if not arduino:
            self.generated_code += "}\n\n"
            return
        
        # Configure pins based on connections
        for wire in self.wires:
            if wire.start_component == arduino:
                arduino_pin = arduino.pins[wire.start_pin_idx]
                connected_comp = wire.end_component
                comp_type = connected_comp.properties.get("type", "unknown")
                comp_pin = connected_comp.pins[wire.end_pin_idx]
                
                pin_var_name = f"{comp_type}_{arduino_pin['name']}"
                
                # Configure pin mode based on component and pin type
                if comp_pin["type"] == "input":
                    self.generated_code += f"  pinMode({pin_var_name}, OUTPUT);\n"
                elif comp_pin["type"] == "output" or comp_pin["type"] == "passive":
                    self.generated_code += f"  pinMode({pin_var_name}, INPUT);\n"
            
            elif wire.end_component == arduino:
                arduino_pin = arduino.pins[wire.end_pin_idx]
                connected_comp = wire.start_component
                comp_type = connected_comp.properties.get("type", "unknown")
                comp_pin = connected_comp.pins[wire.start_pin_idx]
                
                pin_var_name = f"{comp_type}_{arduino_pin['name']}"
                
                # Configure pin mode based on component and pin type
                if comp_pin["type"] == "output":
                    self.generated_code += f"  pinMode({pin_var_name}, INPUT);\n"
                elif comp_pin["type"] == "input" or comp_pin["type"] == "passive":
                    self.generated_code += f"  pinMode({pin_var_name}, OUTPUT);\n"
        
        # Add component-specific setup code
        for component in self.components:
            comp_type = component.properties.get("type", "")
            
            if comp_type == "servo":
                self.generated_code += "  myServo.attach(9); // Assuming servo on pin 9\n"
            elif comp_type == "hc05":
                self.generated_code += "  bluetooth.begin(9600);\n"
        
        self.generated_code += "}\n\n"
    
    def add_loop_function(self, code):
        self.generated_code += "void loop() {\n"
        
        # Add component-specific loop code
        for component in self.components:
            comp_type = component.properties.get("type", "")
            
            if comp_type == "button":
                self.generated_code += "  // Read button state\n"
                self.generated_code += "  if (digitalRead(button_pin) == HIGH) {\n"
                self.generated_code += "    // Button is pressed\n"
                self.generated_code += "    digitalWrite(led_pin, HIGH); // Turn on LED\n"
                self.generated_code += "  } else {\n"
                self.generated_code += "    digitalWrite(led_pin, LOW); // Turn off LED\n"
                self.generated_code += "  }\n\n"
            elif comp_type == "hcsr04":
                self.generated_code += "  // Read distance from ultrasonic sensor\n"
                self.generated_code += "  int distance = sonar.ping_cm();\n"
                self.generated_code += "  Serial.print(\"Distance: \");\n"
                self.generated_code += "  Serial.print(distance);\n"
                self.generated_code += "  Serial.println(\" cm\");\n\n"
            elif comp_type == "hc05":
                self.generated_code += "  // Handle bluetooth communication\n"
                self.generated_code += "  if (bluetooth.available()) {\n"
                self.generated_code += "    char data = bluetooth.read();\n"
                self.generated_code += "    Serial.print(\"Received: \");\n"
                self.generated_code += "    Serial.println(data);\n"
                self.generated_code += "  }\n\n"
        
        self.generated_code += "  delay(100); // Short delay\n"
        self.generated_code += "}\n"
    
    def add_helper_functions(self, code):
        # Add any helper functions needed by the components
        pass
    
    def simulate_circuit(self):
        if not self.components:
            self.show_dialog("Error", "No components placed in the circuit!")
            return True
        
        # Toggle simulation mode
        self.simulation_active = not self.simulation_active
        
        if self.simulation_active:
            # Find and update button text to "Stop Simulation"
            for button in self.buttons:
                if button.text == "Simulate":
                    button.text = "Stop Simulation"
                    break
        else:
            # Find and update button text back to "Simulate"
            for button in self.buttons:
                if button.text == "Stop Simulation":
                    button.text = "Simulate"
                    break
        
        return True
    
    def clear_all(self):
        self.components = []
        self.wires = []
        self.selected_component = None
        self.selected_wire = None
        self.active_wire = None
        self.generated_code = ""
        self.simulation_active = False
        return True
    
    def create_circuit_from_prompt(self):
        # Show dialog to get prompt from user
        dialog_width, dialog_height = 500, 250
        self.active_dialog = InputDialog(
            WIDTH//2 - dialog_width//2,
            HEIGHT//2 - dialog_height//2,
            dialog_width,
            dialog_height,
            "Create Circuit",
            "Enter a description of the circuit you want to create:"
        )
        return True
    
    def process_dialog_result(self, result):
        if not result:
            return
        
        # Generate circuit based on user prompt using Google Gemini API
        try:
            model = genai.GenerativeModel(model_name="gemini-2.5-pro-preview-03-25")
            prompt = f"""
            Generate a JSON representation of an Arduino circuit based on this description: "{result}"
            
            The JSON should follow this format:
            {{
                "components": [
                    {{
                        "type": "arduino_uno",
                        "x": 400,
                        "y": 300,
                        "connections": [
                            {{"from_pin": "D2", "to_component": 1, "to_pin": "Anode (+)"}}
                        ]
                    }},
                    {{
                        "type": "led",
                        "x": 600,
                        "y": 300,
                        "properties": {{"color": "red"}}
                    }}
                ]
            }}
            
            Available component types: arduino_uno, led, resistor, button, hc05, l298n, hcsr04, servo, ir_sensor, battery
            Only include JSON in your response without any explanations or formatting.
            """
            
            response = model.generate_content(prompt)
            circuit_json = self.extract_json_from_response(response.text)
            
            if circuit_json:
                self.create_circuit_from_json(circuit_json)
            else:
                self.show_dialog("Error", "Failed to generate a valid circuit from the description.")
        
        except Exception as e:
            self.show_dialog("Error", f"Error generating circuit: {str(e)}")
    
    def extract_json_from_response(self, text):
        # Try to extract JSON from the response
        try:
            # First attempt: Try to parse the whole response as JSON
            return json.loads(text)
        except:
            try:
                # Second attempt: Try to extract JSON using regex
                match = re.search(r'(\{.*\})', text, re.DOTALL)
                if match:
                    return json.loads(match.group(1))
            except:
                pass
        
        return None
    
    def create_circuit_from_json(self, circuit_data):
        # Clear existing circuit
        self.clear_all()
        
        component_map = {}
        
        # Create components
        for i, comp_data in enumerate(circuit_data.get("components", [])):
            comp_type = comp_data.get("type")
            x = comp_data.get("x", 300 + i * 100)
            y = comp_data.get("y", 300)
            
            # Create component based on type
            for template in self.palette.components:
                if template["name"].lower().replace(" ", "_") == comp_type:
                    new_component = Component(
                        template["name"],
                        x,
                        y,
                        template["width"],
                        template["height"],
                        template["image_path"]
                    )
                    
                    # Apply setup function
                    if template["setup_func"]:
                        template["setup_func"](new_component)
                    
                    # Apply custom properties if any
                    if "properties" in comp_data:
                        for key, value in comp_data["properties"].items():
                            new_component.properties[key] = value
                    
                    self.components.append(new_component)
                    component_map[i] = new_component
                    break
        
        # Create connections
        for i, comp_data in enumerate(circuit_data.get("components", [])):
            if "connections" in comp_data and i in component_map:
                from_component = component_map[i]
                
                for conn in comp_data["connections"]:
                    from_pin_name = conn.get("from_pin")
                    to_component_idx = conn.get("to_component")
                    to_pin_name = conn.get("to_pin")
                    
                    if to_component_idx in component_map:
                        to_component = component_map[to_component_idx]
                        
                        # Find pin indices
                        from_pin_idx = None
                        to_pin_idx = None
                        
                        for idx, pin in enumerate(from_component.pins):
                            if pin["name"] == from_pin_name:
                                from_pin_idx = idx
                                break
                        
                        for idx, pin in enumerate(to_component.pins):
                            if pin["name"] == to_pin_name:
                                to_pin_idx = idx
                                break
                        
                        # Create wire if pins found
                        if from_pin_idx is not None and to_pin_idx is not None:
                            new_wire = Wire(from_component, from_pin_idx, to_component, to_pin_idx)
                            new_wire.update()
                            self.wires.append(new_wire)
    
    def show_dialog(self, title, message):
        dialog_width, dialog_height = 400, 200
        self.active_dialog = InputDialog(
            WIDTH//2 - dialog_width//2,
            HEIGHT//2 - dialog_height//2,
            dialog_width,
            dialog_height,
            title,
            message
        )


# Main function
def main():
    simulator = ArduinoSimulator()
    simulator.run()

if __name__ == "__main__":
    main()
