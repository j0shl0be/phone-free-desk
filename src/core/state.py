import time
import logging
from threading import Lock

logger = logging.getLogger(__name__)


class SystemState:
    """Thread-safe system state management."""

    def __init__(self, cooldown_period: float):
        """
        Initialize system state.

        Args:
            cooldown_period: Minimum seconds between spray activations
        """
        self.cooldown_period = cooldown_period
        self._lock = Lock()
        self._last_spray_time = 0
        self._consecutive_detections = 0

    def can_spray(self) -> bool:
        """
        Check if enough time has passed since last spray.

        Returns:
            True if system is ready to spray again
        """
        with self._lock:
            time_since_last = time.time() - self._last_spray_time
            return time_since_last >= self.cooldown_period

    def record_spray(self):
        """Record that a spray just occurred."""
        with self._lock:
            self._last_spray_time = time.time()
            self._consecutive_detections = 0
            logger.info(f"Spray recorded. Cooldown until {time.time() + self.cooldown_period:.1f}")

    def get_cooldown_remaining(self) -> float:
        """
        Get remaining cooldown time in seconds.

        Returns:
            Seconds remaining (0 if ready)
        """
        with self._lock:
            elapsed = time.time() - self._last_spray_time
            remaining = max(0, self.cooldown_period - elapsed)
            return remaining

    def increment_detection(self) -> int:
        """
        Increment consecutive detection counter.

        Returns:
            New detection count
        """
        with self._lock:
            self._consecutive_detections += 1
            return self._consecutive_detections

    def reset_detections(self):
        """Reset consecutive detection counter."""
        with self._lock:
            self._consecutive_detections = 0

    def get_detection_count(self) -> int:
        """Get current consecutive detection count."""
        with self._lock:
            return self._consecutive_detections
