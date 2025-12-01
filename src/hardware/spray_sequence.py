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

    def execute(self):
        """Execute the full spray sequence."""
        logger.info("Starting spray sequence")

        try:
            # Step 1: Move arm to spray position
            logger.debug("Moving arm to spray position")
            self.arm.move_smooth(
                self.servo_config['servo_1_spray'],
                self.servo_config['servo_2_spray'],
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
