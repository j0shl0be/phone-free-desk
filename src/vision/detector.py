import cv2
import logging
import mediapipe as mp
import numpy as np
from typing import Optional, Tuple, Dict, List
from pathlib import Path

logger = logging.getLogger(__name__)


class HandDetector:
    """Detects hands, phone, and face in camera feed. Triggers when hand overlaps with phone."""

    def __init__(self, camera_config: dict, confidence_threshold: float = 0.7):
        """
        Initialize detector.

        Args:
            camera_config: Camera configuration dict
            confidence_threshold: Minimum confidence for detection (0-1)
        """
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

        # Initialize MediaPipe Face Detection
        self.mp_face = mp.solutions.face_detection
        self.face_detection = self.mp_face.FaceDetection(
            min_detection_confidence=confidence_threshold
        )

        # Initialize phone detector (MobileNet SSD)
        # Note: Model files will need to be downloaded during setup
        # Using COCO-pretrained MobileNet SSD which can detect "cell phone"
        self.phone_detector = None
        self.phone_class_id = 77  # Cell phone class in COCO dataset
        logger.info("Phone detection using color/shape analysis (fallback mode)")

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

    def _detect_phone(self, frame: cv2.Mat) -> Optional[Tuple[int, int, int, int]]:
        """
        Detect phone in frame using edge detection and contour analysis.

        Returns:
            (x, y, w, h) bounding box or None if no phone detected
        """
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Apply Gaussian blur
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Edge detection
        edges = cv2.Canny(blurred, 50, 150)

        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Look for phone-like rectangles
        phone_candidates = []

        for contour in contours:
            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(contour)

            # Filter by size (phone should be reasonable size in frame)
            min_area = (self.frame_width * self.frame_height) * 0.02  # At least 2% of frame
            max_area = (self.frame_width * self.frame_height) * 0.3   # At most 30% of frame
            area = w * h

            if area < min_area or area > max_area:
                continue

            # Filter by aspect ratio (phones are usually portrait: 1.5-2.5 or landscape: 0.4-0.7)
            aspect_ratio = h / w if h > w else w / h
            if not (1.3 < aspect_ratio < 2.8):
                continue

            # Check if contour is roughly rectangular
            approx = cv2.approxPolyDP(contour, 0.04 * cv2.arcLength(contour, True), True)
            if len(approx) >= 4:  # At least 4 vertices (rectangular-ish)
                phone_candidates.append((x, y, w, h, area))

        # Return largest candidate
        if phone_candidates:
            phone_candidates.sort(key=lambda x: x[4], reverse=True)
            x, y, w, h, _ = phone_candidates[0]
            return (x, y, w, h)

        return None

    def _check_overlap(self, box1: Tuple[int, int, int, int],
                      box2: Tuple[int, int, int, int]) -> bool:
        """
        Check if two bounding boxes overlap.

        Args:
            box1: (x, y, w, h)
            box2: (x, y, w, h)

        Returns:
            True if boxes overlap
        """
        x1, y1, w1, h1 = box1
        x2, y2, w2, h2 = box2

        # Check if one box is to the left of the other
        if x1 + w1 < x2 or x2 + w2 < x1:
            return False

        # Check if one box is above the other
        if y1 + h1 < y2 or y2 + h2 < y1:
            return False

        return True

    def detect_hand_in_zone(self) -> Tuple[bool, Optional[Dict[str, float]], Optional[cv2.Mat]]:
        """
        Check if hand overlaps with phone and detect face for targeting.

        Returns:
            (hand_touching_phone, face_position, frame) tuple
            - hand_touching_phone: True if hand overlaps with detected phone (trigger)
            - face_position: Dict with 'x', 'y' normalized coordinates (0-1) of face center (target), or None
            - frame: Current frame (or None if read failed)
        """
        ret, frame = self.cap.read()
        if not ret:
            logger.warning("Failed to read frame from camera")
            return False, None, None

        # Detect phone
        phone_bbox = self._detect_phone(frame)

        # Convert BGR to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Process hands
        hand_results = self.hands.process(rgb_frame)
        hand_touching_phone = False
        hand_bboxes = []

        if hand_results.multi_hand_landmarks:
            for hand_landmarks in hand_results.multi_hand_landmarks:
                # Calculate hand bounding box from landmarks
                x_coords = [lm.x * self.frame_width for lm in hand_landmarks.landmark]
                y_coords = [lm.y * self.frame_height for lm in hand_landmarks.landmark]

                x_min = int(min(x_coords))
                y_min = int(min(y_coords))
                x_max = int(max(x_coords))
                y_max = int(max(y_coords))

                hand_bbox = (x_min, y_min, x_max - x_min, y_max - y_min)
                hand_bboxes.append(hand_bbox)

                # Check overlap with phone
                if phone_bbox and self._check_overlap(hand_bbox, phone_bbox):
                    hand_touching_phone = True
                    logger.debug("Hand touching phone detected!")

        # Process face detection (for targeting)
        face_results = self.face_detection.process(rgb_frame)
        face_position = None

        if face_results.detections:
            # Use the first detected face
            detection = face_results.detections[0]
            bbox = detection.location_data.relative_bounding_box

            # Calculate face center
            face_x = bbox.xmin + bbox.width / 2
            face_y = bbox.ymin + bbox.height / 2

            face_position = {
                'x': face_x,
                'y': face_y
            }

            logger.debug(f"Face detected at ({face_position['x']:.3f}, {face_position['y']:.3f})")

        return hand_touching_phone, face_position, frame

    def get_annotated_frame(self) -> Optional[cv2.Mat]:
        """
        Get a frame with phone, hand, and face detection drawn (for calibration/debugging).

        Returns:
            Annotated frame or None if read failed
        """
        ret, frame = self.cap.read()
        if not ret:
            return None

        # Detect phone
        phone_bbox = self._detect_phone(frame)
        if phone_bbox:
            x, y, w, h = phone_bbox
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(frame, "PHONE", (x, y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Convert BGR to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Draw hand landmarks and bounding boxes
        hand_results = self.hands.process(rgb_frame)
        if hand_results.multi_hand_landmarks:
            mp_drawing = mp.solutions.drawing_utils
            for hand_landmarks in hand_results.multi_hand_landmarks:
                # Draw landmarks
                mp_drawing.draw_landmarks(
                    frame,
                    hand_landmarks,
                    self.mp_hands.HAND_CONNECTIONS
                )

                # Draw hand bounding box
                x_coords = [lm.x * self.frame_width for lm in hand_landmarks.landmark]
                y_coords = [lm.y * self.frame_height for lm in hand_landmarks.landmark]
                x_min, y_min = int(min(x_coords)), int(min(y_coords))
                x_max, y_max = int(max(x_coords)), int(max(y_coords))

                hand_bbox = (x_min, y_min, x_max - x_min, y_max - y_min)

                # Check if overlapping with phone
                is_touching = phone_bbox and self._check_overlap(hand_bbox, phone_bbox)
                color = (0, 0, 255) if is_touching else (255, 255, 0)  # Red if touching, cyan if not

                cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), color, 2)
                if is_touching:
                    cv2.putText(frame, "TOUCHING!", (x_min, y_min - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        # Draw face detections
        face_results = self.face_detection.process(rgb_frame)
        if face_results.detections:
            for detection in face_results.detections:
                bbox = detection.location_data.relative_bounding_box

                # Convert to pixel coordinates
                x = int(bbox.xmin * self.frame_width)
                y = int(bbox.ymin * self.frame_height)
                w = int(bbox.width * self.frame_width)
                h = int(bbox.height * self.frame_height)

                # Draw face bounding box
                cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

                # Draw center crosshair
                center_x = x + w // 2
                center_y = y + h // 2
                cv2.drawMarker(frame, (center_x, center_y), (255, 0, 0),
                              cv2.MARKER_CROSS, 20, 2)
                cv2.putText(frame, "TARGET", (center_x - 30, center_y - 20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

        return frame

    def cleanup(self):
        """Release camera resources."""
        self.hands.close()
        self.face_detection.close()
        self.cap.release()
        logger.info("Hand detector cleaned up")
