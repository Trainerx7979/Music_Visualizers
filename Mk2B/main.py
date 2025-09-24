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

# === Enhanced Music Platformer with Better Graphics & Effects ===

pygame.init()

# Constants
WIDTH, HEIGHT = 768, 768
FPS = 60
BACKGROUND_COLOR = (15, 15, 25)

# Enhanced Robot colors with gradients
ROBOT_ORANGE = (255, 165, 0)
ROBOT_DARK_ORANGE = (255, 140, 0)
ROBOT_LIGHT_ORANGE = (255, 200, 100)
ROBOT_HIGHLIGHT = (255, 255, 150)
ROBOT_SHADOW = (180, 120, 0)

# Platform colors
PLATFORM_COLOR = (100, 100, 100)
SPECIAL_PLATFORM_COLOR = (150, 150, 255)
BOUNCE_PLATFORM_COLOR = (255, 100, 150)
MOVING_PLATFORM_COLOR = (100, 255, 150)

# Enhanced particle colors
PARTICLE_COLORS = [(255, 255, 255), (255, 200, 100), (255, 150, 50), (255, 100, 200)]
COIN_GOLD = (255, 225, 0)
COIN_YELLOW = (190, 190, 0)

# Enemy colors
ENEMY_RED = (255, 80, 80)
ENEMY_DARK_RED = (200, 40, 40)

class Particle:
    def __init__(self, x, y, vel_x, vel_y, color, life=30, particle_type="normal"):
        self.x = x
        self.y = y
        self.vel_x = vel_x
        self.vel_y = vel_y
        self.color = color
        self.life = life
        self.max_life = life
        self.size = random.randint(2, 6)
        self.particle_type = particle_type
        self.rotation = 0
        self.rotation_speed = random.uniform(-0.3, 0.3)
        
    def update(self):
        self.x += self.vel_x
        self.y += self.vel_y
        
        if self.particle_type == "spark":
            self.vel_y += 0.05  # Less gravity for sparks
            self.vel_x *= 0.98  # Air resistance
        else:
            self.vel_y += 0.1  # Normal gravity
            
        self.rotation += self.rotation_speed
        self.life -= 1
        return self.life > 0
    
    def draw(self, screen, camera_x):
        if self.life > 0:
            draw_x = self.x - camera_x
            alpha = self.life / self.max_life
            size = max(1, int(self.size * alpha))
            
            if self.particle_type == "spark":
                # Draw star-shaped spark
                points = []
                for i in range(8):
                    angle = i * math.pi / 4 + self.rotation
                    r = size if i % 2 == 0 else size * 0.4
                    px = draw_x + math.cos(angle) * r
                    py = self.y + math.sin(angle) * r
                    points.append((px, py))
                if len(points) >= 3:
                    pygame.draw.polygon(screen, self.color, points)
            else:
                pygame.draw.circle(screen, self.color, (int(draw_x), int(self.y)), size)

class Enemy:
    def __init__(self, x, y, enemy_type="spiker"):
        self.x = x
        self.y = y
        self.width = 30
        self.height = 30
        self.enemy_type = enemy_type
        self.vel_x = random.uniform(-2, -0.5)
        self.vel_y = 0
        self.animation_frame = 0
        self.alive = True
        self.hit_animation = 0
        self.ground_y = y + self.height
        
        if enemy_type == "floater":
            self.vel_y = random.uniform(-1, 1)
            self.float_amplitude = random.uniform(30, 60)
            self.float_speed = random.uniform(0.02, 0.05)
            self.start_y = y
        elif enemy_type == "bouncer":
            self.vel_y = -8
            self.bounce_power = random.uniform(6, 10)
    
    def update(self, platforms):
        if not self.alive:
            if self.hit_animation > 0:
                self.hit_animation -= 1
            return False
            
        self.animation_frame += 1
        
        if self.enemy_type == "spiker":
            # Ground-based enemy with simple AI
            self.x += self.vel_x
            
        elif self.enemy_type == "floater":
            # Floating enemy with sine wave movement
            self.x += self.vel_x
            self.y = self.start_y + math.sin(self.animation_frame * self.float_speed) * self.float_amplitude
            
        elif self.enemy_type == "bouncer":
            # Bouncing enemy
            self.x += self.vel_x
            self.y += self.vel_y
            self.vel_y += 0.4  # Gravity
            
            # Platform collision for bouncing
            for platform in platforms:
                if (self.x < platform.x + platform.width and 
                    self.x + self.width > platform.x and
                    self.y + self.height > platform.y and
                    self.y + self.height < platform.y + platform.height + 10):
                    
                    if self.vel_y > 0:
                        self.y = platform.y - self.height
                        self.vel_y = -self.bounce_power
        
        return True
    
    def check_collision(self, robot):
        if not self.alive:
            return False
            
        robot_rect = pygame.Rect(robot.x, robot.y, robot.width, robot.height)
        enemy_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        return robot_rect.colliderect(enemy_rect)
    
    def destroy(self):
        self.alive = False
        self.hit_animation = 30
    
    def draw(self, screen, camera_x):
        draw_x = self.x - camera_x
        
        if not self.alive:
            if self.hit_animation > 0:
                # Explosion effect
                for i in range(8):
                    angle = i * math.pi / 4
                    explosion_x = draw_x + self.width/2 + math.cos(angle) * (30 - self.hit_animation)
                    explosion_y = self.y + self.height/2 + math.sin(angle) * (30 - self.hit_animation)
                    size = max(1, self.hit_animation // 5)
                    pygame.draw.circle(screen, (255, 255, 0), (int(explosion_x), int(explosion_y)), size)
            return
        
        if self.enemy_type == "spiker":
            # Draw spiky enemy
            body_rect = pygame.Rect(draw_x, self.y, self.width, self.height)
            pygame.draw.rect(screen, ENEMY_RED, body_rect, border_radius=5)
            pygame.draw.rect(screen, ENEMY_DARK_RED, body_rect, 3, border_radius=5)
            
            # Draw spikes
            spike_count = 6
            for i in range(spike_count):
                spike_x = draw_x + (i + 1) * self.width / (spike_count + 1)
                spike_points = [
                    (spike_x, self.y - 8),
                    (spike_x - 4, self.y),
                    (spike_x + 4, self.y)
                ]
                pygame.draw.polygon(screen, ENEMY_DARK_RED, spike_points)
                
        elif self.enemy_type == "floater":
            # Draw floating enemy with glow
            glow_size = 5 + int(math.sin(self.animation_frame * 0.2) * 3)
            pygame.draw.circle(screen, (100, 50, 50), 
                             (int(draw_x + self.width/2), int(self.y + self.height/2)), 
                             self.width//2 + glow_size)
            pygame.draw.circle(screen, ENEMY_RED, 
                             (int(draw_x + self.width/2), int(self.y + self.height/2)), 
                             self.width//2)
            
            # Floating particles
            if self.animation_frame % 10 == 0:
                return [(draw_x + self.width/2 + random.randint(-5, 5), 
                        self.y + self.height/2 + random.randint(-5, 5))]
                
        elif self.enemy_type == "bouncer":
            # Draw bouncing enemy
            squash_factor = max(0, abs(self.vel_y) / 15)
            enemy_width = int(self.width * (1 + squash_factor * 0.3))
            enemy_height = int(self.height * (1 - squash_factor * 0.2))
            enemy_y = self.y + (self.height - enemy_height)
            
            enemy_rect = pygame.Rect(draw_x - (enemy_width - self.width)//2, enemy_y, 
                                   enemy_width, enemy_height)
            pygame.draw.ellipse(screen, ENEMY_RED, enemy_rect)
            pygame.draw.ellipse(screen, ENEMY_DARK_RED, enemy_rect, 3)
        
        return []

class Coin:
    def __init__(self, x, y, coin_type="normal"):
        self.x = x
        self.y = y
        self.collected = False
        self.animation_frame = 0
        self.float_offset = 0
        self.pulse_scale = 1.0
        self.collection_animation = 0
        self.coin_type = coin_type
        self.rotation = 0
        
    def update(self):
        self.animation_frame += 0.25
        self.rotation += 0.15
        self.float_offset = math.sin(self.animation_frame) * 4
        
        if self.coin_type == "super":
            self.pulse_scale = 1.2 + 0.4 * math.sin(self.animation_frame * 0.3)
        else:
            self.pulse_scale = 1.0 + 0.2 * math.sin(self.animation_frame * 0.15)
            
        if self.collection_animation > 0:
            self.collection_animation -= 1
    
    def collect(self):
        if not self.collected:
            self.collected = True
            self.collection_animation = 25
            return self.coin_type
        return None
    
    def draw(self, screen, camera_x):
        if self.collected and self.collection_animation <= 0:
            return
            
        draw_x = self.x - camera_x
        draw_y = self.y + self.float_offset
        
        if self.collection_animation > 0:
            scale = 1.0 + (25 - self.collection_animation) * 0.15
            alpha = self.collection_animation / 25.0
            size = int(15 * scale * alpha) if self.coin_type == "super" else int(12 * scale * alpha)
        else:
            size = int(15 * self.pulse_scale) if self.coin_type == "super" else int(12 * self.pulse_scale)
        
        if size > 0:
            if self.coin_type == "super":
                # Super coin with extra effects
                for i in range(3):
                    glow_size = size + (3 - i) * 3
                    glow_alpha = 100 - i * 30
                    pygame.draw.circle(screen, (*COIN_YELLOW, glow_alpha), 
                                     (int(draw_x), int(draw_y)), glow_size)
                
                # Rotating sparkles
                for i in range(6):
                    angle = self.rotation + i * math.pi / 3
                    spark_x = draw_x + math.cos(angle) * (size + 8)
                    spark_y = draw_y + math.sin(angle) * (size + 8)
                    pygame.draw.circle(screen, (255, 255, 255), (int(spark_x), int(spark_y)), 2)
            
            # Main coin
            pygame.draw.circle(screen, COIN_YELLOW, (int(draw_x), int(draw_y)), size + 2)
            pygame.draw.circle(screen, COIN_GOLD, (int(draw_x), int(draw_y)), size)
            
            # 3D effect with rotation
            highlight_offset = int(math.cos(self.rotation) * size * 0.3)
            pygame.draw.circle(screen, (255, 255, 200), 
                             (int(draw_x + highlight_offset), int(draw_y - 3)), 
                             max(1, size // 3))

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
        self.jump_animation = 0
        self.hit_animation = 0
        self.landing_animation = 0
        self.speed_boost = 0
        self.last_beat_frame = -10
        self.target_platform = None
        self.coins_collected = 0
        self.super_coins_collected = 0
        self.combo_multiplier = 1.0
        self.glow_intensity = 0
        self.jump_buffer = 0
        self.coyote_timer = 0
        self.dance_move = None
        self.dance_timer = 0
        self.invulnerable_timer = 0
        self.lives = 3
        self.trail_positions = []
        
        # Dance moves
        self.dance_moves = ["spin", "flip", "wave", "pump", "twist"]
        
    def start_dance_move(self):
        if self.dance_timer <= 0:
            self.dance_move = random.choice(self.dance_moves)
            self.dance_timer = 40
    
    def update(self, platforms, coins, particles, enemies, audio_energy, beat_detected, frame_num):
        # Invulnerability countdown
        if self.invulnerable_timer > 0:
            self.invulnerable_timer -= 1
        
        # Trail effect
        self.trail_positions.append((self.x + self.width/2, self.y + self.height/2))
        if len(self.trail_positions) > 8:
            self.trail_positions.pop(0)
        
        # Handle jump buffering and coyote time
        if self.on_ground:
            self.coyote_timer = 15
        else:
            self.coyote_timer = max(0, self.coyote_timer - 1)

        if beat_detected:
            self.jump_buffer = 15
        else:
            self.jump_buffer = max(0, self.jump_buffer - 1)

        # Enhanced beat-based actions
        if beat_detected and frame_num - self.last_beat_frame > 10:
            self.last_beat_frame = frame_num
            
            # Start dance move when jumping
            if self.jump_buffer > 0 and self.coyote_timer > 0:
                self.start_dance_move()
            
            # Find nearest platform
            nearest_platform = None
            min_distance = float('inf')
            
            for platform in platforms:
                if platform.x > self.x and platform.x - self.x < 350:
                    distance = abs(platform.x - self.x)
                    if distance < min_distance:
                        min_distance = distance
                        nearest_platform = platform
            
            if self.jump_buffer > 0 and self.coyote_timer > 0 and nearest_platform:
                distance_x = nearest_platform.x - self.x
                distance_y = nearest_platform.y - self.y
                
                # Enhanced jump calculation
                base_jump = 16 + audio_energy * 12
                if distance_y < -120:
                    jump_strength = base_jump + 8
                else:
                    jump_strength = base_jump
                
                self.vel_y = -jump_strength
                self.on_ground = False
                self.jump_animation = 30
                self.target_platform = nearest_platform
                
                # Enhanced jump particles
                for i in range(40):
                    particle_type = "spark" if random.random() > 0.7 else "normal"
                    particles.append(Particle(
                        self.x + self.width/2 + random.randint(-12, 12),
                        self.y + self.height,
                        random.randint(-4, 4),
                        random.randint(-10, -5),
                        random.choice(PARTICLE_COLORS),
                        random.randint(25, 50),
                        particle_type
                    ))
            
            elif not self.on_ground and audio_energy > 0.6:
                # Air control with visual effects
                self.vel_y -= 4
                self.glow_intensity = 25
                
                # Air dash particles
                for i in range(8):
                    particles.append(Particle(
                        self.x + random.randint(0, self.width),
                        self.y + random.randint(0, self.height),
                        random.randint(-6, -2),
                        random.randint(-3, 3),
                        ROBOT_LIGHT_ORANGE,
                        15,
                        "spark"
                    ))
        
        # Enhanced movement with better smoothing
        base_speed = 5
        energy_speed = audio_energy * 15
        target_speed = base_speed + energy_speed + self.speed_boost
        
        # Smoother acceleration
        speed_diff = target_speed - self.vel_x
        if abs(speed_diff) > 0.3:
            self.vel_x += speed_diff * 0.15
        else:
            self.vel_x = target_speed
        
        # Gravity
        if not self.on_ground:
            self.vel_y += 0.65
        
        # Update position
        old_y = self.y
        self.x += self.vel_x
        self.y += self.vel_y
        
        # Platform collision with enhanced landing detection
        was_on_ground = self.on_ground
        self.on_ground = False
        
        for platform in platforms:
            if (self.x < platform.x + platform.width and 
                self.x + self.width > platform.x and
                self.y + self.height > platform.y and
                self.y + self.height < platform.y + platform.height + 25):
                
                if self.vel_y > 0:
                    self.y = platform.y - self.height
                    self.vel_y = 0
                    self.on_ground = True
                    
                    if not was_on_ground:
                        self.landing_animation = 20
                        
                        # Perfect landing detection with enhanced rewards
                        if platform == self.target_platform:
                            self.combo_multiplier = min(4.0, self.combo_multiplier + 1.8)
                            self.speed_boost = min(12, self.speed_boost + 3)
                            self.glow_intensity = 40
                            
                            # Perfect landing particle explosion
                            for i in range(35):
                                particles.append(Particle(
                                    self.x + self.width/2 + random.randint(-20, 20),
                                    self.y + self.height,
                                    random.randint(-6, 6),
                                    random.randint(-12, -6),
                                    COIN_GOLD,
                                    random.randint(35, 60),
                                    "spark"
                                ))
                        else:
                            self.combo_multiplier = max(1.0, self.combo_multiplier - 0.3)
                        
                        self.target_platform = None
                    
                    # Platform effects
                    if hasattr(platform, 'special') and platform.special:
                        self.hit_animation = 15
                        self.speed_boost = min(12, self.speed_boost + 4)
                        platform.hit()
                    
                    if hasattr(platform, 'bounce') and platform.bounce:
                        self.vel_y = -22
                        self.on_ground = False
                        self.jump_animation = 25
                        self.start_dance_move()
                        
                        # Enhanced bounce particles
                        for i in range(25):
                            particles.append(Particle(
                                self.x + self.width/2,
                                self.y + self.height,
                                random.randint(-5, 5),
                                random.randint(-15, -8),
                                BOUNCE_PLATFORM_COLOR,
                                random.randint(30, 55),
                                "spark"
                            ))
        
        # Enhanced coin collection
        for coin in coins:
            if not coin.collected:
                coin_distance = math.sqrt((self.x + self.width/2 - coin.x)**2 + 
                                        (self.y + self.height/2 - coin.y)**2)
                if coin_distance < 40:
                    coin_type = coin.collect()
                    if coin_type:
                        if coin_type == "super":
                            self.super_coins_collected += 1
                            self.combo_multiplier = min(4.0, self.combo_multiplier + 1.0)
                            self.speed_boost = min(12, self.speed_boost + 2)
                            self.glow_intensity = 35
                            
                            # Super coin particles
                            for i in range(50):
                                particles.append(Particle(
                                    coin.x + random.randint(-8, 8),
                                    coin.y + random.randint(-8, 8),
                                    random.randint(-5, 5),
                                    random.randint(-8, -3),
                                    random.choice([COIN_GOLD, (255, 255, 255), COIN_YELLOW]),
                                    random.randint(30, 50),
                                    "spark"
                                ))
                        else:
                            self.coins_collected += 1
                            self.combo_multiplier = min(4.0, self.combo_multiplier + 0.6)
                            self.speed_boost = min(10, self.speed_boost + 1)
                            self.glow_intensity = 30
                            
                            # Normal coin particles
                            for i in range(40):
                                particles.append(Particle(
                                    coin.x + random.randint(-6, 6),
                                    coin.y + random.randint(-6, 6),
                                    random.randint(-4, 4),
                                    random.randint(-7, -3),
                                    COIN_GOLD,
                                    random.randint(25, 40)
                                ))
        
        # Enemy collision
        for enemy in enemies:
            if enemy.alive and self.invulnerable_timer <= 0 and enemy.check_collision(self):
                if self.vel_y > 5 and self.y < enemy.y:
                    # Destroy enemy by landing on it
                    enemy.destroy()
                    self.vel_y = -12
                    self.combo_multiplier = min(4.0, self.combo_multiplier + 0.8)
                    self.glow_intensity = 25
                    
                    # Enemy destruction particles
                    for i in range(30):
                        particles.append(Particle(
                            enemy.x + enemy.width/2 + random.randint(-10, 10),
                            enemy.y + enemy.height/2 + random.randint(-10, 10),
                            random.randint(-6, 6),
                            random.randint(-10, -4),
                            (255, 100, 100),
                            random.randint(20, 40),
                            "spark"
                        ))
                else:
                    # Take damage
                    self.lives -= 1
                    self.invulnerable_timer = 120
                    self.hit_animation = 30
                    self.combo_multiplier = max(1.0, self.combo_multiplier * 0.5)
                    
                    # Damage particles
                    for i in range(20):
                        particles.append(Particle(
                            self.x + self.width/2,
                            self.y + self.height/2,
                            random.randint(-8, 8),
                            random.randint(-8, -2),
                            (255, 0, 0),
                            random.randint(15, 30)
                        ))
        
        # Keep robot in bounds
        if self.y > HEIGHT - 80:
            self.y = HEIGHT - 80
            self.vel_y = 0
            self.on_ground = True
            self.landing_animation = 15
        
        # Decay effects
        if self.speed_boost > 0:
            self.speed_boost -= 0.02
        if self.combo_multiplier > 1.0:
            self.combo_multiplier -= 0.002
        if self.glow_intensity > 0:
            self.glow_intensity -= 1.2
        if self.dance_timer > 0:
            self.dance_timer -= 1
        
        # Update animations
        self.animation_frame += 1
        if self.jump_animation > 0:
            self.jump_animation -= 1
        if self.hit_animation > 0:
            self.hit_animation -= 1
        if self.landing_animation > 0:
            self.landing_animation -= 1
    
    def draw(self, screen, camera_x):
        draw_x = self.x - camera_x
        
        # Draw trail effect
        for i, (trail_x, trail_y) in enumerate(self.trail_positions[:-1]):
            trail_draw_x = trail_x - camera_x
            alpha = (i + 1) / len(self.trail_positions)
            trail_size = int(alpha * 8)
            if trail_size > 0:
                trail_color = (*ROBOT_LIGHT_ORANGE, int(alpha * 100))
                pygame.draw.circle(screen, ROBOT_LIGHT_ORANGE, 
                                 (int(trail_draw_x), int(trail_y)), trail_size)
        
        # Enhanced glow effect
        if self.glow_intensity > 0 or self.invulnerable_timer > 0:
            glow_size = int(self.glow_intensity * 1.8) if self.invulnerable_timer <= 0 else 15
            glow_color = ROBOT_LIGHT_ORANGE if self.invulnerable_timer <= 0 else (255, 100, 100)
            
            for i in range(4):
                current_glow_size = glow_size + (4 - i) * 3
                if current_glow_size > 0:
                    pygame.draw.ellipse(screen, glow_color, 
                                      (draw_x - current_glow_size, self.y - current_glow_size//2, 
                                       self.width + current_glow_size*2, self.height + current_glow_size))
        
        # Robot body with enhanced landing squash and dance moves
        body_width = self.width
        body_height = self.height
        body_y = self.y
        body_rotation = 0
        
        # Dance move effects
        if self.dance_timer > 0:
            dance_progress = (40 - self.dance_timer) / 40
            
            if self.dance_move == "spin":
                body_rotation = dance_progress * math.pi * 4
            elif self.dance_move == "flip":
                if dance_progress < 0.5:
                    body_height = int(self.height * (1 - dance_progress * 2))
                else:
                    body_height = int(self.height * ((dance_progress - 0.5) * 2))
                body_y = self.y + (self.height - body_height)
            elif self.dance_move == "wave":
                wave_offset = math.sin(dance_progress * math.pi * 6) * 8
                body_y += wave_offset
            elif self.dance_move == "pump":
                pump_scale = 1 + math.sin(dance_progress * math.pi * 8) * 0.3
                body_width = int(self.width * pump_scale)
                body_height = int(self.height * pump_scale)
                body_y = self.y + (self.height - body_height) // 2
            elif self.dance_move == "twist":
                body_width = int(self.width * (1 + math.sin(dance_progress * math.pi * 6) * 0.4))
        
        if self.landing_animation > 0:
            squash_factor = self.landing_animation / 20.0
            body_width = int(body_width * (1 + squash_factor * 0.4))
            body_height = int(body_height * (1 - squash_factor * 0.3))
            body_y = self.y + (self.height - body_height)
        
        # Enhanced robot drawing with gradient effect
        body_rect = pygame.Rect(draw_x - (body_width - self.width)//2, body_y, body_width, body_height)
        
        # Gradient body effect
        if body_rotation == 0:
            # Shadow
            shadow_rect = pygame.Rect(body_rect.x + 3, body_rect.y + 3, body_rect.width, body_rect.height)
            pygame.draw.rect(screen, ROBOT_SHADOW, shadow_rect, border_radius=10)
            
            # Main body
            pygame.draw.rect(screen, ROBOT_ORANGE, body_rect, border_radius=10)
            
            # Highlight gradient
            highlight_rect = pygame.Rect(body_rect.x, body_rect.y, body_rect.width, body_rect.height//3)
            pygame.draw.rect(screen, ROBOT_LIGHT_ORANGE, highlight_rect, border_radius=10)
            
            # Outline
            pygame.draw.rect(screen, ROBOT_DARK_ORANGE, body_rect, 4, border_radius=10)
        else:
            # Rotated body for spin dance
            center_x = draw_x + self.width // 2
            center_y = body_y + body_height // 2
            
            # Create rotated rectangle points
            corners = [
                (-body_width//2, -body_height//2),
                (body_width//2, -body_height//2),
                (body_width//2, body_height//2),
                (-body_width//2, body_height//2)
            ]
            
            rotated_corners = []
            for corner_x, corner_y in corners:
                rot_x = corner_x * math.cos(body_rotation) - corner_y * math.sin(body_rotation)
                rot_y = corner_x * math.sin(body_rotation) + corner_y * math.cos(body_rotation)
                rotated_corners.append((center_x + rot_x, center_y + rot_y))
            
            pygame.draw.polygon(screen, ROBOT_ORANGE, rotated_corners)
            pygame.draw.polygon(screen, ROBOT_DARK_ORANGE, rotated_corners, 4)
        
        # Enhanced eyes with more expressions
        eye_size = 10
        eye_y_offset = 0
        eye_scale = 1.0
        
        if self.jump_animation > 0:
            eye_y_offset = -3
            eye_scale = 1.2
        elif self.landing_animation > 0:
            eye_y_offset = 3
            eye_scale = 0.8
        elif self.hit_animation > 0:
            eye_scale = 1.5
            eye_y_offset = random.randint(-2, 2)
        elif self.dance_timer > 0:
            eye_scale = 1.3
            eye_y_offset = int(math.sin(self.animation_frame * 0.5) * 2)
        
        eye_size = int(eye_size * eye_scale)
        left_eye = (draw_x + 12, body_y + 15 + eye_y_offset)
        right_eye = (draw_x + body_width - 20, body_y + 15 + eye_y_offset)
        
        # Eye whites
        pygame.draw.circle(screen, (255, 255, 255), left_eye, eye_size)
        pygame.draw.circle(screen, (255, 255, 255), right_eye, eye_size)
        
        # Pupils with enhanced movement
        pupil_offset_x = 0
        pupil_offset_y = 0
        
        if abs(self.vel_x) > 8:
            pupil_offset_x = 3
        if self.vel_y < -5:  # Looking up when jumping high
            pupil_offset_y = -2
        elif self.vel_y > 8:  # Looking down when falling fast
            pupil_offset_y = 2
        
        pupil_size = max(2, eye_size // 2)
        pygame.draw.circle(screen, (0, 0, 0), 
                         (left_eye[0] + pupil_offset_x, left_eye[1] + pupil_offset_y), pupil_size)
        pygame.draw.circle(screen, (0, 0, 0), 
                         (right_eye[0] + pupil_offset_x, right_eye[1] + pupil_offset_y), pupil_size)
        
        # Eye shine
        shine_size = max(1, pupil_size // 2)
        pygame.draw.circle(screen, (255, 255, 255), 
                         (left_eye[0] + pupil_offset_x - 1, left_eye[1] + pupil_offset_y - 1), shine_size)
        pygame.draw.circle(screen, (255, 255, 255), 
                         (right_eye[0] + pupil_offset_x - 1, right_eye[1] + pupil_offset_y - 1), shine_size)
        
        # Enhanced running animation
        if self.on_ground and abs(self.vel_x) > 2:
            leg_speed = 0.6 + (self.vel_x / 15)
            leg_offset = math.sin(self.animation_frame * leg_speed) * 12
            leg_y = body_y + body_height
            
            # Enhanced legs with joints
            left_leg_x = draw_x + 10
            right_leg_x = draw_x + body_width - 18
            
            # Left leg
            leg_height = 18 + int(leg_offset)
            pygame.draw.rect(screen, ROBOT_DARK_ORANGE, 
                           (left_leg_x, leg_y, 10, max(8, leg_height)))
            # Knee joint
            pygame.draw.circle(screen, ROBOT_ORANGE, 
                             (left_leg_x + 5, leg_y + leg_height//2), 4)
            # Foot
            pygame.draw.ellipse(screen, ROBOT_SHADOW, 
                              (left_leg_x - 2, leg_y + leg_height, 14, 6))
            
            # Right leg
            leg_height = 18 - int(leg_offset)
            pygame.draw.rect(screen, ROBOT_DARK_ORANGE, 
                           (right_leg_x, leg_y, 10, max(8, leg_height)))
            # Knee joint
            pygame.draw.circle(screen, ROBOT_ORANGE, 
                             (right_leg_x + 5, leg_y + leg_height//2), 4)
            # Foot
            pygame.draw.ellipse(screen, ROBOT_SHADOW, 
                              (right_leg_x - 2, leg_y + leg_height, 14, 6))
            
            # Running dust particles
            if self.vel_x > 10 and self.animation_frame % 6 == 0:
                dust_particles = []
                for i in range(3):
                    dust_x = draw_x + random.randint(-5, 5)
                    dust_y = leg_y + 20 + random.randint(-3, 3)
                    pygame.draw.circle(screen, (120, 120, 120), (dust_x, dust_y), 
                                     random.randint(1, 3))
        
        # Enhanced jump animation with better trail
        if self.jump_animation > 0:
            trail_length = min(self.jump_animation, 12)
            for i in range(trail_length):
                alpha = (trail_length - i) / trail_length
                trail_alpha = int(alpha * 150)
                trail_color = (*ROBOT_LIGHT_ORANGE[:3], trail_alpha)
                trail_x = draw_x - self.vel_x * i * 0.8
                trail_y = body_y + i * 8
                trail_width = int(body_width * alpha)
                trail_height = int(body_height * alpha)
                
                if trail_width > 5 and trail_height > 5:
                    trail_rect = pygame.Rect(trail_x, trail_y, trail_width, trail_height)
                    pygame.draw.rect(screen, ROBOT_LIGHT_ORANGE, trail_rect, border_radius=5)
        
        # Enhanced hit animation with screen shake effect
        if self.hit_animation > 0:
            shake_intensity = self.hit_animation // 3
            for i in range(25):
                sparkle_x = draw_x + random.randint(-30, body_width + 30)
                sparkle_y = body_y + random.randint(-20, body_height + 20)
                sparkle_size = random.randint(2, 8)
                sparkle_color = random.choice([(255, 255, 255), (255, 200, 100), (255, 100, 100)])
                pygame.draw.circle(screen, sparkle_color, (sparkle_x, sparkle_y), sparkle_size)
        
        # Enhanced speed boost trails
        if self.speed_boost > 4:
            trail_count = int(self.speed_boost // 2)
            for i in range(trail_count):
                trail_x = draw_x - 35 - i*12
                trail_y = body_y + body_height//2 + math.sin(self.animation_frame * 0.6 + i) * 8
                trail_size = max(2, 6 - i)
                trail_color = [*ROBOT_HIGHLIGHT]
                trail_color[0] = max(100, trail_color[0] - i * 30)
                pygame.draw.circle(screen, trail_color, (int(trail_x), int(trail_y)), trail_size)
        
        # Invulnerability flashing effect
        if self.invulnerable_timer > 0 and self.invulnerable_timer % 8 < 4:
            overlay = pygame.Surface((body_width + 10, body_height + 10))
            overlay.set_alpha(100)
            overlay.fill((255, 100, 100))
            screen.blit(overlay, (draw_x - 5, body_y - 5))
        
        # Lives indicator hearts (only when damaged)
        if self.lives < 3:
            for i in range(3):
                heart_x = draw_x + i * 15 - 20
                heart_y = body_y - 25
                if i < self.lives:
                    pygame.draw.circle(screen, (255, 100, 100), (heart_x, heart_y), 6)
                    pygame.draw.circle(screen, (255, 0, 0), (heart_x, heart_y), 4)
                else:
                    pygame.draw.circle(screen, (100, 100, 100), (heart_x, heart_y), 6)
                    pygame.draw.circle(screen, (60, 60, 60), (heart_x, heart_y), 4)

class Platform:
    def __init__(self, x, y, width, height, special=False, bounce=False, moving=False):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.special = special
        self.bounce = bounce
        self.moving = moving
        self.hit_animation = 0
        self.glow_animation = 0
        self.move_speed = random.uniform(1, 3) if moving else 0
        self.move_direction = random.choice([-1, 1]) if moving else 0
        self.original_y = y
        self.move_range = random.randint(50, 100)
        
    def hit(self):
        self.hit_animation = 20
        self.glow_animation = 40
        
    def update(self):
        if self.hit_animation > 0:
            self.hit_animation -= 1
        if self.glow_animation > 0:
            self.glow_animation -= 1
            
        # Moving platform logic
        if self.moving:
            self.y += self.move_speed * self.move_direction
            if abs(self.y - self.original_y) > self.move_range:
                self.move_direction *= -1
    
    def draw(self, screen, camera_x):
        draw_x = self.x - camera_x
        
        if draw_x + self.width > 0 and draw_x < WIDTH:
            # Platform color selection
            if self.moving:
                color = MOVING_PLATFORM_COLOR
            elif self.bounce:
                color = BOUNCE_PLATFORM_COLOR
            elif self.special:
                color = SPECIAL_PLATFORM_COLOR
            else:
                color = PLATFORM_COLOR
            
            # Hit animation effect
            if self.hit_animation > 0:
                hit_intensity = self.hit_animation * 3
                color = tuple(min(255, c + hit_intensity) for c in color)
            
            # Enhanced glow effect
            if self.glow_animation > 0:
                glow_intensity = self.glow_animation // 8
                for i in range(glow_intensity):
                    glow_size = i * 3
                    glow_rect = pygame.Rect(draw_x - glow_size, self.y - glow_size, 
                                          self.width + glow_size*2, self.height + glow_size*2)
                    glow_color = tuple(min(255, c + 50 - i*10) for c in color)
                    pygame.draw.rect(screen, glow_color, glow_rect, border_radius=5)
            
            # Main platform with 3D effect
            platform_rect = pygame.Rect(draw_x, self.y, self.width, self.height)
            
            # Shadow
            shadow_rect = pygame.Rect(draw_x + 3, self.y + 3, self.width, self.height)
            pygame.draw.rect(screen, tuple(c//2 for c in color), shadow_rect, border_radius=5)
            
            # Main platform
            pygame.draw.rect(screen, color, platform_rect, border_radius=5)
            
            # Highlight
            highlight_rect = pygame.Rect(draw_x, self.y, self.width, self.height//3)
            highlight_color = tuple(min(255, c + 40) for c in color)
            pygame.draw.rect(screen, highlight_color, highlight_rect, border_radius=5)
            
            # Outline
            pygame.draw.rect(screen, (220, 220, 220), platform_rect, 3, border_radius=5)
            
            # Special platform indicators
            if self.special:
                # Animated energy cores
                for i in range(4):
                    core_x = draw_x + (i + 1) * self.width // 5
                    core_y = self.y + self.height // 2
                    pulse = math.sin(pygame.time.get_ticks() * 0.01 + i) * 0.4 + 0.8
                    core_size = int(5 * pulse)
                    
                    pygame.draw.circle(screen, (255, 255, 255), (core_x, core_y), core_size + 2)
                    pygame.draw.circle(screen, SPECIAL_PLATFORM_COLOR, (core_x, core_y), core_size)
            
            if self.bounce:
                # Enhanced bounce indicator with animation
                bounce_offset = math.sin(pygame.time.get_ticks() * 0.03) * 4
                bounce_y = self.y + 8 + bounce_offset
                
                # Multiple bounce arrows
                for i in range(3):
                    arrow_y = bounce_y + i * 6
                    arrow_alpha = 255 - i * 60
                    arrow_size = 8 - i * 2
                    
                    pygame.draw.polygon(screen, (*BOUNCE_PLATFORM_COLOR, arrow_alpha), [
                        (draw_x + self.width//2, arrow_y),
                        (draw_x + self.width//2 - arrow_size, arrow_y + arrow_size),
                        (draw_x + self.width//2 + arrow_size, arrow_y + arrow_size)
                    ])
            
            if self.moving:
                # Movement indicator
                move_indicator_y = self.y + self.height + 5
                indicator_width = max(10, int(self.width * 0.3))
                
                # Direction arrows
                if self.move_direction > 0:
                    # Down arrow
                    pygame.draw.polygon(screen, MOVING_PLATFORM_COLOR, [
                        (draw_x + self.width//2, move_indicator_y + 8),
                        (draw_x + self.width//2 - 6, move_indicator_y),
                        (draw_x + self.width//2 + 6, move_indicator_y)
                    ])
                else:
                    # Up arrow
                    pygame.draw.polygon(screen, MOVING_PLATFORM_COLOR, [
                        (draw_x + self.width//2, move_indicator_y),
                        (draw_x + self.width//2 - 6, move_indicator_y + 8),
                        (draw_x + self.width//2 + 6, move_indicator_y + 8)
                    ])

class PlatformGenerator:
    def __init__(self):
        self.platforms = []
        self.coins = []
        self.enemies = []
        self.last_platform_x = 0
        self.generate_initial_platforms()
    
    def generate_initial_platforms(self):
        # Starting platform
        self.platforms.append(Platform(0, HEIGHT - 60, 250, 160))
        self.last_platform_x = 250
        
        # Generate ahead
        for _ in range(30):
            self.generate_next_platform()
    
    def generate_next_platform(self):
        gap = random.randint(70, 220)
        width = random.randint(90, 180)
        height = random.randint(12, 60)
        y = random.randint(HEIGHT - 550, HEIGHT - 150)
        
        # Enhanced platform type distribution
        platform_type = random.random()
        if platform_type < 0.15:
            special = True
            bounce = False
            moving = False
        elif platform_type < 0.25:
            special = False
            bounce = True
            moving = False
        elif platform_type < 0.35:
            special = False
            bounce = False
            moving = True
        else:
            special = False
            bounce = False
            moving = False
        
        platform = Platform(self.last_platform_x + gap, y, width, height, special, bounce, moving)
        self.platforms.append(platform)
        
        # Enhanced coin generation
        coin_chance = random.random()
        if coin_chance < 0.7:  # 70% chance for coins
            coin_count = random.randint(1, 4)
            for i in range(coin_count):
                coin_x = platform.x + random.randint(10, platform.width - 10)
                coin_y = platform.y - random.randint(45, 120)
                coin_type = "super" if random.random() < 0.2 else "normal"
                self.coins.append(Coin(coin_x, coin_y, coin_type))
        
        # Floating coins in gaps
        if random.random() < 0.4:
            floating_coin_count = random.randint(1, 3)
            for i in range(floating_coin_count):
                coin_x = self.last_platform_x + gap // 3 + i * (gap // 3)
                coin_y = random.randint(HEIGHT - 450, HEIGHT - 200)
                coin_type = "super" if random.random() < 0.15 else "normal"
                self.coins.append(Coin(coin_x, coin_y, coin_type))
        
        # Enemy generation
        enemy_chance = random.random()
        if enemy_chance < 0.3 and self.last_platform_x > 500:  # 30% chance after initial area
            enemy_type = random.choice(["spiker", "floater", "bouncer"])
            if enemy_type == "floater":
                enemy_x = platform.x + random.randint(0, platform.width)
                enemy_y = platform.y - random.randint(80, 150)
            else:
                enemy_x = platform.x + random.randint(10, platform.width - 40)
                enemy_y = platform.y - 35
            
            self.enemies.append(Enemy(enemy_x, enemy_y, enemy_type))
        
        self.last_platform_x = platform.x + platform.width
    
    def update(self, camera_x):
        # Remove old objects
        self.platforms = [p for p in self.platforms if p.x + p.width > camera_x - 300]
        self.coins = [c for c in self.coins if c.x > camera_x - 300]
        self.enemies = [e for e in self.enemies if e.x > camera_x - 300]
        
        # Generate new platforms
        while self.last_platform_x < camera_x + WIDTH * 2.5:
            self.generate_next_platform()
        
        # Update existing objects
        for platform in self.platforms:
            platform.update()
        for coin in self.coins:
            coin.update()
        
        # Update enemies
        active_enemies = []
        for enemy in self.enemies:
            if enemy.update(self.platforms):
                active_enemies.append(enemy)
        self.enemies = active_enemies
    
    def get_platforms(self):
        return self.platforms
    
    def get_coins(self):
        return self.coins
    
    def get_enemies(self):
        return self.enemies

# Enhanced audio processing functions (keeping the existing ones but with improvements)
def extract_audio_with_ffmpeg(video_path):
    """Extract audio from video using ffmpeg with better error handling"""
    print("Extracting audio from video...")
    
    temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    temp_wav.close()
    
    try:
        # Primary extraction command
        cmd = [
            'ffmpeg', '-i', video_path, 
            '-vn', '-acodec', 'pcm_s16le', 
            '-ar', '44100', '-ac', '1', 
            '-y', temp_wav.name
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"FFmpeg primary command failed: {result.stderr}")
            # Fallback command
            cmd = ['ffmpeg', '-i', video_path, '-vn', '-ar', '22050', '-y', temp_wav.name]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"FFmpeg fallback failed: {result.stderr}")
                raise Exception("Both FFmpeg commands failed")
        
        # Read the WAV file
        with wave.open(temp_wav.name, 'rb') as wav_file:
            frames = wav_file.getnframes()
            sample_rate = wav_file.getframerate()
            duration = frames / sample_rate
            
            raw_audio = wav_file.readframes(frames)
            audio_data = np.frombuffer(raw_audio, dtype=np.int16).astype(np.float32)
            audio_data = audio_data / 32768.0  # Normalize
        
        print(f"Successfully extracted {duration:.2f}s of audio at {sample_rate}Hz")
        return audio_data, sample_rate, duration
    
    except Exception as e:
        print(f"Audio extraction error: {e}")
        print("Generating synthetic audio data...")
        # Return synthetic data
        sample_rate = 22050
        duration = get_video_duration(video_path)
        audio_data = np.random.random(int(sample_rate * duration)) * 0.1
        return audio_data, sample_rate, duration
    
    finally:
        if os.path.exists(temp_wav.name):
            os.unlink(temp_wav.name)

def get_video_duration(video_path):
    """Get video duration using ffprobe with better error handling"""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-show_entries', 
            'format=duration', '-of', 'csv=p=0', video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except Exception as e:
        print(f"Duration detection failed: {e}")
    
    # Fallback: try to get frame count and fps
    try:
        cmd = ['ffprobe', '-v', 'quiet', '-select_streams', 'v:0', 
               '-show_entries', 'stream=nb_frames,r_frame_rate', '-of', 'csv=p=0', video_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                parts = line.split(',')
                if len(parts) >= 2:
                    try:
                        frames = int(parts[0])
                        fps_str = parts[1]
                        if '/' in fps_str:
                            num, den = fps_str.split('/')
                            fps = float(num) / float(den)
                        else:
                            fps = float(fps_str)
                        return frames / fps
                    except:
                        continue
    except Exception as e:
        print(f"Frame-based duration detection failed: {e}")
    
    return 15.0  # Conservative fallback

def extract_audio_features(video_path):
    """Enhanced audio feature extraction with better beat detection"""
    
    duration = get_video_duration(video_path)
    print(f"Video duration: {duration:.2f}s")
    
    try:
        audio_data, sample_rate, audio_duration = extract_audio_with_ffmpeg(video_path)
        duration = min(duration, audio_duration)
    except Exception as e:
        print(f"Audio processing failed: {e}")
        return generate_synthetic_features(duration)
    
    # Enhanced audio processing
    chunk_size = max(1, sample_rate // FPS)
    energy_values = []
    spectral_values = []
    tempo_values = []
    
    # Process audio in overlapping windows for smoother features
    window_size = chunk_size * 2
    hop_size = chunk_size
    
    for i in range(0, len(audio_data) - window_size, hop_size):
        window = audio_data[i:i+window_size]
        
        # Energy features
        rms_energy = np.sqrt(np.mean(window**2))
        energy_values.append(rms_energy)
        
        # Spectral features
        if len(window) > 1:
            # High frequency content (brightness)
            spectral_centroid = np.mean(np.abs(np.diff(window)))
            spectral_values.append(spectral_centroid)
            
            # Tempo-related features (flux)
            if i > hop_size:
                prev_window = audio_data[i-hop_size:i-hop_size+window_size]
                spectral_flux = np.mean((np.abs(np.fft.fft(window)) - 
                                       np.abs(np.fft.fft(prev_window)))**2)
                tempo_values.append(spectral_flux)
            else:
                tempo_values.append(0)
        else:
            spectral_values.append(0)
            tempo_values.append(0)
    
    # Normalize features
    if energy_values:
        max_energy = max(energy_values)
        if max_energy > 0:
            energy_values = [e / max_energy for e in energy_values]
    
    if spectral_values:
        max_spectral = max(spectral_values)
        if max_spectral > 0:
            spectral_values = [s / max_spectral for s in spectral_values]
    
    if tempo_values:
        max_tempo = max(tempo_values)
        if max_tempo > 0:
            tempo_values = [t / max_tempo for t in tempo_values]
    
    # Enhanced beat detection using multiple criteria
    beats = detect_beats_enhanced(energy_values, spectral_values, tempo_values)
    
    print(f"Detected {len(beats)} beats in {len(energy_values)} frames")
    return energy_values, beats, duration

def detect_beats_enhanced(energy_values, spectral_values, tempo_values):
    """Enhanced beat detection using multiple audio features"""
    beats = []
    
    if len(energy_values) < 10:
        return beats
    
    # Adaptive thresholding
    energy_threshold = np.mean(energy_values) + 0.5 * np.std(energy_values)
    spectral_threshold = np.mean(spectral_values) + 0.3 * np.std(spectral_values) if spectral_values else 0
    tempo_threshold = np.mean(tempo_values) + 0.4 * np.std(tempo_values) if tempo_values else 0
    
    min_beat_gap = 6  # Minimum frames between beats
    beat_confirmation_window = 3
    
    for i in range(beat_confirmation_window, len(energy_values) - beat_confirmation_window):
        # Multi-criteria beat detection
        energy_peak = (energy_values[i] > energy_threshold and 
                      energy_values[i] > energy_values[i-1] and 
                      energy_values[i] > energy_values[i+1])
        
        spectral_peak = (spectral_values and i < len(spectral_values) and
                        spectral_values[i] > spectral_threshold)
        
        tempo_peak = (tempo_values and i < len(tempo_values) and
                     tempo_values[i] > tempo_threshold)
        
        # Require at least energy peak + one other criterion
        is_beat = energy_peak and (spectral_peak or tempo_peak)
        
        # Additional confirmation: check if it's a local maximum
        if is_beat:
            local_max = all(energy_values[i] >= energy_values[j] 
                           for j in range(max(0, i-beat_confirmation_window), 
                                        min(len(energy_values), i+beat_confirmation_window+1)))
            
            if local_max and (not beats or i - beats[-1] >= min_beat_gap):
                # Final check: significant energy increase
                if i > 0 and energy_values[i] > energy_values[i-1] * 1.2:
                    beats.append(i)
    
    return beats

def generate_synthetic_features(duration):
    """Generate synthetic audio features when extraction fails"""
    print("Generating synthetic audio features...")
    total_frames = int(duration * FPS)
    energy_values = []
    beats = []
    
    # Create more musical synthetic patterns
    base_tempo = random.uniform(0.4, 0.8)  # Base beat frequency
    
    for i in range(total_frames):
        t = i / FPS
        
        # Multi-layered energy pattern
        bass_energy = 0.6 * math.sin(t * base_tempo * 2 * math.pi)
        mid_energy = 0.3 * math.sin(t * base_tempo * 4 * math.pi + math.pi/3)
        high_energy = 0.2 * math.sin(t * base_tempo * 8 * math.pi + math.pi/2)
        noise = 0.1 * random.random()
        
        energy = max(0, min(1, 0.4 + bass_energy + mid_energy + high_energy + noise))
        energy_values.append(energy)
        
        # Generate beats with musical timing
        beat_probability = base_tempo * 0.3
        if random.random() < beat_probability and (not beats or i - beats[-1] >= 8):
            beats.append(i)
        
        # Add occasional strong beats
        if i % int(FPS / base_tempo) == 0 and random.random() > 0.4:
            beats.append(i)
    
    return energy_values, beats, duration

def main(input_video_path, output_path):
    # Extract enhanced audio features
    energy_values, beats, duration = extract_audio_features(input_video_path)
    total_frames = int(duration * FPS)
    
    print(f"Processing {total_frames} frames with {len(beats)} beat markers...")
    
    # Initialize enhanced game objects
    robot = Robot(50, HEIGHT - 350)
    platform_generator = PlatformGenerator()
    particles = []
    
    # Enhanced camera system
    camera_x = 0
    camera_shake_x = 0
    camera_shake_intensity = 0
    
    # Video writer setup with better quality
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, FPS, (WIDTH, HEIGHT))
    
    # Create pygame surface
    screen = pygame.Surface((WIDTH, HEIGHT))
    
    # Performance tracking
    frames_processed = 0
    life_reset = 0
    for frame in range(total_frames):
        # Get enhanced audio features
        audio_energy = 0
        beat_detected = False
        beat_strength = 0
        
        if frame < len(energy_values):
            audio_energy = energy_values[frame]
            if frame in beats:
                beat_detected = True
                # Calculate beat strength based on surrounding energy
                beat_strength = audio_energy
                if frame > 0:
                    beat_strength += (audio_energy - energy_values[frame-1])
                beat_strength = max(0, min(1, beat_strength))
        
        # Enhanced camera shake
        if beat_detected and beat_strength > 0.6:
            camera_shake_intensity = int(beat_strength * 12)
            camera_shake_x = random.randint(-camera_shake_intensity, camera_shake_intensity)
        else:
            camera_shake_x *= 0.8
            if abs(camera_shake_x) < 1:
                camera_shake_x = 0
        
        # Enhanced camera following with prediction
        robot_velocity_prediction = robot.x + robot.vel_x * 10
        target_camera_x = robot_velocity_prediction - WIDTH // 3 + camera_shake_x
        
        # Smoother camera with different speeds for different situations
        if beat_detected and beat_strength > 0.7:
            # Quick camera adjustment on strong beats
            camera_x += (target_camera_x - camera_x) * 0.25
        else:
            # Normal smooth following
            camera_x += (target_camera_x - camera_x) * 0.12
        
        # Update game objects with enhanced parameters
        robot.update(platform_generator.get_platforms(), 
                    platform_generator.get_coins(),
                    particles, 
                    platform_generator.get_enemies(),
                    audio_energy, 
                    beat_detected, 
                    frame)
        
        platform_generator.update(camera_x)
        
        # Update particles with better cleanup
        particles = [p for p in particles if p.update()]
        
        # Add ambient particles on strong beats
        if beat_detected and beat_strength > 0.5:
            for i in range(int(beat_strength * 15)):
                particles.append(Particle(
                    camera_x + random.randint(0, WIDTH),
                    random.randint(HEIGHT//4, HEIGHT),
                    random.randint(-2, 2),
                    random.randint(-5, -1),
                    random.choice(PARTICLE_COLORS),
                    random.randint(30, 60),
                    "spark"
                ))
        
        # Enhanced background rendering
        screen.fill(BACKGROUND_COLOR)
        
        # Dynamic background with music response
        pulse_strength = int(audio_energy * 30)
        beat_flash = int(beat_strength * 40) if beat_detected else 0
        
        background_base = tuple(min(255, c + pulse_strength + beat_flash) for c in BACKGROUND_COLOR)
        screen.fill(background_base)
        
        # Gradient background layers
        gradient_layers = HEIGHT // 6
        for i in range(gradient_layers):
            layer_alpha = i / gradient_layers
            layer_pulse = int(audio_energy * 15 * layer_alpha)
            
            color = (
                min(255, int(BACKGROUND_COLOR[0] + layer_alpha * 25 + layer_pulse)),
                min(255, int(BACKGROUND_COLOR[1] + layer_alpha * 25 + layer_pulse)),
                min(255, int(BACKGROUND_COLOR[2] + layer_alpha * 45 + layer_pulse))
            )
            
            pygame.draw.rect(screen, color, (0, i * 6, WIDTH, 6))
        
        # Beat flash effect
        if beat_detected and beat_strength > 0.8:
            flash_overlay = pygame.Surface((WIDTH, HEIGHT))
            flash_overlay.set_alpha(int(beat_strength * 30))
            flash_overlay.fill((255, 255, 255))
            screen.blit(flash_overlay, (0, 0))
        
        # Draw game objects in proper order
        
        # Draw platforms
        for platform in platform_generator.get_platforms():
            platform.draw(screen, camera_x)
        
        # Draw coins
        for coin in platform_generator.get_coins():
            coin.draw(screen, camera_x)
        
        # Draw enemies
        for enemy in platform_generator.get_enemies():
            enemy.draw(screen, camera_x)
        
        # Draw particles (behind robot for some, in front for others)
        background_particles = [p for p in particles if p.particle_type != "spark"]
        foreground_particles = [p for p in particles if p.particle_type == "spark"]
        
        for particle in background_particles:
            particle.draw(screen, camera_x)
        
        # Draw robot
        robot.draw(screen, camera_x)
        
        # Draw foreground particles
        for particle in foreground_particles:
            particle.draw(screen, camera_x)
        
        # Enhanced UI with better styling
        try:
            font_large = pygame.font.Font(None, 32)
            font_medium = pygame.font.Font(None, 24)
            font_small = pygame.font.Font(None, 20)
        except:
            font_large = pygame.font.SysFont('Arial', 28, bold=True)
            font_medium = pygame.font.SysFont('Arial', 20, bold=True)
            font_small = pygame.font.SysFont('Arial', 16)
        
        # UI Background panel
        ui_panel = pygame.Surface((280, 120))
        ui_panel.set_alpha(180)
        ui_panel.fill((0, 0, 0))
        screen.blit(ui_panel, (10, 10))
        
        # Coins collected with icon
        pygame.draw.circle(screen, COIN_GOLD, (25, 25), 8)
        pygame.draw.circle(screen, COIN_YELLOW, (25, 25), 6)
        coin_text = font_medium.render(f": {robot.coins_collected}", True, COIN_GOLD)
        screen.blit(coin_text, (40, 18))
        
        # Super coins
        if robot.super_coins_collected > 0:
            pygame.draw.circle(screen, COIN_GOLD, (25, 45), 10)
            pygame.draw.circle(screen, (255, 255, 255), (25, 45), 8)
            pygame.draw.circle(screen, COIN_GOLD, (25, 45), 6)
            super_coin_text = font_small.render(f": {robot.super_coins_collected}", True, (255, 255, 255))
            screen.blit(super_coin_text, (40, 40))
        
        # Combo multiplier with glow effect
        if robot.combo_multiplier > 1.2:
            combo_glow = int((robot.combo_multiplier - 1) * 100)
            combo_color = (255, min(255, 200 + combo_glow), min(255, 100 + combo_glow))
            combo_text = font_medium.render(f"COMBO: {robot.combo_multiplier:.1f}x", True, combo_color)
            
            # Glow effect for high combos
            if robot.combo_multiplier > 2.0:
                glow_surface = font_medium.render(f"COMBO: {robot.combo_multiplier:.1f}x", True, (255, 255, 255))
                glow_surface.set_alpha(100)
                screen.blit(glow_surface, (12, 62))
                screen.blit(glow_surface, (8, 62))
                screen.blit(glow_surface, (10, 60))
                screen.blit(glow_surface, (10, 64))
            
            screen.blit(combo_text, (10, 62))
        
        # Speed boost indicator with motion blur effect
        if robot.speed_boost > 2:
            speed_intensity = min(255, int(robot.speed_boost * 25))
            speed_color = (255, speed_intensity, 0)
            speed_text = font_medium.render("SPEED BOOST!", True, speed_color)
            
            # Motion blur effect
            for offset in range(3):
                blur_alpha = 100 - offset * 30
                blur_surface = font_medium.render("SPEED BOOST!", True, speed_color)
                blur_surface.set_alpha(blur_alpha)
                screen.blit(blur_surface, (10 + offset * 2, 85))
            
            screen.blit(speed_text, (10, 85))
        
        # Lives indicator (enhanced hearts)
        if robot.lives < 3:
            for i in range(3):
                heart_x = WIDTH - 120 + i * 25
                heart_y = 25
                
                if i < robot.lives:
                    # Alive heart
                    pygame.draw.circle(screen, (255, 50, 50), (heart_x - 3, heart_y - 2), 8)
                    pygame.draw.circle(screen, (255, 50, 50), (heart_x + 3, heart_y - 2), 8)
                    pygame.draw.polygon(screen, (255, 50, 50), [
                        (heart_x - 8, heart_y + 2),
                        (heart_x, heart_y + 12),
                        (heart_x + 8, heart_y + 2)
                    ])
                    # Shine
                    pygame.draw.circle(screen, (255, 150, 150), (heart_x - 2, heart_y - 1), 3)
                else:
                    # Empty heart
                    pygame.draw.circle(screen, (100, 100, 100), (heart_x - 3, heart_y - 2), 8, 2)
                    pygame.draw.circle(screen, (100, 100, 100), (heart_x + 3, heart_y - 2), 8, 2)
                    pygame.draw.polygon(screen, (100, 100, 100), [
                        (heart_x - 8, heart_y + 2),
                        (heart_x, heart_y + 12),
                        (heart_x + 8, heart_y + 2)
                    ], 2)
        
        # Audio visualization (enhanced)
        if audio_energy > 0:
            # Energy bar
            bar_width = int(audio_energy * 120)
            bar_height = 8
            bar_x = WIDTH - 140
            bar_y = 50
            
            # Background
            pygame.draw.rect(screen, (50, 50, 50), (bar_x, bar_y, 120, bar_height), border_radius=4)
            
            # Energy level with color coding
            if audio_energy > 0.8:
                bar_color = (255, 100, 100)  # Red for high energy
            elif audio_energy > 0.5:
                bar_color = (255, 200, 100)  # Orange for medium energy
            else:
                bar_color = (100, 255, 100)  # Green for low energy
            
            pygame.draw.rect(screen, bar_color, (bar_x, bar_y, bar_width, bar_height), border_radius=4)
            
            # Energy text
            energy_text = font_small.render("ENERGY", True, (200, 200, 200))
            screen.blit(energy_text, (bar_x, bar_y - 15))
        
        # Beat indicator (enhanced)
        if beat_detected:
            beat_size = int(15 + beat_strength * 20)
            beat_alpha = int(beat_strength * 255)
            
            # Pulsing beat indicator
            pygame.draw.circle(screen, (255, 255, 255), (WIDTH - 30, 80), beat_size + 3)
            pygame.draw.circle(screen, (255, 0, 0), (WIDTH - 30, 80), beat_size)
            pygame.draw.circle(screen, (255, 255, 255), (WIDTH - 30, 80), beat_size - 5)
            
            # Beat ripples
            for ripple in range(3):
                ripple_size = beat_size + ripple * 8
                ripple_alpha = max(0, beat_alpha - ripple * 80)
                if ripple_alpha > 0:
                    ripple_surface = pygame.Surface((ripple_size * 2, ripple_size * 2))
                    ripple_surface.set_alpha(ripple_alpha)
                    pygame.draw.circle(ripple_surface, (255, 255, 255), 
                                     (ripple_size, ripple_size), ripple_size, 3)
                    screen.blit(ripple_surface, (WIDTH - 30 - ripple_size, 80 - ripple_size))
        
        # Performance indicator (frame counter for debugging)
        if frame % 60 == 0:  # Update every second
            fps_text = font_small.render(f"Frame: {frame}", True, (150, 150, 150))
            screen.blit(fps_text, (10, HEIGHT - 25))
        
        # Game over screen
        if robot.lives <= 0:
            life_reset += 1
            if life_reset >= 200:
                life_reset = 0
                robot.lives = 3
            game_over_overlay = pygame.Surface((WIDTH, HEIGHT))
            game_over_overlay.set_alpha(200)
            game_over_overlay.fill((0, 0, 0))
            screen.blit(game_over_overlay, (0, 0))
            
            game_over_text = font_large.render("GAME OVER", True, (255, 100, 100))
            game_over_rect = game_over_text.get_rect(center=(WIDTH//2, HEIGHT//2 - 50))
            screen.blit(game_over_text, game_over_rect)
            
            final_score_text = font_medium.render(f"Final Score: {robot.coins_collected + robot.super_coins_collected * 5}", 
                                                True, (255, 255, 255))
            score_rect = final_score_text.get_rect(center=(WIDTH//2, HEIGHT//2))
            screen.blit(final_score_text, score_rect)
            
            max_combo_text = font_medium.render(f"Max Combo: {robot.combo_multiplier:.1f}x", 
                                              True, (255, 255, 255))
            combo_rect = max_combo_text.get_rect(center=(WIDTH//2, HEIGHT//2 + 30))
            screen.blit(max_combo_text, combo_rect)
        
        # Convert pygame surface to opencv format
        frame_array = pygame.surfarray.array3d(screen)
        frame_array = np.transpose(frame_array, (1, 0, 2))
        frame_array = cv2.cvtColor(frame_array, cv2.COLOR_RGB2BGR)
        
        # Write frame
        out.write(frame_array)
        
        frames_processed += 1
        
        # Progress indicator with ETA
        if frame % (FPS * 2) == 0:  # Every 2 seconds
            progress_percent = (frame / total_frames) * 100
            if frame > 0:
                time_per_frame = frame / max(1, frames_processed)
                eta_seconds = (total_frames - frame) * time_per_frame / FPS
                eta_minutes = int(eta_seconds // 60)
                eta_seconds = int(eta_seconds % 60)
                print(f"Progress: {frame}/{total_frames} frames ({progress_percent:.1f}%) - "
                      f"ETA: {eta_minutes:02d}:{eta_seconds:02d}")
            else:
                print(f"Progress: {frame}/{total_frames} frames ({progress_percent:.1f}%)")
    
    # Cleanup and final statistics
    out.release()
    pygame.quit()
    
    print(f"\n🎬 Animation saved to {output_path}")
    print(f"📊 Final Statistics:")
    print(f"   • Coins collected: {robot.coins_collected}")
    print(f"   • Super coins: {robot.super_coins_collected}")
    print(f"   • Max combo: {robot.combo_multiplier:.1f}x")
    print(f"   • Final lives: {robot.lives}")
    print(f"   • Total beats detected: {len(beats)}")
    print(f"   • Video duration: {duration:.2f}s")
    print(f"   • Total frames: {total_frames}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 3:
        print("🎵 Enhanced Music Platformer Visualizer")
        print("Usage: python enhanced_platformer.py <input_video.mp4> <output_animation.mp4>")
        print("\nFeatures:")
        print("  • Enhanced graphics with particle effects")
        print("  • Music-synced robot dance moves")
        print("  • Multiple enemy types to avoid")
        print("  • Super coins and combo system")
        print("  • Dynamic camera with beat-synced shake")
        print("  • Lives system with invulnerability")
        print("  • Moving and special platforms")
        sys.exit(1)
    
    input_video = sys.argv[1]
    output_video = sys.argv[2]
    
    if not os.path.exists(input_video):
        print(f"❌ Error: Input video '{input_video}' not found")
        sys.exit(1)
    
    print(f"🎵 Starting enhanced music platformer visualization...")
    print(f"📁 Input: {input_video}")
    print(f"💾 Output: {output_video}")
    
    main(input_video, output_video)