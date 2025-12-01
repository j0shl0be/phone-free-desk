import time
import logging
from gpiozero import AngularServo
from gpiozero.pins.pigpio import PiGPIOFactory

logger = logging.getLogger(__name__)


class RoboticArm:
    """Controls a 2-DOF robotic arm using servo motors."""

    def __init__(self, servo_1_pin: int, servo_2_pin: int, config: dict):
        """
        Initialize the robotic arm.

        Args:
            servo_1_pin: GPIO pin for first servo
            servo_2_pin: GPIO pin for second servo
            config: Servo configuration dict from settings
        """
        self.config = config

        # Use pigpio for better PWM control
        try:
            factory = PiGPIOFactory()
        except Exception as e:
            logger.warning(f"Could not initialize pigpio, using default: {e}")
            factory = None

        # Initialize servos (assuming SG90 servos: -90 to 90 degrees)
        self.servo_1 = AngularServo(
            servo_1_pin,
            min_angle=-90,
            max_angle=90,
            pin_factory=factory
        )

        self.servo_2 = AngularServo(
            servo_2_pin,
            min_angle=-90,
            max_angle=90,
            pin_factory=factory
        )

        # Move to rest position on init
        self.move_to_rest()
        logger.info("Robotic arm initialized")

    def _angle_to_servo_range(self, angle: float) -> float:
        """Convert 0-180 degree range to servo's -90 to 90 range."""
        return angle - 90

    def move_to_rest(self):
        """Move arm to rest position."""
        angle_1 = self._angle_to_servo_range(self.config['servo_1_rest'])
        angle_2 = self._angle_to_servo_range(self.config['servo_2_rest'])

        self.servo_1.angle = angle_1
        self.servo_2.angle = angle_2
        logger.debug(f"Moved to rest position: ({angle_1}, {angle_2})")

    def move_to_spray(self):
        """Move arm to spray position."""
        angle_1 = self._angle_to_servo_range(self.config['servo_1_spray'])
        angle_2 = self._angle_to_servo_range(self.config['servo_2_spray'])

        self.servo_1.angle = angle_1
        self.servo_2.angle = angle_2
        logger.debug(f"Moved to spray position: ({angle_1}, {angle_2})")

    def move_smooth(self, target_1: float, target_2: float, duration: float):
        """
        Smoothly move servos to target positions.

        Args:
            target_1: Target angle for servo 1 (0-180)
            target_2: Target angle for servo 2 (0-180)
            duration: Time to complete movement in seconds
        """
        # Convert to servo range
        target_1 = self._angle_to_servo_range(target_1)
        target_2 = self._angle_to_servo_range(target_2)

        # Get current positions (approximate)
        start_1 = self.servo_1.angle or 0
        start_2 = self.servo_2.angle or 0

        steps = 20
        step_duration = duration / steps

        for i in range(steps + 1):
            progress = i / steps
            angle_1 = start_1 + (target_1 - start_1) * progress
            angle_2 = start_2 + (target_2 - start_2) * progress

            self.servo_1.angle = angle_1
            self.servo_2.angle = angle_2
            time.sleep(step_duration)

    def cleanup(self):
        """Clean up GPIO resources."""
        self.move_to_rest()
        time.sleep(0.5)
        self.servo_1.close()
        self.servo_2.close()
        logger.info("Robotic arm cleaned up")
