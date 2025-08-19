import pygame
import numpy as np
import cv2
import math
import random
import subprocess
import tempfile
import os
import wave
import struct

# === Enhanced Endless Platformer with Dynamic Animations ===
# New features:
# - Robot spinning/flipping on big jumps
# - Dynamic dance moves while running
# - Varied jump styles and air tricks
# - Enhanced particle systems that follow robot movements
# - More expressive eye and body animations

# Initialize Pygame
pygame.init()

# Constants
WIDTH, HEIGHT = 768, 768
FPS = 60
BACKGROUND_COLOR = (15, 15, 25)  # Darker, more cinematic background

# Robot colors
ROBOT_ORANGE = (255, 165, 0)
ROBOT_DARK_ORANGE = (255, 140, 0)
ROBOT_LIGHT_ORANGE = (255, 200, 100)
ROBOT_HIGHLIGHT = (255, 255, 150)

# Platform colors
PLATFORM_COLOR = (100, 100, 100)
SPECIAL_PLATFORM_COLOR = (150, 150, 255)
BOUNCE_PLATFORM_COLOR = (255, 100, 150)

# Coin colors
COIN_GOLD = (255, 215, 0)
COIN_YELLOW = (200, 200, 0)

# Effect colors
PARTICLE_COLORS = [(255, 255, 255), (255, 200, 100), (255, 150, 50)]

class Particle:
    def __init__(self, x, y, vel_x, vel_y, color, life=30, follow_robot=False):
        self.x = x
        self.y = y
        self.vel_x = vel_x
        self.vel_y = vel_y
        self.color = color
        self.life = life
        self.max_life = life
        self.size = random.randint(2, 5)
        self.follow_robot = follow_robot
        self.rotation = random.randint(0, 360)
        self.rotation_speed = random.randint(-10, 10)
    
    def update(self, robot_x=0, robot_y=0):
        if self.follow_robot:
            # Particles that loosely follow the robot
            target_x = robot_x + random.randint(-20, 20)
            target_y = robot_y + random.randint(-10, 30)
            self.vel_x += (target_x - self.x) * 0.01
            self.vel_y += (target_y - self.y) * 0.01
        
        self.x += self.vel_x
        self.y += self.vel_y
        self.vel_y += 0.1  # Gravity
        self.life -= 1
        self.rotation += self.rotation_speed
        return self.life > 0
    
    def draw(self, screen, camera_x):
        if self.life > 0:
            draw_x = self.x - camera_x
            alpha = self.life / self.max_life
            size = int(self.size * alpha)
            if size > 0:
                # Add rotation effect for some particles
                if self.rotation_speed != 0:
                    # Draw as small rotating square
                    points = []
                    for angle in [45, 135, 225, 315]:
                        rad = math.radians(angle + self.rotation)
                        px = draw_x + math.cos(rad) * size
                        py = self.y + math.sin(rad) * size
                        points.append((px, py))
                    if len(points) >= 3:
                        pygame.draw.polygon(screen, self.color, points)
                else:
                    pygame.draw.circle(screen, self.color, (int(draw_x), int(self.y)), size)

class Coin:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.collected = False
        self.animation_frame = 0
        self.float_offset = 0
        self.pulse_scale = 1.0
        self.collection_animation = 0
        
    def update(self):
        self.animation_frame += 0.2
        self.float_offset = math.sin(self.animation_frame) * 3
        
        # Pulse effect
        pulse_speed = 0.15
        self.pulse_scale = 1.0 + 0.2 * math.sin(self.animation_frame * pulse_speed)
        
        if self.collection_animation > 0:
            self.collection_animation -= 1
    
    def collect(self):
        if not self.collected:
            self.collected = True
            self.collection_animation = 20
            return True
        return False
    
    def draw(self, screen, camera_x):
        if self.collected and self.collection_animation <= 0:
            return
            
        draw_x = self.x - camera_x
        draw_y = self.y + self.float_offset
        
        if self.collection_animation > 0:
            # Collection animation - growing and fading
            scale = 1.0 + (20 - self.collection_animation) * 0.1
            alpha = self.collection_animation / 20.0
            size = int(12 * scale * alpha)
        else:
            size = int(12 * self.pulse_scale)
        
        if size > 0:
            # Outer glow
            pygame.draw.circle(screen, COIN_YELLOW, (int(draw_x), int(draw_y)), size + 2)
            # Main coin
            pygame.draw.circle(screen, COIN_GOLD, (int(draw_x), int(draw_y)), size)
            # Inner highlight
            pygame.draw.circle(screen, COIN_YELLOW, (int(draw_x - 3), int(draw_y - 3)), max(1, size // 3))

class Robot:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 40
        self.height = 50
        self.vel_x = 0
        self.vel_y = 0
        self.on_ground = False
        self.animation_frame = 0
        self.facing_right = True
        
        # Enhanced animation states
        self.jump_animation = 0
        self.flip_rotation = 0  # For spinning jumps
        self.flip_speed = 0
        self.is_flipping = False
        
        # Dance move states
        self.dance_state = "normal"  # normal, head_bob, arm_swing, shoulder_shrug
        self.dance_timer = 0
        self.dance_intensity = 0
        
        # Expression states
        self.expression = "normal"  # normal, excited, focused, surprised
        self.expression_timer = 0
        
        # Other animation states
        self.hit_animation = 0
        self.landing_animation = 0
        self.speed_boost = 0
        self.last_beat_frame = -10
        self.target_platform = None
        self.coins_collected = 0
        self.combo_multiplier = 1.0
        self.glow_intensity = 0
        self.jump_buffer = 0
        self.coyote_timer = 0
        
        # Air trick system
        self.air_trick = None  # "spin", "flip", "twist", "double_jump"
        self.air_trick_timer = 0
        self.double_jump_available = False
        
        # Particle trail system
        self.trail_particles = []
        
    def update(self, platforms, coins, particles, audio_energy, beat_detected, frame_num):
        # Handle jump buffering and coyote time
        if self.on_ground:
            self.coyote_timer = 10
            self.double_jump_available = True
        else:
            self.coyote_timer = max(0, self.coyote_timer - 1)

        if beat_detected:
            self.jump_buffer = 10
        else:
            self.jump_buffer = max(0, self.jump_buffer - 1)

        # Update dance moves based on audio energy and combo
        self._update_dance_moves(audio_energy, beat_detected)
        
        # Update expressions
        self._update_expressions(audio_energy, beat_detected)

        # Handle beat-based actions with enhanced variety
        if beat_detected and frame_num - self.last_beat_frame > 10:
            self.last_beat_frame = frame_num
            
            # Find nearest platform ahead for landing targeting
            nearest_platform = None
            min_distance = float('inf')
            
            for platform in platforms:
                if platform.x > self.x and platform.x - self.x < 300:
                    distance = abs(platform.x - self.x)
                    if distance < min_distance:
                        min_distance = distance
                        nearest_platform = platform
            
            if self.jump_buffer > 0 and self.coyote_timer > 0 and nearest_platform:
                # Calculate jump to land on platform
                distance_x = nearest_platform.x - self.x
                distance_y = nearest_platform.y - self.y
                
                # Jump strength based on audio energy and distance
                base_jump = 15 + audio_energy * 10
                if distance_y < -100:  # Platform is higher
                    jump_strength = base_jump + 8
                else:
                    jump_strength = base_jump
                
                self.vel_y = -jump_strength
                self.on_ground = False
                self.jump_animation = 25
                self.target_platform = nearest_platform
                
                # Determine jump style based on energy and combo
                self._determine_jump_style(audio_energy, jump_strength)
                
                # Add jump particles with variety
                self._create_jump_particles(particles, audio_energy)
                
            elif not self.on_ground and audio_energy > 0.6 and self.double_jump_available:
                # Double jump / air control
                self.vel_y -= 8
                self.double_jump_available = False
                self.air_trick = "double_jump"
                self.air_trick_timer = 15
                self.glow_intensity = 20
                
                # Double jump particles
                for i in range(8):
                    particles.append(Particle(
                        self.x + self.width/2 + random.randint(-5, 5),
                        self.y + self.height/2,
                        random.randint(-2, 2),
                        random.randint(-4, -1),
                        ROBOT_HIGHLIGHT,
                        random.randint(15, 25)
                    ))
        
        # Update flip rotation
        if self.is_flipping:
            self.flip_rotation += self.flip_speed
            if abs(self.flip_rotation) >= 360:
                self.flip_rotation = 0
                self.is_flipping = False
                self.flip_speed = 0
        
        # Update air tricks
        if self.air_trick_timer > 0:
            self.air_trick_timer -= 1
            if self.air_trick_timer == 0:
                self.air_trick = None
        
        # Speed based on audio energy with dance influence
        base_speed = 4
        energy_speed = audio_energy * 12
        dance_speed_mod = 1.0
        
        if self.dance_state == "arm_swing":
            dance_speed_mod = 1.2
        elif self.dance_state == "head_bob":
            dance_speed_mod = 1.1
        
        target_speed = (base_speed + energy_speed + self.speed_boost) * dance_speed_mod
        
        # Smooth speed transitions
        if abs(self.vel_x - target_speed) > 0.5:
            self.vel_x += (target_speed - self.vel_x) * 0.1
        else:
            self.vel_x = target_speed
        
        # Apply gravity
        if not self.on_ground:
            self.vel_y += 0.6
        
        # Update position
        old_y = self.y
        self.x += self.vel_x
        self.y += self.vel_y
        
        # Create trail particles when moving fast
        if self.vel_x > 10 or self.glow_intensity > 15:
            if random.random() < 0.3:
                particles.append(Particle(
                    self.x + random.randint(0, self.width),
                    self.y + random.randint(0, self.height),
                    random.randint(-2, 0),
                    random.randint(-1, 1),
                    ROBOT_LIGHT_ORANGE,
                    random.randint(10, 20),
                    follow_robot=True
                ))
        
        # Platform collision with enhanced landing detection
        was_on_ground = self.on_ground
        self.on_ground = False
        
        for platform in platforms:
            if (self.x < platform.x + platform.width and 
                self.x + self.width > platform.x and
                self.y + self.height > platform.y and
                self.y + self.height < platform.y + platform.height + 20):
                
                if self.vel_y > 0:  # Falling
                    self.y = platform.y - self.height
                    self.vel_y = 0
                    self.on_ground = True
                    
                    # Landing animation and effects with style consideration
                    if not was_on_ground:
                        self.landing_animation = 15
                        self._handle_landing(platform, particles)
                    
                    # Platform-specific effects
                    if platform.special:
                        self.hit_animation = 10
                        self.speed_boost = min(10, self.speed_boost + 3)
                        platform.hit()
                        self.expression = "excited"
                        self.expression_timer = 30
                    
                    # Bounce platforms
                    if hasattr(platform, 'bounce') and platform.bounce:
                        self.vel_y = -20
                        self.on_ground = False
                        self.jump_animation = 20
                        self.is_flipping = True
                        self.flip_speed = 25
                        
                        # Bounce particles
                        for i in range(12):
                            particles.append(Particle(
                                self.x + self.width/2,
                                self.y + self.height,
                                random.randint(-4, 4),
                                random.randint(-12, -6),
                                BOUNCE_PLATFORM_COLOR,
                                random.randint(25, 45)
                            ))
        
        # Coin collection with enhanced effects
        for coin in coins:
            if not coin.collected:
                coin_distance = math.sqrt((self.x + self.width/2 - coin.x)**2 + 
                                        (self.y + self.height/2 - coin.y)**2)
                if coin_distance < 30:
                    if coin.collect():
                        self.coins_collected += 1
                        self.combo_multiplier = min(3.0, self.combo_multiplier + 0.1)
                        self.speed_boost = min(8, self.speed_boost + 1)
                        self.glow_intensity = 25
                        self.expression = "excited"
                        self.expression_timer = 20
                        
                        # Enhanced coin collection particles
                        for i in range(20):
                            particles.append(Particle(
                                coin.x + random.randint(-8, 8),
                                coin.y + random.randint(-8, 8),
                                random.randint(-4, 4),
                                random.randint(-8, -3),
                                COIN_GOLD if i < 15 else ROBOT_HIGHLIGHT,
                                random.randint(25, 40),
                                follow_robot=(i < 5)
                            ))
        
        # Keep robot in bounds vertically
        if self.y > HEIGHT - 100:
            self.y = HEIGHT - 100
            self.vel_y = 0
            self.on_ground = True
            self.landing_animation = 10
        
        # Decay effects
        if self.speed_boost > 0:
            self.speed_boost -= 0.03
        if self.combo_multiplier > 1.0:
            self.combo_multiplier -= 0.003
        if self.glow_intensity > 0:
            self.glow_intensity -= 1
        
        # Update timers
        if self.dance_timer > 0:
            self.dance_timer -= 1
        if self.expression_timer > 0:
            self.expression_timer -= 1
        
        # Update animations
        self.animation_frame += 1
        if self.jump_animation > 0:
            self.jump_animation -= 1
        if self.hit_animation > 0:
            self.hit_animation -= 1
        if self.landing_animation > 0:
            self.landing_animation -= 1
    
    def _update_dance_moves(self, audio_energy, beat_detected):
        """Update dance move states based on audio"""
        if beat_detected and self.on_ground:
            # Change dance move based on energy and combo
            if audio_energy > 0.7:
                self.dance_state = "arm_swing"
                self.dance_timer = 40
                self.dance_intensity = min(1.0, audio_energy)
            elif audio_energy > 0.5:
                self.dance_state = "head_bob"
                self.dance_timer = 30
                self.dance_intensity = audio_energy
            elif self.combo_multiplier > 2.0:
                self.dance_state = "shoulder_shrug"
                self.dance_timer = 25
                self.dance_intensity = 0.8
        
        if self.dance_timer == 0:
            self.dance_state = "normal"
            self.dance_intensity = 0
    
    def _update_expressions(self, audio_energy, beat_detected):
        """Update facial expressions"""
        if self.expression_timer == 0:
            if audio_energy > 0.8:
                self.expression = "excited"
                self.expression_timer = 20
            elif self.combo_multiplier > 2.5:
                self.expression = "focused"
                self.expression_timer = 30
            elif beat_detected and random.random() < 0.3:
                self.expression = "surprised"
                self.expression_timer = 15
            else:
                self.expression = "normal"
    
    def _determine_jump_style(self, audio_energy, jump_strength):
        """Determine what kind of jump/flip to perform"""
        if audio_energy > 0.8 and jump_strength > 25:
            # Big flip
            self.is_flipping = True
            self.flip_speed = 30 + audio_energy * 20
            self.air_trick = "flip"
            self.air_trick_timer = 25
        elif self.combo_multiplier > 2.0:
            # Spin jump
            self.is_flipping = True
            self.flip_speed = 15
            self.air_trick = "spin"
            self.air_trick_timer = 20
        elif random.random() < 0.4:
            # Regular air trick
            tricks = ["twist", "spin"]
            self.air_trick = random.choice(tricks)
            self.air_trick_timer = 15
    
    def _create_jump_particles(self, particles, audio_energy):
        """Create particles for jump with variety based on audio energy"""
        particle_count = int(16 + audio_energy * 10)
        colors = PARTICLE_COLORS + [ROBOT_LIGHT_ORANGE, ROBOT_HIGHLIGHT]
        
        for i in range(particle_count):
            particles.append(Particle(
                self.x + self.width/2 + random.randint(-15, 15),
                self.y + self.height,
                random.randint(-5, 5),
                random.randint(-10, -4),
                random.choice(colors),
                random.randint(20, 50),
                follow_robot=(i < 3 and audio_energy > 0.6)
            ))
    
    def _handle_landing(self, platform, particles):
        """Handle landing effects and animations"""
        # Check if this was the targeted platform
        if platform == self.target_platform:
            self.combo_multiplier = min(3.0, self.combo_multiplier + 0.5)
            self.speed_boost = min(8, self.speed_boost + 2)
            self.glow_intensity = 30
            self.expression = "excited"
            self.expression_timer = 25
            
            # Perfect landing particles
            for i in range(24):
                particles.append(Particle(
                    self.x + self.width/2 + random.randint(-20, 20),
                    self.y + self.height,
                    random.randint(-6, 6),
                    random.randint(-12, -6),
                    COIN_YELLOW if i < 15 else ROBOT_HIGHLIGHT,
                    random.randint(30, 60),
                    follow_robot=(i < 4)
                ))
        else:
            # Reset combo for missed targets
            self.combo_multiplier = max(1.0, self.combo_multiplier - 0.2)
        
        self.target_platform = None
        self.is_flipping = False
        self.flip_rotation = 0
        self.flip_speed = 0
    
    def draw(self, screen, camera_x):
        draw_x = self.x - camera_x
        
        # Glow effect
        if self.glow_intensity > 0:
            glow_size = int(self.glow_intensity * 2)
            for i in range(3):
                pygame.draw.ellipse(screen, ROBOT_LIGHT_ORANGE, 
                                  (draw_x - glow_size + i*2, self.y - glow_size//2 + i, 
                                   self.width + glow_size*2 - i*4, self.height + glow_size - i*2))
        
        # Robot body with enhanced animations
        body_width = self.width
        body_height = self.height
        body_y = self.y
        body_x_offset = 0
        
        # Landing squash effect
        if self.landing_animation > 0:
            squash_factor = self.landing_animation / 15.0
            body_width = int(self.width * (1 + squash_factor * 0.3))
            body_height = int(self.height * (1 - squash_factor * 0.2))
            body_y = self.y + (self.height - body_height)
        
        # Dance move body modifications
        if self.dance_state == "shoulder_shrug" and self.dance_timer > 0:
            shrug_amount = math.sin(self.animation_frame * 0.3) * self.dance_intensity * 5
            body_y += int(shrug_amount)
        elif self.dance_state == "head_bob" and self.dance_timer > 0:
            bob_amount = math.sin(self.animation_frame * 0.4) * self.dance_intensity * 3
            body_y += int(bob_amount)
        elif self.dance_state == "arm_swing" and self.dance_timer > 0:
            swing_amount = math.sin(self.animation_frame * 0.5) * self.dance_intensity * 2
            body_x_offset = int(swing_amount)
        
        # Handle flip rotation
        if self.is_flipping or self.flip_rotation != 0:
            # Draw rotated robot (simplified - just flip the drawing)
            flip_factor = math.sin(math.radians(self.flip_rotation))
            body_height = max(10, int(self.height * abs(math.cos(math.radians(self.flip_rotation)))))
            body_width = int(self.width * (1 + abs(flip_factor) * 0.5))
        
        body_rect = pygame.Rect(draw_x - (body_width - self.width)//2 + body_x_offset, 
                               body_y, body_width, body_height)
        
        # Body color variation based on state
        body_color = ROBOT_ORANGE
        if self.dance_state != "normal":
            body_color = tuple(min(255, c + 20) for c in ROBOT_ORANGE)
        
        pygame.draw.rect(screen, body_color, body_rect, border_radius=8)
        pygame.draw.rect(screen, ROBOT_DARK_ORANGE, body_rect, 3, border_radius=8)
        
        # Enhanced eyes with expressions
        eye_size = 8
        eye_y_offset = 0
        pupil_size = eye_size // 2
        
        # Expression-based eye modifications
        if self.expression == "excited":
            eye_size = 10
            eye_y_offset = -1
        elif self.expression == "surprised":
            eye_size = 12
            pupil_size = eye_size // 3
        elif self.expression == "focused":
            eye_y_offset = -2
            pupil_size = eye_size // 1.5
        
        if self.jump_animation > 0:
            eye_y_offset -= 2  # Eyes look up when jumping
        elif self.landing_animation > 0:
            eye_y_offset += 2   # Eyes look down when landing
        
        # Head bob for dance
        if self.dance_state == "head_bob":
            head_bob = math.sin(self.animation_frame * 0.4) * self.dance_intensity * 4
            eye_y_offset += int(head_bob)
            
        left_eye = (draw_x + body_x_offset + 10, body_y + 12 + eye_y_offset)
        right_eye = (draw_x + body_x_offset + body_width - 18, body_y + 12 + eye_y_offset)
        
        pygame.draw.circle(screen, (255, 255, 255), left_eye, eye_size)
        pygame.draw.circle(screen, (255, 255, 255), right_eye, eye_size)
        
        # Enhanced pupil direction and expression
        pupil_offset_x = 0
        pupil_offset_y = 0
        
        if abs(self.vel_x) > 6:
            pupil_offset_x = 2
        if self.air_trick == "double_jump":
            pupil_offset_y = -2
        elif self.expression == "surprised":
            pupil_offset_y = -1
        
        pygame.draw.circle(screen, (0, 0, 0), 
                         (left_eye[0] + pupil_offset_x, left_eye[1] + pupil_offset_y), pupil_size)
        pygame.draw.circle(screen, (0, 0, 0), 
                         (right_eye[0] + pupil_offset_x, right_eye[1] + pupil_offset_y), pupil_size)
        
        # Enhanced running animation with dance moves
        if self.on_ground:
            leg_speed = 0.4 + (self.vel_x / 20)
            if self.dance_state == "arm_swing":
                leg_speed *= 1.5
            
            leg_offset = math.sin(self.animation_frame * leg_speed) * 10
            leg_y = body_y + body_height
            
            # Arm swing dance move - add arm animations
            if self.dance_state == "arm_swing" and self.dance_timer > 0:
                arm_swing = math.sin(self.animation_frame * 0.5) * self.dance_intensity * 15
                # Left arm
                pygame.draw.rect(screen, ROBOT_DARK_ORANGE, 
                               (draw_x + body_x_offset - 5, body_y + 15, 6, 20 + int(arm_swing)))
                # Right arm
                pygame.draw.rect(screen, ROBOT_DARK_ORANGE, 
                               (draw_x + body_width + body_x_offset - 1, body_y + 15, 6, 20 - int(arm_swing)))
            
            # Enhanced legs with dance variation
            leg_width = 8
            if self.dance_state == "shoulder_shrug":
                leg_width = 10  # Wider stance for shrugging
            
            # Left leg
            pygame.draw.rect(screen, ROBOT_DARK_ORANGE, 
                           (draw_x + body_x_offset + 8, leg_y, leg_width, 15 + leg_offset))
            # Right leg
            pygame.draw.rect(screen, ROBOT_DARK_ORANGE, 
                           (draw_x + body_width + body_x_offset - 16, leg_y, leg_width, 15 - leg_offset))
            
            # Enhanced foot particles when running fast
            if self.vel_x > 8 and self.animation_frame % 6 == 0:
                foot_particle_color = (150, 150, 150)
                if self.dance_state != "normal":
                    foot_particle_color = ROBOT_LIGHT_ORANGE
                pygame.draw.circle(screen, foot_particle_color, 
                                 (draw_x + random.randint(0, self.width), 
                                  int(leg_y + 15)), random.randint(2, 4))
        
        # Enhanced jump animation with air tricks
        if self.jump_animation > 0:
            # Enhanced air trail effect
            trail_length = min(max(self.jump_animation, 1), 12)
            for i in range(trail_length):
                alpha = (trail_length - i) / trail_length
                trail_intensity = int(255 * alpha)
                trail_color = (trail_intensity, int(trail_intensity * 0.7), int(trail_intensity * 0.3))
                
                trail_x = draw_x - self.vel_x * i * 0.5
                trail_y = body_y + i * 2
                trail_width = int(body_width * alpha)
                trail_height = int(body_height * alpha)
                
                if trail_width > 0 and trail_height > 0:
                    pygame.draw.rect(screen, trail_color, 
                                   (trail_x, trail_y, trail_width, trail_height), border_radius=1)
            
            # Redraw robot on top of trail
            pygame.draw.rect(screen, body_color, body_rect, border_radius=8)
            pygame.draw.rect(screen, ROBOT_DARK_ORANGE, body_rect, 3, border_radius=8)
            
            # Redraw eyes on top
            pygame.draw.circle(screen, (255, 255, 255), left_eye, eye_size)
            pygame.draw.circle(screen, (255, 255, 255), right_eye, eye_size)
            pygame.draw.circle(screen, (0, 0, 0), 
                             (left_eye[0] + pupil_offset_x, left_eye[1] + pupil_offset_y), pupil_size)
            pygame.draw.circle(screen, (0, 0, 0), 
                             (right_eye[0] + pupil_offset_x, right_eye[1] + pupil_offset_y), pupil_size)
            
            # Air trick visual effects
            if self.air_trick == "spin":
                # Draw spinning indicators around robot
                for i in range(4):
                    angle = (self.animation_frame * 10 + i * 90) % 360
                    spin_x = draw_x + body_width/2 + math.cos(math.radians(angle)) * 25
                    spin_y = body_y + body_height/2 + math.sin(math.radians(angle)) * 15
                    pygame.draw.circle(screen, ROBOT_HIGHLIGHT, (int(spin_x), int(spin_y)), 3)
            
            elif self.air_trick == "twist":
                # Draw twisting motion lines
                for i in range(3):
                    twist_offset = math.sin(self.animation_frame * 0.5 + i) * 10
                    pygame.draw.line(screen, ROBOT_HIGHLIGHT,
                                   (draw_x + body_width/2 - 10, body_y + i * 10 + twist_offset),
                                   (draw_x + body_width/2 + 10, body_y + i * 10 - twist_offset), 2)
            
            elif self.air_trick == "double_jump":
                # Draw double jump boost effect
                for i in range(6):
                    boost_y = body_y + body_height + i * 5
                    boost_size = 6 - i
                    if boost_size > 0:
                        pygame.draw.circle(screen, ROBOT_HIGHLIGHT, 
                                         (draw_x + body_width/2, int(boost_y)), boost_size)

        # Enhanced hit animation with more dynamic sparkles
        if self.hit_animation > 0:
            for i in range(12):
                sparkle_angle = (i * 30 + self.animation_frame * 5) % 360
                sparkle_distance = 20 + (self.hit_animation / 10) * 10
                sparkle_x = draw_x + body_width/2 + math.cos(math.radians(sparkle_angle)) * sparkle_distance
                sparkle_y = body_y + body_height/2 + math.sin(math.radians(sparkle_angle)) * sparkle_distance
                sparkle_size = random.randint(2, 8)
                
                # Different sparkle colors based on combo
                if self.combo_multiplier > 2.0:
                    sparkle_color = COIN_GOLD
                else:
                    sparkle_color = (255, 255, 255)
                
                pygame.draw.circle(screen, sparkle_color, 
                                 (int(sparkle_x), int(sparkle_y)), sparkle_size)
        
        # Enhanced speed boost indicator with dynamic trail
        if self.speed_boost > 3:
            for i in range(5):
                trail_x = draw_x - 40 - i*8
                trail_y = body_y + body_height//2 + math.sin(self.animation_frame * 0.5 + i) * 8
                trail_size = max(1, 5 - i)
                trail_alpha = max(0.3, 1.0 - i * 0.2)
                
                # Color based on speed boost level
                if self.speed_boost > 7:
                    trail_color = COIN_GOLD
                elif self.speed_boost > 5:
                    trail_color = ROBOT_HIGHLIGHT
                else:
                    trail_color = ROBOT_LIGHT_ORANGE
                
                pygame.draw.circle(screen, trail_color, (int(trail_x), int(trail_y)), trail_size)
        
        # Combo multiplier visual indicator
        if self.combo_multiplier > 1.5:
            combo_glow = int((self.combo_multiplier - 1.0) * 30)
            combo_rings = int(self.combo_multiplier)
            for i in range(combo_rings):
                ring_radius = 30 + i * 10 + math.sin(self.animation_frame * 0.2) * 3
                ring_thickness = max(1, 3 - i)
                pygame.draw.circle(screen, COIN_YELLOW, 
                                 (draw_x + body_width/2, body_y + body_height/2), 
                                 int(ring_radius), ring_thickness)

class Platform:
    def __init__(self, x, y, width, height, special=False, bounce=False):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.special = special
        self.bounce = bounce
        self.hit_animation = 0
        self.glow_animation = 0
        
    def hit(self):
        self.hit_animation = 15
        self.glow_animation = 30
        
    def update(self):
        if self.hit_animation > 0:
            self.hit_animation -= 1
        if self.glow_animation > 0:
            self.glow_animation -= 1
    
    def draw(self, screen, camera_x):
        draw_x = self.x - camera_x
        
        # Only draw if on screen
        if draw_x + self.width > 0 and draw_x < WIDTH:
            if self.bounce:
                color = BOUNCE_PLATFORM_COLOR
            elif self.special:
                color = SPECIAL_PLATFORM_COLOR
            else:
                color = PLATFORM_COLOR
            
            # Hit animation effect
            if self.hit_animation > 0:
                color = tuple(min(255, c + 70) for c in color)
            
            # Enhanced glow effect for special platforms
            if self.glow_animation > 0:
                glow_size = int(self.glow_animation / 6)
                for i in range(3):
                    glow_alpha = (self.glow_animation - i * 5) / 30.0
                    if glow_alpha > 0:
                        glow_rect = pygame.Rect(draw_x - glow_size - i*2, self.y - glow_size - i*2, 
                                              self.width + (glow_size + i*2)*2, self.height + (glow_size + i*2)*2)
                        glow_color = tuple(min(255, int(c + glow_alpha * 50)) for c in color)
                        pygame.draw.rect(screen, glow_color, glow_rect, border_radius=5)
            
            platform_rect = pygame.Rect(draw_x, self.y, self.width, self.height)
            pygame.draw.rect(screen, color, platform_rect)
            pygame.draw.rect(screen, (200, 200, 200), platform_rect, 2)
            
            # Enhanced special platform indicators
            if self.special:
                # Animated pulsing dots with trails
                for i in range(3):
                    dot_x = draw_x + (i + 1) * self.width // 4
                    dot_y = self.y + self.height // 2
                    pulse = math.sin(pygame.time.get_ticks() * 0.01 + i) * 0.3 + 0.7
                    dot_size = int(4 * pulse)
                    
                    # Draw dot with glow
                    pygame.draw.circle(screen, (255, 255, 255), (dot_x, dot_y), dot_size + 2)
                    pygame.draw.circle(screen, SPECIAL_PLATFORM_COLOR, (dot_x, dot_y), dot_size)
                    
                    # Add small particle trail
                    if random.random() < 0.1:
                        trail_x = dot_x + random.randint(-5, 5)
                        trail_y = dot_y + random.randint(-3, 3)
                        pygame.draw.circle(screen, (255, 255, 255), (trail_x, trail_y), 1)
            
            if self.bounce:
                # Enhanced bounce indicator with animation
                bounce_y = self.y + 5 + math.sin(pygame.time.get_ticks() * 0.03) * 4
                arrow_size = 8 + math.sin(pygame.time.get_ticks() * 0.05) * 2
                bounce_pulse = math.sin(pygame.time.get_ticks() * 0.02) * 0.5 + 0.5
                
                # Draw animated bounce arrow
                pygame.draw.polygon(screen, (255, 255, 255), [
                    (draw_x + self.width//2, int(bounce_y)),
                    (draw_x + self.width//2 - int(arrow_size), int(bounce_y + arrow_size * 1.5)),
                    (draw_x + self.width//2 + int(arrow_size), int(bounce_y + arrow_size * 1.5))
                ])
                
                # Add bounce energy lines
                for i in range(3):
                    line_y = bounce_y + arrow_size * 2 + i * 3
                    line_width = int((3-i) * 2 * bounce_pulse) + 2
                    if line_width > 0:
                        pygame.draw.line(screen, BOUNCE_PLATFORM_COLOR,
                                       (draw_x + self.width//2 - line_width, int(line_y)),
                                       (draw_x + self.width//2 + line_width, int(line_y)), 2)

class PlatformGenerator:
    def __init__(self):
        self.platforms = []
        self.coins = []
        self.last_platform_x = 0
        self.generate_initial_platforms()
    
    def generate_initial_platforms(self):
        # Starting platform
        self.platforms.append(Platform(0, HEIGHT - 60, 200, 160))
        self.last_platform_x = 200
        
        # Generate ahead
        for _ in range(25):
            self.generate_next_platform()
    
    def generate_next_platform(self):
        gap = random.randint(60, 180)
        width = random.randint(80, 160)
        height = random.randint(10, 50)
        y = random.randint(HEIGHT - 500, HEIGHT - 150)
        
        # Enhanced platform type distribution
        platform_type = random.random()
        if platform_type < 0.25:  # Increased special platform chance
            special = True
            bounce = False
        elif platform_type < 0.35:  # Increased bounce platform chance
            special = False
            bounce = True
        else:
            special = False
            bounce = False
        
        platform = Platform(self.last_platform_x + gap, y, width, height, special, bounce)
        self.platforms.append(platform)
        
        # Enhanced coin placement with patterns
        if random.random() < 0.7:  # Increased coin chance
            coin_count = random.randint(1, 4)  # More coins possible
            
            # Different coin patterns
            pattern = random.choice(["scattered", "arc", "line"])
            
            if pattern == "scattered":
                for i in range(coin_count):
                    coin_x = platform.x + random.randint(0, platform.width)
                    coin_y = platform.y - random.randint(40, 120)
                    self.coins.append(Coin(coin_x, coin_y))
            
            elif pattern == "arc":
                # Coins in an arc above platform
                for i in range(coin_count):
                    progress = i / max(1, coin_count - 1)
                    coin_x = platform.x + progress * platform.width
                    arc_height = math.sin(progress * math.pi) * 80 + 40
                    coin_y = platform.y - arc_height
                    self.coins.append(Coin(coin_x, coin_y))
            
            elif pattern == "line":
                # Coins in a line leading to platform
                start_x = platform.x - gap // 2
                for i in range(coin_count):
                    coin_x = start_x + i * (gap // (coin_count + 1))
                    coin_y = platform.y - random.randint(30, 80)
                    self.coins.append(Coin(coin_x, coin_y))
        
        # Enhanced floating coins with bonus clusters
        if random.random() < 0.4:
            cluster_size = random.randint(1, 3)
            center_x = self.last_platform_x + gap // 2
            center_y = random.randint(HEIGHT - 400, HEIGHT - 200)
            
            for i in range(cluster_size):
                coin_x = center_x + random.randint(-30, 30)
                coin_y = center_y + random.randint(-20, 20)
                self.coins.append(Coin(coin_x, coin_y))
        
        self.last_platform_x = platform.x + platform.width
    
    def update(self, camera_x):
        # Remove old platforms and coins
        self.platforms = [p for p in self.platforms if p.x + p.width > camera_x - 200]
        self.coins = [c for c in self.coins if c.x > camera_x - 200]
        
        # Generate new platforms
        while self.last_platform_x < camera_x + WIDTH * 2:
            self.generate_next_platform()
        
        # Update existing platforms and coins
        for platform in self.platforms:
            platform.update()
        for coin in self.coins:
            coin.update()
    
    def get_platforms(self):
        return self.platforms
    
    def get_coins(self):
        return self.coins

def extract_audio_with_ffmpeg(video_path):
    """Extract audio from video using ffmpeg and return raw audio data"""
    print("Extracting audio from video...")
    
    # Create temporary WAV file
    temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    temp_wav.close()
    
    try:
        # Use ffmpeg to extract audio as WAV
        cmd = [
            'ffmpeg', '-i', video_path, 
            '-vn', '-acodec', 'pcm_s16le', 
            '-ar', '22050', '-ac', '1', 
            '-y', temp_wav.name
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"FFmpeg error: {result.stderr}")
            # Fallback to simpler command
            cmd = ['ffmpeg', '-i', video_path, '-vn', '-y', temp_wav.name]
            subprocess.run(cmd, capture_output=True)
        
        # Read WAV file
        with wave.open(temp_wav.name, 'rb') as wav_file:
            frames = wav_file.getnframes()
            sample_rate = wav_file.getframerate()
            duration = frames / sample_rate
            
            # Read audio data
            raw_audio = wav_file.readframes(frames)
            audio_data = np.frombuffer(raw_audio, dtype=np.int16).astype(np.float32)
            audio_data = audio_data / 32768.0  # Normalize to [-1, 1]
        
        return audio_data, sample_rate, duration
    
    except Exception as e:
        print(f"Error extracting audio: {e}")
        # Return dummy data if extraction fails
        return np.array([0.0] * 22050), 22050, 1.0
    
    finally:
        # Clean up temp file
        if os.path.exists(temp_wav.name):
            os.unlink(temp_wav.name)

def get_video_duration(video_path):
    """Get video duration using ffprobe"""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-show_entries', 
            'format=duration', '-of', 'csv=p=0', video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return float(result.stdout.strip())
    except:
        return 10.0  # Default fallback

def extract_audio_features(video_path):
    """Extract audio from video and compute energy features with enhanced beat detection"""
    
    # Get video duration
    duration = get_video_duration(video_path)
    
    # Try to extract audio
    try:
        audio_data, sample_rate, audio_duration = extract_audio_with_ffmpeg(video_path)
        duration = min(duration, audio_duration)
    except Exception as e:
        print(f"Audio extraction failed: {e}")
        print("Using enhanced synthetic audio features based on video duration...")
        # Generate more sophisticated synthetic features
        total_frames = int(duration * FPS)
        energy_values = []
        beats = []
        
        for i in range(total_frames):
            # Create more musical synthetic energy pattern
            t = i / FPS
            # Base rhythm
            energy = 0.4 + 0.3 * math.sin(t * 2 * math.pi * 2)  # 2 Hz base
            # Add higher frequency components
            energy += 0.2 * math.sin(t * 2 * math.pi * 4)  # 4 Hz
            energy += 0.1 * math.sin(t * 2 * math.pi * 8)  # 8 Hz
            # Add some randomness
            energy += 0.1 * random.random()
            energy_values.append(max(0, min(1, energy)))
            
            # Add beats with musical timing (roughly 120 BPM)
            if i % 30 == 0 and random.random() > 0.2:  # Every 0.5 seconds
                beats.append(i)
            # Add some off-beat elements
            elif i % 45 == 0 and random.random() > 0.6:
                beats.append(i)
        
        return energy_values, beats, duration
    
    # Enhanced audio processing
    chunk_size = max(1, sample_rate // FPS)
    energy_values = []
    spectral_values = []
    
    # Apply simple high-pass filter to emphasize beats
    if len(audio_data) > 1:
        audio_data = np.diff(audio_data, prepend=audio_data[0])
    
    for i in range(0, len(audio_data), chunk_size):
        chunk = audio_data[i:i+chunk_size]
        if len(chunk) > 0:
            # Enhanced RMS energy calculation
            energy = np.sqrt(np.mean(chunk**2))
            
            # Add peak detection within chunk
            if len(chunk) > 10:
                peaks = np.where(np.abs(chunk) > np.std(chunk) * 2)[0]
                if len(peaks) > 0:
                    energy *= 1.3  # Boost energy for chunks with peaks
            
            energy_values.append(energy)
            
            # Enhanced spectral analysis
            if len(chunk) > 1:
                # Simple measure of spectral change/novelty
                spectral = np.mean(np.abs(np.diff(chunk)))
                spectral_values.append(spectral)
            else:
                spectral_values.append(0)
    
    # Normalize values with better scaling
    if energy_values:
        # Use percentile-based normalization to avoid outliers
        p95 = np.percentile(energy_values, 95)
        energy_values = [min(1.0, e / p95) for e in energy_values]
    
    if spectral_values:
        max_spectral = max(spectral_values) if spectral_values else 1
        if max_spectral > 0:
            spectral_values = [s / max_spectral for s in spectral_values]
    
    # Much enhanced beat detection
    beats = []
    if len(energy_values) > 4:
        # Adaptive threshold based on local energy
        window_size = 20
        beat_threshold = 0.3
        min_beat_gap = 6  # Reduced for more responsive beats
        
        for i in range(window_size, len(energy_values) - window_size):
            local_window = energy_values[max(0, i-window_size):min(len(energy_values), i+window_size)]
            local_mean = np.mean(local_window)
            local_std = np.std(local_window)
            
            # Adaptive threshold
            threshold = max(beat_threshold, local_mean + local_std * 0.5)
            
            # Peak detection with multiple criteria
            is_peak = (energy_values[i] > threshold and 
                      energy_values[i] > energy_values[i-1] and 
                      energy_values[i] > energy_values[i+1])
            
            # Additional spectral novelty check
            if i < len(spectral_values) and spectral_values[i] > 0.6:
                is_peak = is_peak or energy_values[i] > local_mean * 1.2
            
            if is_peak:
                # Check minimum gap
                if not beats or i - beats[-1] >= min_beat_gap:
                    beats.append(i)
        
        # Add some guaranteed beats if too few detected
        if len(beats) < duration * 0.5:  # Less than 0.5 beats per second
            for i in range(0, len(energy_values), 30):  # Every 0.5 seconds
                if not any(abs(i - beat) < 5 for beat in beats):
                    beats.append(i)
    
    print(f"Detected {len(beats)} beats in {duration:.1f} seconds ({len(beats)/duration:.1f} BPS)")
    return energy_values, beats, duration

def main(input_video_path, output_path):
    # Extract audio features
    energy_values, beats, duration = extract_audio_features(input_video_path)
    total_frames = int(duration * FPS)
    
    # Initialize game objects
    robot = Robot(50, HEIGHT - 350)
    platform_generator = PlatformGenerator()
    particles = []
    
    # Camera
    camera_x = 0
    
    # Video writer setup
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, FPS, (WIDTH, HEIGHT))
    
    # Create pygame surface
    screen = pygame.Surface((WIDTH, HEIGHT))
    
    print(f"Generating {total_frames} frames with enhanced animations...")
    
    for frame in range(total_frames):
        # Get audio features for current frame
        audio_energy = 0
        beat_detected = False
        
        if frame < len(energy_values):
            audio_energy = energy_values[frame]
            beat_detected = frame in beats
        
        # Enhanced camera shake effect
        camera_shake = 0
        if beat_detected:
            shake_intensity = min(8, int(audio_energy * 12))
            camera_shake = random.randint(-shake_intensity, shake_intensity)
        
        # Camera follows robot smoothly with enhanced movement
        target_camera_x = robot.x - WIDTH // 3 + camera_shake
        # Smoother camera movement that anticipates robot movement
        camera_lerp_speed = 0.08 + (robot.vel_x / 100)  # Faster camera when robot moves fast
        camera_x += (target_camera_x - camera_x) * camera_lerp_speed
        
        # Update game objects with particle tracking
        robot.update(platform_generator.get_platforms(), platform_generator.get_coins(), 
                    particles, audio_energy, beat_detected, frame)
        platform_generator.update(camera_x)
        
        # Update particles with robot position for following effects
        particles = [p for p in particles if p.update(robot.x + robot.width/2, robot.y + robot.height/2)]
        
        # Enhanced background rendering
        screen.fill(BACKGROUND_COLOR)
        
        # Dynamic background with multiple layers
        pulse_strength = int(audio_energy * 30)
        beat_flash = 20 if beat_detected and audio_energy > 0.6 else 0
        
        background_base = tuple(min(255, c + pulse_strength + beat_flash) for c in BACKGROUND_COLOR)
        screen.fill(background_base)
        
        # Multi-layered gradient background
        for i in range(HEIGHT // 3):
            layer_progress = i / (HEIGHT // 3)
            
            # Base gradient
            color = (
                int(BACKGROUND_COLOR[0] + layer_progress * 25),
                int(BACKGROUND_COLOR[1] + layer_progress * 25),
                int(BACKGROUND_COLOR[2] + layer_progress * 40)
            )
            
            # Add beat-reactive color shifts
            if beat_detected:
                color = tuple(min(255, c + int(audio_energy * 30)) for c in color)
            
            # Add combo-based color enhancement
            if robot.combo_multiplier > 2.0:
                combo_bonus = int((robot.combo_multiplier - 2.0) * 20)
                color = (min(255, color[0] + combo_bonus), 
                        min(255, color[1] + combo_bonus//2), 
                        color[2])
            
            pygame.draw.rect(screen, color, (0, i * 3, WIDTH, 3))
        
        # Add moving background elements for depth
        if frame % 5 == 0 and audio_energy > 0.4:
            bg_particle_x = WIDTH + random.randint(0, 50)
            bg_particle_y = random.randint(50, HEIGHT - 50)
            bg_particle_speed = -2 - audio_energy * 3
            particles.append(Particle(
                camera_x + bg_particle_x, bg_particle_y,
                bg_particle_speed, 0,
                (50, 50, 80), 60
            ))
        
        # Draw platforms with enhanced effects
        for platform in platform_generator.get_platforms():
            platform.draw(screen, camera_x)
        
        # Draw coins with enhanced glow
        for coin in platform_generator.get_coins():
            coin.draw(screen, camera_x)
        
        # Draw particles in layers for better depth
        background_particles = [p for p in particles if not p.follow_robot]
        foreground_particles = [p for p in particles if p.follow_robot]
        
        for particle in background_particles:
            particle.draw(screen, camera_x)
        
        # Draw robot
        robot.draw(screen, camera_x)
        
        # Draw foreground particles over robot
        for particle in foreground_particles:
            particle.draw(screen, camera_x)
        
        # Enhanced UI elements with better styling
        font_size = 24
        if hasattr(pygame.font, 'Font'):
            font = pygame.font.Font(None, font_size)
        else:
            font = pygame.font.SysFont('Arial', font_size)
        
        # Coins collected counter with glow effect
        coin_text = font.render(f"Coins: {robot.coins_collected}", True, COIN_GOLD)
        # Add text shadow/glow
        shadow_text = font.render(f"Coins: {robot.coins_collected}", True, (100, 70, 0))
        screen.blit(shadow_text, (12, 12))
        screen.blit(coin_text, (10, 10))
        
        # Enhanced combo multiplier display
        if robot.combo_multiplier > 1.1:
            combo_color = ROBOT_HIGHLIGHT if robot.combo_multiplier > 2.0 else (255, 200, 100)
            combo_text = font.render(f"Combo: {robot.combo_multiplier:.1f}x", True, combo_color)
            shadow_text = font.render(f"Combo: {robot.combo_multiplier:.1f}x", True, (80, 60, 0))
            screen.blit(shadow_text, (12, 42))
            screen.blit(combo_text, (10, 40))
        
        # Enhanced speed boost indicator
        if robot.speed_boost > 1:
            boost_intensity = min(255, int(robot.speed_boost * 30))
            speed_color = (255, boost_intensity, boost_intensity // 2)
            speed_text = font.render("Speed Boost!", True, speed_color)
            screen.blit(speed_text, (10, 70))
        
        # Enhanced audio visualization
        if audio_energy > 0:
            # Audio energy bar with gradient
            energy_bar_width = int(audio_energy * 100)
            bar_rect = pygame.Rect(WIDTH - 120, 10, 100, 12)
            pygame.draw.rect(screen, (60, 60, 60), bar_rect)
            
            # Gradient energy fill
            for i in range(energy_bar_width):
                fill_color_intensity = int(255 * (i / 100))
                fill_color = (fill_color_intensity, 255 - fill_color_intensity//2, 100)
                pygame.draw.rect(screen, fill_color, (WIDTH - 118 + i, 12, 1, 8))
        
        # Enhanced beat indicator with rings
        if beat_detected:
            beat_center = (WIDTH - 30, 50)
            # Multiple ring effect
            for i in range(3):
                ring_size = 15 + i * 5
                ring_alpha = max(0, 255 - i * 80)
                ring_color = (255, ring_alpha, ring_alpha)
                pygame.draw.circle(screen, ring_color, beat_center, ring_size, 2)
            
            # Central beat indicator
            pygame.draw.circle(screen, (255, 255, 255), beat_center, 8)
            pygame.draw.circle(screen, (255, 0, 0), beat_center, 6)
        
        # Dance move indicator
        if robot.dance_state != "normal":
            dance_font = pygame.font.Font(None, 20)
            dance_text = dance_font.render(f"♪ {robot.dance_state.replace('_', ' ').title()} ♪", 
                                         True, ROBOT_HIGHLIGHT)
            screen.blit(dance_text, (10, 100))
        
        # Air trick indicator
        if robot.air_trick and robot.air_trick_timer > 0:
            trick_font = pygame.font.Font(None, 18)
            trick_name = robot.air_trick.replace('_', ' ').title()
            trick_text = trick_font.render(f"✦ {trick_name} ✦", True, (255, 255, 255))
            screen.blit(trick_text, (WIDTH - 150, 80))
        
        # Expression indicator (subtle)
        if robot.expression != "normal" and robot.expression_timer > 10:
            expr_font = pygame.font.Font(None, 16)
            expressions = {
                "excited": "😄", "surprised": "😲", "focused": "😤"
            }
            if robot.expression in expressions:
                expr_text = expr_font.render(expressions[robot.expression], True, (255, 255, 255))
                screen.blit(expr_text, (WIDTH - 200, 50))
        
        # Convert pygame surface to opencv format
        frame_array = pygame.surfarray.array3d(screen)
        frame_array = np.transpose(frame_array, (1, 0, 2))
        frame_array = cv2.cvtColor(frame_array, cv2.COLOR_RGB2BGR)
        
        # Write frame
        out.write(frame_array)
        
        # Enhanced progress indicator
        if frame % 60 == 0:
            progress_percent = frame/total_frames*100
            estimated_remaining = (total_frames - frame) / 60  # seconds remaining
            print(f"Progress: {frame}/{total_frames} frames ({progress_percent:.1f}%) - "
                  f"ETA: {estimated_remaining:.0f}s - "
                  f"Robot Stats: {robot.coins_collected} coins, {robot.combo_multiplier:.1f}x combo, "
                  f"Dance: {robot.dance_state}")
    
    # Cleanup
    out.release()
    pygame.quit()
    
    # Final statistics
    print(f"\n🎮 Animation Complete! 🎮")
    print(f"📊 Final Statistics:")
    print(f"   💰 Coins collected: {robot.coins_collected}")
    print(f"   🔥 Max combo reached: {robot.combo_multiplier:.1f}x")
    print(f"   🎬 Total frames rendered: {total_frames}")
    print(f"   ⏱️  Video duration: {duration:.1f} seconds")
    print(f"   💾 Output saved to: {output_path}")
    print(f"   🎵 Detected beats: {len(beats)} ({len(beats)/duration:.1f} BPS)")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 3:
        print("🤖 Enhanced Music Visualizer - Dynamic Robot Platformer")
        print("Usage: python enhanced_platformer.py <input_video.mp4> <output_animation.mp4>")
        print("\nNew Features:")
        print("  ✨ Robot spinning/flipping on big jumps")
        print("  💃 Dynamic dance moves (head bob, arm swing, shoulder shrug)")
        print("  🎪 Air tricks and double jumps")
        print("  👀 Expressive eye animations and facial expressions")
        print("  🌟 Enhanced particle effects that follow robot")
        print("  🎨 Improved visual feedback and UI elements")
        print("  🎵 Better audio analysis and beat detection")
        sys.exit(1)
    
    input_video = sys.argv[1]
    output_video = sys.argv[2]
    
    if not os.path.exists(input_video):
        print(f"❌ Error: Input video {input_video} not found")
        sys.exit(1)
    
    print(f"🎬 Starting enhanced music visualization...")
    print(f"📽️  Input: {input_video}")
    print(f"📹 Output: {output_video}")
    print("🚀 Initializing enhanced robot animations...\n")
    
    main(input_video, output_video)