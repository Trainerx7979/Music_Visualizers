import cv2
import numpy as np
import librosa
import pygame
import math
import argparse
from pathlib import Path

class MusicRobot:
    def __init__(self, size=(200, 200)):
        self.size = size
        self.width, self.height = size
        
        # Robot parameters
        self.base_body_size = 60
        self.base_head_size = 40
        self.base_eye_size = 8
        self.base_antenna_height = 15
        
        # Animation state
        self.bounce_offset = 0
        self.eye_blink = 0
        self.antenna_sway = 0
        self.body_pulse = 1.0
        self.arm_angle_left = 0
        self.arm_angle_right = 0
        self.arm_length_multiplier = 1.0
        self.beat_blink_timer = 0
        
    def update(self, beat_strength, spectral_centroid, tempo_factor, rms_energy):
        """Update robot animation based on music features"""
        # Bounce based on beat strength
        self.bounce_offset = beat_strength * 20
        
        # Body pulse based on overall energy
        self.body_pulse = 1.0 + (beat_strength * 0.3)
        
        # Antenna sway based on spectral centroid (frequency content)
        self.antenna_sway = (spectral_centroid - 0.5) * 30
        
        # Arms are highly reactive to music
        # Left arm responds to beat strength and energy
        self.arm_angle_left += (beat_strength * 2.0 + rms_energy * 1.5) * 0.3
        
        # Right arm responds to spectral content and tempo
        self.arm_angle_right += (spectral_centroid * 1.5 + tempo_factor * 0.5) * 0.4
        
        # Arm length varies with energy
        self.arm_length_multiplier = 1.0 + (rms_energy * 0.4) + (beat_strength * 0.3)
        
        # Eye blinking - occasional random blinks
        self.eye_blink = max(0, self.eye_blink - 0.15)
        
        # Beat-synchronized blinking (more likely on strong beats)
        self.beat_blink_timer = max(0, self.beat_blink_timer - 1)
        if beat_strength > 0.7 and self.beat_blink_timer <= 0:
            self.eye_blink = 1.0
            self.beat_blink_timer = 15  # Prevent rapid blinking
        elif np.random.random() < 0.015:  # Occasional random blinks
            self.eye_blink = 1.0
    
    def draw(self, surface):
        """Draw the robot on a pygame surface"""
        surface.fill((0, 0, 0))  # Black background
        
        center_x, center_y = self.width // 2, self.height // 2
        
        # Apply bounce
        robot_y = center_y - int(self.bounce_offset)
        
        # Body (main rectangle)
        body_size = int(self.base_body_size * self.body_pulse)
        body_rect = pygame.Rect(
            center_x - body_size // 2,
            robot_y - body_size // 4,
            body_size,
            body_size
        )
        pygame.draw.rect(surface, (255, 100, 0), body_rect, border_radius=10)  # Orange
        pygame.draw.rect(surface, (255, 165, 0), body_rect, 3, border_radius=10)  # Orange border
        
        # Head (circle)
        head_size = int(self.base_head_size * self.body_pulse)
        head_pos = (center_x, robot_y - body_size // 2 - head_size // 2)
        pygame.draw.circle(surface, (255, 100, 0), head_pos, head_size)
        pygame.draw.circle(surface, (255, 165, 0), head_pos, head_size, 3)
        
        # Eyes - blink occasionally and with beats
        eye_size = int(self.base_eye_size * (1 - self.eye_blink * 0.9))
        left_eye = (center_x - 12, robot_y - body_size // 2 - head_size // 2 - 5)
        right_eye = (center_x + 12, robot_y - body_size // 2 - head_size // 2 - 5)
        
        if eye_size > 1:
            pygame.draw.circle(surface, (255, 255, 255), left_eye, eye_size)
            pygame.draw.circle(surface, (255, 255, 255), right_eye, eye_size)
            pygame.draw.circle(surface, (0, 0, 0), left_eye, eye_size // 2)
            pygame.draw.circle(surface, (0, 0, 0), right_eye, eye_size // 2)
        
        # Antennae
        antenna_height = self.base_antenna_height
        antenna_top_y = robot_y - body_size // 2 - head_size - antenna_height
        
        # Left antenna
        left_antenna_x = center_x - 15 + int(self.antenna_sway * 0.5)
        pygame.draw.line(surface, (255, 165, 0), 
                        (center_x - 15, robot_y - body_size // 2 - head_size),
                        (left_antenna_x, antenna_top_y), 3)
        pygame.draw.circle(surface, (255, 0, 0), (left_antenna_x, antenna_top_y), 4)
        
        # Right antenna
        right_antenna_x = center_x + 15 - int(self.antenna_sway * 0.5)
        pygame.draw.line(surface, (255, 165, 0),
                        (center_x + 15, robot_y - body_size // 2 - head_size),
                        (right_antenna_x, antenna_top_y), 3)
        pygame.draw.circle(surface, (255, 0, 0), (right_antenna_x, antenna_top_y), 4)
        
        # Highly reactive arms
        base_arm_length = 25 * self.arm_length_multiplier
        
        # Left arm - dynamic movement
        left_arm_angle = math.sin(self.arm_angle_left) * 0.8 + math.cos(self.arm_angle_left * 0.7) * 0.4
        left_arm_end = (
            center_x - body_size // 2 + int(math.cos(left_arm_angle) * base_arm_length),
            robot_y + int(math.sin(left_arm_angle) * base_arm_length)
        )
        
        # Right arm - different reactive pattern
        right_arm_angle = math.cos(self.arm_angle_right) * 0.9 + math.sin(self.arm_angle_right * 1.3) * 0.3
        right_arm_end = (
            center_x + body_size // 2 + int(math.cos(right_arm_angle) * base_arm_length),
            robot_y + int(math.sin(right_arm_angle) * base_arm_length)
        )
        
        # Draw arms with variable thickness based on energy
        arm_thickness = max(3, int(5 * self.arm_length_multiplier))
        
        pygame.draw.line(surface, (255, 220, 220),
                        (center_x - body_size // 2, robot_y),
                        left_arm_end, arm_thickness)
        pygame.draw.line(surface, (255, 220, 220),
                        (center_x + body_size // 2, robot_y),
                        right_arm_end, arm_thickness)
        
        # Hands - size varies with energy
        hand_size = int(8 * self.arm_length_multiplier)
        pygame.draw.circle(surface, (255, 255, 255), left_arm_end, hand_size)
        pygame.draw.circle(surface, (255, 255, 255), right_arm_end, hand_size)

class MusicAnalyzer:
    def __init__(self, audio_file, fps=30):
        self.fps = fps
        self.y, self.sr = librosa.load(audio_file)
        self.duration = len(self.y) / self.sr
        
        # Pre-compute audio features
        self.compute_features()
    
    def compute_features(self):
        """Pre-compute all audio features for the entire track"""
        hop_length = int(self.sr / self.fps)
        
        # Beat tracking
        tempo, beats = librosa.beat.beat_track(y=self.y, sr=self.sr, hop_length=hop_length)
        self.tempo = tempo
        
        # RMS energy (for beat strength and arm reactivity)
        self.rms = librosa.feature.rms(y=self.y, hop_length=hop_length)[0]
        
        # Spectral centroid (brightness)
        self.spectral_centroid = librosa.feature.spectral_centroid(y=self.y, sr=self.sr, hop_length=hop_length)[0]
        
        # Zero crossing rate (for additional arm movement variation)
        self.zcr = librosa.feature.zero_crossing_rate(y=self.y, hop_length=hop_length)[0]
        
        # Normalize features
        self.rms = (self.rms - np.min(self.rms)) / (np.max(self.rms) - np.min(self.rms))
        self.spectral_centroid = (self.spectral_centroid - np.min(self.spectral_centroid)) / (np.max(self.spectral_centroid) - np.min(self.spectral_centroid))
        self.zcr = (self.zcr - np.min(self.zcr)) / (np.max(self.zcr) - np.min(self.zcr))
        
        # Beat strength detection
        self.beat_frames = librosa.frames_to_samples(beats, hop_length=hop_length)
        self.beat_strength = np.zeros(len(self.rms))
        
        for beat_frame in self.beat_frames:
            frame_idx = int(beat_frame * self.fps / self.sr)
            if frame_idx < len(self.beat_strength):
                self.beat_strength[frame_idx] = 1.0
        
        # Smooth beat strength
        kernel = np.exp(-np.linspace(-2, 2, 10)**2)
        kernel = kernel / np.sum(kernel)
        self.beat_strength = np.convolve(self.beat_strength, kernel, mode='same')
    
    def get_features_at_time(self, time_seconds):
        """Get audio features at a specific time"""
        frame_idx = int(time_seconds * self.fps)
        frame_idx = max(0, min(frame_idx, len(self.rms) - 1))
        
        return {
            'beat_strength': self.beat_strength[frame_idx],
            'spectral_centroid': self.spectral_centroid[frame_idx],
            'tempo_factor': self.tempo / 120.0,  # Normalize around 120 BPM
            'rms_energy': self.rms[frame_idx]
        }

def create_robot_animation(input_video, output_video, robot_size=(200, 200)):
    """Create standalone robot animation video from input music video"""
    
    # Initialize pygame
    pygame.init()
    
    # Load video to get timing info
    cap = cv2.VideoCapture(input_video)
    if not cap.isOpened():
        raise ValueError(f"Could not open video file: {input_video}")
    
    # Get video properties
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps
    
    cap.release()  # We only needed the timing info
    
    print(f"Video: {fps} FPS, {total_frames} frames, {duration:.2f} seconds")
    print(f"Robot animation: {robot_size[0]}x{robot_size[1]}")
    
    # Extract audio for analysis
    import tempfile
    import subprocess
    
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio:
        temp_audio_path = temp_audio.name
    
    # Extract audio using ffmpeg
    cmd = [
        'ffmpeg', '-i', input_video, '-vn', '-acodec', 'pcm_s16le', 
        '-ar', '22050', '-ac', '1', '-y', temp_audio_path
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    
    # Initialize components
    analyzer = MusicAnalyzer(temp_audio_path, fps=fps)
    robot = MusicRobot(robot_size)
    
    # Create pygame surface for robot
    robot_surface = pygame.Surface(robot_size)
    
    # Video writer - output just the robot animation on black background
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_video, fourcc, fps, robot_size)
    
    frame_count = 0
    
    try:
        for frame_count in range(total_frames):
            # Get current time
            current_time = frame_count / fps
            
            # Get audio features
            features = analyzer.get_features_at_time(current_time)
            
            # Update robot with enhanced arm reactivity
            robot.update(
                features['beat_strength'],
                features['spectral_centroid'],
                features['tempo_factor'],
                features['rms_energy']
            )
            
            # Draw robot
            robot.draw(robot_surface)
            
            # Convert pygame surface to OpenCV format
            robot_array = pygame.surfarray.array3d(robot_surface)
            robot_array = np.rot90(robot_array)
            robot_array = np.flipud(robot_array)
            robot_bgr = cv2.cvtColor(robot_array, cv2.COLOR_RGB2BGR)
            
            out.write(robot_bgr)
            
            if frame_count % 100 == 0:
                print(f"Processed {frame_count}/{total_frames} frames")
    
    finally:
        out.release()
        pygame.quit()
        
        # Clean up temp file
        Path(temp_audio_path).unlink(missing_ok=True)
    
    print(f"Robot animation saved to: {output_video}")
    print("This video has a black background and can be composited over your original video.")

def main():
    parser = argparse.ArgumentParser(description='Generate music-reactive robot animation')
    parser.add_argument('input_video', help='Input music video file (mp4)')
    parser.add_argument('-o', '--output', help='Output robot animation file', 
                       default='robot_animation.mp4')
    parser.add_argument('--robot-size', nargs=2, type=int, default=[200, 200], 
                       help='Robot animation size (width height)')
    
    args = parser.parse_args()
    
    if not Path(args.input_video).exists():
        print(f"Error: Input video '{args.input_video}' not found")
        return
    
    print(f"Processing video: {args.input_video}")
    print(f"Robot size: {args.robot_size[0]}x{args.robot_size[1]}")
    
    create_robot_animation(
        args.input_video,
        args.output,
        tuple(args.robot_size)
    )

if __name__ == "__main__":
    main()