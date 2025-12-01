import logging
import numpy as np
from typing import Tuple, Dict

logger = logging.getLogger(__name__)


class ArmKinematics:
    """
    Inverse kinematics for 2DOF robotic arm.

    Maps 2D camera coordinates to servo angles for targeting.
    Assumes:
    - Servo 1 controls horizontal rotation (azimuth)
    - Servo 2 controls vertical tilt (elevation)
    """

    def __init__(self, calibration: dict):
        """
        Initialize kinematics with calibration data.

        Args:
            calibration: Dict containing calibration parameters
                - camera_to_world: Transformation from camera coords to world coords
                - servo_limits: Min/max angles for each servo
        """
        self.calibration = calibration

        # Camera field of view mapping
        # Normalized x: 0 (left) -> 1 (right) maps to servo angles
        # Normalized y: 0 (top) -> 1 (bottom) maps to servo angles

        # Get calibration corners (camera coords -> servo angles)
        corners = calibration.get('corners', {})

        # Corner calibration points: camera (x, y) -> (servo1_angle, servo2_angle)
        # Default assumes center of frame maps to center servo positions
        self.top_left = corners.get('top_left', {'cam_x': 0.0, 'cam_y': 0.0, 'servo1': 60, 'servo2': 120})
        self.top_right = corners.get('top_right', {'cam_x': 1.0, 'cam_y': 0.0, 'servo1': 120, 'servo2': 120})
        self.bottom_left = corners.get('bottom_left', {'cam_x': 0.0, 'cam_y': 1.0, 'servo1': 60, 'servo2': 80})
        self.bottom_right = corners.get('bottom_right', {'cam_x': 1.0, 'cam_y': 1.0, 'servo1': 120, 'servo2': 80})

        logger.info("Arm kinematics initialized with calibration")

    def camera_to_servo_angles(self, cam_x: float, cam_y: float) -> Tuple[float, float]:
        """
        Convert normalized camera coordinates to servo angles.

        Uses bilinear interpolation across calibrated corner points.

        Args:
            cam_x: Normalized camera X coordinate (0=left, 1=right)
            cam_y: Normalized camera Y coordinate (0=top, 1=bottom)

        Returns:
            (servo1_angle, servo2_angle) tuple in degrees (0-180)
        """
        # Clamp to valid range
        cam_x = np.clip(cam_x, 0.0, 1.0)
        cam_y = np.clip(cam_y, 0.0, 1.0)

        # Bilinear interpolation
        # Interpolate top edge
        top_servo1 = self.top_left['servo1'] + cam_x * (self.top_right['servo1'] - self.top_left['servo1'])
        top_servo2 = self.top_left['servo2'] + cam_x * (self.top_right['servo2'] - self.top_left['servo2'])

        # Interpolate bottom edge
        bottom_servo1 = self.bottom_left['servo1'] + cam_x * (self.bottom_right['servo1'] - self.bottom_left['servo1'])
        bottom_servo2 = self.bottom_left['servo2'] + cam_x * (self.bottom_right['servo2'] - self.bottom_left['servo2'])

        # Interpolate between top and bottom
        servo1 = top_servo1 + cam_y * (bottom_servo1 - top_servo1)
        servo2 = top_servo2 + cam_y * (bottom_servo2 - top_servo2)

        # Clamp to valid servo range
        servo1 = np.clip(servo1, 0, 180)
        servo2 = np.clip(servo2, 0, 180)

        logger.debug(f"Camera ({cam_x:.3f}, {cam_y:.3f}) -> Servo angles ({servo1:.1f}°, {servo2:.1f}°)")

        return float(servo1), float(servo2)

    def get_spray_angles(self, hand_position: Dict[str, float]) -> Tuple[float, float]:
        """
        Get servo angles to spray at detected hand position.

        Args:
            hand_position: Dict with 'x', 'y' normalized camera coordinates

        Returns:
            (servo1_angle, servo2_angle) tuple in degrees
        """
        return self.camera_to_servo_angles(hand_position['x'], hand_position['y'])

    def update_corner_calibration(self, corner: str, cam_x: float, cam_y: float,
                                  servo1: float, servo2: float):
        """
        Update a corner calibration point.

        Args:
            corner: 'top_left', 'top_right', 'bottom_left', or 'bottom_right'
            cam_x: Camera x coordinate (0-1)
            cam_y: Camera y coordinate (0-1)
            servo1: Servo 1 angle (0-180)
            servo2: Servo 2 angle (0-180)
        """
        point = {'cam_x': cam_x, 'cam_y': cam_y, 'servo1': servo1, 'servo2': servo2}

        if corner == 'top_left':
            self.top_left = point
        elif corner == 'top_right':
            self.top_right = point
        elif corner == 'bottom_left':
            self.bottom_left = point
        elif corner == 'bottom_right':
            self.bottom_right = point
        else:
            raise ValueError(f"Invalid corner: {corner}")

        logger.info(f"Updated {corner} calibration: cam({cam_x:.3f}, {cam_y:.3f}) -> servos({servo1:.1f}°, {servo2:.1f}°)")

    def get_calibration_dict(self) -> dict:
        """
        Get current calibration as a dict for saving to config.

        Returns:
            Calibration dict with corner points
        """
        return {
            'corners': {
                'top_left': self.top_left,
                'top_right': self.top_right,
                'bottom_left': self.bottom_left,
                'bottom_right': self.bottom_right
            }
        }
