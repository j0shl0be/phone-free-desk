import time
import logging
from gpiozero import OutputDevice

logger = logging.getLogger(__name__)


class WaterPump:
    """Controls a water pump via GPIO relay."""

    def __init__(self, pump_pin: int):
        """
        Initialize the water pump.

        Args:
            pump_pin: GPIO pin connected to pump relay
        """
        # OutputDevice for simple on/off control
        # active_high=True means HIGH turns pump on
        self.pump = OutputDevice(pump_pin, active_high=True, initial_value=False)
        self.is_running = False
        logger.info(f"Water pump initialized on GPIO {pump_pin}")

    def on(self):
        """Turn pump on."""
        if not self.is_running:
            self.pump.on()
            self.is_running = True
            logger.debug("Pump turned ON")

    def off(self):
        """Turn pump off."""
        if self.is_running:
            self.pump.off()
            self.is_running = False
            logger.debug("Pump turned OFF")

    def spray(self, duration: float):
        """
        Run pump for a specific duration.

        Args:
            duration: Time to run pump in seconds
        """
        logger.info(f"Spraying for {duration} seconds")
        self.on()
        time.sleep(duration)
        self.off()

    def cleanup(self):
        """Clean up GPIO resources."""
        self.off()
        self.pump.close()
        logger.info("Water pump cleaned up")
