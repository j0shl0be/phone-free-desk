import time
import logging
import threading
from typing import Callable
from .state import SystemState
from ..hardware import SpraySequence
from ..vision import HandDetector
from ..api.routes import get_dnd_state

logger = logging.getLogger(__name__)


class Orchestrator:
    """Main orchestrator that coordinates vision detection and spray activation."""

    def __init__(
        self,
        spray_sequence: SpraySequence,
        hand_detector: HandDetector,
        config: dict
    ):
        """
        Initialize orchestrator.

        Args:
            spray_sequence: SpraySequence instance
            hand_detector: HandDetector instance
            config: Full configuration dict
        """
        self.spray_sequence = spray_sequence
        self.hand_detector = hand_detector
        self.config = config

        # Initialize system state
        self.state = SystemState(config['pump']['cooldown_period'])

        # Detection configuration
        self.min_detection_frames = config['vision']['min_detection_frames']

        # Control flags
        self._running = False
        self._vision_thread = None

        logger.info("Orchestrator initialized")

    def _vision_loop(self):
        """Main vision detection loop (runs in separate thread)."""
        logger.info("Vision loop started")

        while self._running:
            try:
                # Get DND status from API state
                dnd_state = get_dnd_state()
                dnd_active = dnd_state["active"]

                # Detect hand in zone
                hand_detected, _ = self.hand_detector.detect_hand_in_zone()

                if hand_detected:
                    detection_count = self.state.increment_detection()
                    logger.debug(f"Hand detected ({detection_count}/{self.min_detection_frames})")
                else:
                    # Reset counter if no hand detected
                    if self.state.get_detection_count() > 0:
                        self.state.reset_detections()
                        logger.debug("Hand detection reset")

                # Check if we should trigger spray
                should_spray = (
                    dnd_active and
                    self.state.get_detection_count() >= self.min_detection_frames and
                    self.state.can_spray()
                )

                if should_spray:
                    logger.warning("TRIGGERING SPRAY SEQUENCE!")
                    try:
                        self.spray_sequence.execute()
                        self.state.record_spray()
                    except Exception as e:
                        logger.error(f"Error executing spray sequence: {e}")

                # Small sleep to control loop rate
                # FPS is controlled by camera, but add small delay
                time.sleep(0.05)

            except Exception as e:
                logger.error(f"Error in vision loop: {e}")
                time.sleep(1)  # Longer delay on error

        logger.info("Vision loop stopped")

    def start(self):
        """Start the orchestrator and vision loop."""
        if self._running:
            logger.warning("Orchestrator already running")
            return

        self._running = True

        # Start vision loop in separate thread
        self._vision_thread = threading.Thread(target=self._vision_loop, daemon=True)
        self._vision_thread.start()

        logger.info("Orchestrator started")

    def stop(self):
        """Stop the orchestrator and vision loop."""
        if not self._running:
            return

        logger.info("Stopping orchestrator...")
        self._running = False

        # Wait for vision thread to finish
        if self._vision_thread:
            self._vision_thread.join(timeout=5)

        logger.info("Orchestrator stopped")

    def cleanup(self):
        """Clean up all resources."""
        self.stop()
        self.hand_detector.cleanup()
        self.spray_sequence.cleanup()
        logger.info("Orchestrator cleaned up")
