#!/usr/bin/env python3
"""
Phone Free Desk - Main Entry Point

Coordinates the web API, vision detection, and hardware control
to spray water when a hand is detected near a phone while DND is active.
"""

import logging
import signal
import sys
import yaml
import uvicorn
from pathlib import Path
from threading import Thread

# Import components
from api.server import create_app
from hardware import RoboticArm, WaterPump, SpraySequence, ArmKinematics
from vision import HandDetector
from core import Orchestrator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/phone-free-desk.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class PhoneFreeDesk:
    """Main application class."""

    def __init__(self, config_path: str = "config/settings.yaml"):
        """
        Initialize the application.

        Args:
            config_path: Path to configuration YAML file
        """
        logger.info("Initializing Phone Free Desk")

        # Load configuration
        self.config = self._load_config(config_path)

        # Initialize hardware
        logger.info("Initializing hardware...")
        self.arm = RoboticArm(
            self.config['gpio']['servo_1'],
            self.config['gpio']['servo_2'],
            self.config['servo']
        )
        self.pump = WaterPump(self.config['gpio']['pump'])
        self.spray_sequence = SpraySequence(self.arm, self.pump, self.config)

        # Initialize vision
        logger.info("Initializing vision...")
        self.hand_detector = HandDetector(
            self.config['camera'],
            self.config['vision']['confidence_threshold']
        )

        # Initialize kinematics
        logger.info("Initializing kinematics...")
        self.kinematics = ArmKinematics(self.config.get('kinematics', {}))

        # Initialize orchestrator
        logger.info("Initializing orchestrator...")
        self.orchestrator = Orchestrator(
            self.spray_sequence,
            self.hand_detector,
            self.kinematics,
            self.config
        )

        # Create FastAPI app
        self.app = create_app()

        logger.info("Phone Free Desk initialized successfully")

    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file."""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(path, 'r') as f:
            config = yaml.safe_load(f)

        logger.info(f"Configuration loaded from {config_path}")
        return config

    def run(self):
        """Run the application."""
        try:
            # Start orchestrator
            self.orchestrator.start()

            # Run FastAPI server (blocking)
            logger.info(f"Starting API server on {self.config['api']['host']}:{self.config['api']['port']}")
            uvicorn.run(
                self.app,
                host=self.config['api']['host'],
                port=self.config['api']['port'],
                log_level="info"
            )

        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.error(f"Error running application: {e}", exc_info=True)
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up resources...")
        try:
            self.orchestrator.cleanup()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        logger.info("Shutdown complete")


def main():
    """Main entry point."""
    # Create and run application
    app = PhoneFreeDesk()

    # Setup signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}")
        app.cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run the application
    app.run()


if __name__ == "__main__":
    main()
