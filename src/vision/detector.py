import cv2
import logging
import mediapipe as mp
from typing import Optional, Tuple
from .zone import PhoneZone

logger = logging.getLogger(__name__)


class HandDetector:
    """Detects hands in camera feed and checks if they're in the phone zone."""

    def __init__(self, camera_config: dict, zone: PhoneZone, confidence_threshold: float = 0.7):
        """
        Initialize hand detector.

        Args:
            camera_config: Camera configuration dict
            zone: PhoneZone instance defining detection area
            confidence_threshold: Minimum confidence for hand detection (0-1)
        """
        self.zone = zone
        self.confidence_threshold = confidence_threshold
        self.camera_config = camera_config

        # Initialize MediaPipe Hands
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=confidence_threshold,
            min_tracking_confidence=confidence_threshold
        )

        # Initialize camera
        self.cap = cv2.VideoCapture(camera_config['device_index'])
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, camera_config['width'])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_config['height'])
        self.cap.set(cv2.CAP_PROP_FPS, camera_config['fps'])

        if not self.cap.isOpened():
            raise RuntimeError("Could not open camera")

        # Get actual frame dimensions
        self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        logger.info(f"Hand detector initialized at {self.frame_width}x{self.frame_height}")

    def detect_hand_in_zone(self) -> Tuple[bool, Optional[cv2.Mat]]:
        """
        Check if a hand is detected in the phone zone.

        Returns:
            (hand_detected, frame) tuple
            - hand_detected: True if hand is in zone
            - frame: Current frame (or None if read failed)
        """
        ret, frame = self.cap.read()
        if not ret:
            logger.warning("Failed to read frame from camera")
            return False, None

        # Convert BGR to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Process frame with MediaPipe
        results = self.hands.process(rgb_frame)

        hand_in_zone = False

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Check if any landmark is in the zone
                # Using wrist (landmark 0) and palm center as key points
                wrist = hand_landmarks.landmark[0]
                middle_mcp = hand_landmarks.landmark[9]  # Middle finger base

                # Check if key points are in zone
                if (self.zone.contains_point(wrist.x, wrist.y) or
                    self.zone.contains_point(middle_mcp.x, middle_mcp.y)):
                    hand_in_zone = True
                    logger.debug("Hand detected in phone zone")
                    break

        return hand_in_zone, frame

    def get_annotated_frame(self) -> Optional[cv2.Mat]:
        """
        Get a frame with detection zone and hand landmarks drawn (for calibration/debugging).

        Returns:
            Annotated frame or None if read failed
        """
        ret, frame = self.cap.read()
        if not ret:
            return None

        # Draw detection zone
        x1, y1, x2, y2 = self.zone.get_pixel_coords(self.frame_width, self.frame_height)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(frame, "Phone Zone", (x1, y1 - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        # Convert BGR to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)

        # Draw hand landmarks
        if results.multi_hand_landmarks:
            mp_drawing = mp.solutions.drawing_utils
            for hand_landmarks in results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(
                    frame,
                    hand_landmarks,
                    self.mp_hands.HAND_CONNECTIONS
                )

        return frame

    def cleanup(self):
        """Release camera resources."""
        self.hands.close()
        self.cap.release()
        logger.info("Hand detector cleaned up")
