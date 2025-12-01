import time
import logging
from .arm import RoboticArm
from .pump import WaterPump

logger = logging.getLogger(__name__)


class SpraySequence:
    """Orchestrates the complete spray sequence with arm and pump."""

    def __init__(self, arm: RoboticArm, pump: WaterPump, config: dict):
        """
        Initialize spray sequence controller.

        Args:
            arm: RoboticArm instance
            pump: WaterPump instance
            config: Configuration dict with servo and pump settings
        """
        self.arm = arm
        self.pump = pump
        self.servo_config = config['servo']
        self.pump_config = config['pump']
        logger.info("Spray sequence initialized")

    def execute(self, target_servo1: float, target_servo2: float):
        """
        Execute the full spray sequence aimed at a specific target.

        Args:
            target_servo1: Target angle for servo 1 (0-180 degrees)
            target_servo2: Target angle for servo 2 (0-180 degrees)
        """
        logger.info(f"Starting spray sequence targeting ({target_servo1:.1f}°, {target_servo2:.1f}°)")

        try:
            # Step 1: Move arm to target position
            logger.debug("Moving arm to target position")
            self.arm.move_smooth(
                target_servo1,
                target_servo2,
                self.servo_config['movement_duration']
            )

            # Step 2: Wait for arm to stabilize
            time.sleep(0.3)

            # Step 3: Activate pump
            self.pump.spray(self.pump_config['spray_duration'])

            # Step 4: Return arm to rest position
            logger.debug("Returning arm to rest position")
            self.arm.move_smooth(
                self.servo_config['servo_1_rest'],
                self.servo_config['servo_2_rest'],
                self.servo_config['movement_duration']
            )

            logger.info("Spray sequence completed")

        except Exception as e:
            logger.error(f"Error during spray sequence: {e}")
            # Ensure pump is off even if error occurs
            self.pump.off()
            # Try to return arm to rest
            try:
                self.arm.move_to_rest()
            except:
                pass
            raise

    def cleanup(self):
        """Clean up hardware resources."""
        self.pump.cleanup()
        self.arm.cleanup()
