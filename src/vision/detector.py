import cv2
import logging
import numpy as np
from typing import Optional, Tuple, Dict, List
from pathlib import Path
from ultralytics import YOLO

logger = logging.getLogger(__name__)


class HandDetector:
    """Detects phone, hands, and people using YOLOv8. Triggers when hand overlaps with phone."""

    def __init__(self, camera_config: dict, vision_config: dict = None):
        """
        Initialize detector with YOLOv8.

        Args:
            camera_config: Camera configuration dict
            vision_config: Vision configuration dict (optional, for backwards compat)
        """
        self.camera_config = camera_config

        # Handle both old and new API
        if vision_config is None:
            # Old API: second param was confidence_threshold
            vision_config = {'phone_confidence': 0.3, 'person_confidence': 0.5}
        elif isinstance(vision_config, (int, float)):
            # Old API: second param was confidence_threshold
            vision_config = {'phone_confidence': float(vision_config), 'person_confidence': float(vision_config)}

        self.vision_config = vision_config

        # Get config values
        model_path = vision_config.get('model', 'yolov8n.pt')
        self.phone_confidence = vision_config.get('phone_confidence', 0.3)
        self.person_confidence = vision_config.get('person_confidence', 0.5)
        self.frame_skip = vision_config.get('frame_skip', 2)
        self.debug = vision_config.get('debug', False)

        # Frame counter for skipping
        self.frame_counter = 0
        self.last_detections = {'phone': [], 'person': []}

        # Initialize YOLOv8 model
        logger.info(f"Loading YOLOv8 model: {model_path}")
        logger.info(f"Phone confidence: {self.phone_confidence}, Person confidence: {self.person_confidence}")
        logger.info(f"Frame skip: {self.frame_skip}, Debug: {self.debug}")
        self.model = YOLO(model_path)

        # COCO dataset class IDs
        self.CLASS_PHONE = 67  # cell phone
        self.CLASS_PERSON = 0  # person

        logger.info("YOLOv8 model loaded successfully")

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

        logger.info(f"Detector initialized at {self.frame_width}x{self.frame_height}")

    def _detect_objects(self, frame: cv2.Mat, force: bool = False) -> Dict[str, List[Tuple[int, int, int, int, float]]]:
        """
        Detect phone, hands, and people in frame using YOLOv8.

        Args:
            frame: Input frame
            force: Force detection even if frame should be skipped

        Returns:
            Dict with 'phone', 'person' keys, each containing list of (x, y, w, h, confidence) tuples
        """
        # Frame skipping for performance (unless forced)
        if not force:
            self.frame_counter += 1
            if self.frame_counter % self.frame_skip != 0:
                # Return cached detections
                return self.last_detections

        # Run YOLOv8 inference with low confidence to catch everything
        # We'll filter by separate thresholds below
        results = self.model(frame, conf=0.1, verbose=False)[0]

        detections = {
            'phone': [],
            'person': []
        }

        # Parse detections
        for box in results.boxes:
            cls_id = int(box.cls[0])
            confidence = float(box.conf[0])

            # Get bounding box coordinates (xyxy format)
            x1, y1, x2, y2 = map(int, box.xyxy[0])

            # Convert to xywh format
            x, y, w, h = x1, y1, x2 - x1, y2 - y1

            if cls_id == self.CLASS_PHONE and confidence >= self.phone_confidence:
                detections['phone'].append((x, y, w, h, confidence))
                if self.debug:
                    logger.info(f"PHONE detected: conf={confidence:.3f}, bbox=({x},{y},{w},{h})")
            elif cls_id == self.CLASS_PERSON and confidence >= self.person_confidence:
                detections['person'].append((x, y, w, h, confidence))
                if self.debug:
                    logger.info(f"PERSON detected: conf={confidence:.3f}, bbox=({x},{y},{w},{h})")

        # Cache detections
        self.last_detections = detections

        if self.debug and not detections['phone']:
            logger.info("No phone detected in this frame")

        return detections

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
        Check if person's hand overlaps with phone and detect person for targeting.

        Returns:
            (hand_touching_phone, face_position, frame) tuple
            - hand_touching_phone: True if person overlaps with detected phone (trigger)
            - face_position: Dict with 'x', 'y' normalized coordinates (0-1) of person center (target), or None
            - frame: Current frame (or None if read failed)
        """
        ret, frame = self.cap.read()
        if not ret:
            logger.warning("Failed to read frame from camera")
            return False, None, None

        # Detect objects
        detections = self._detect_objects(frame)

        # Check if phone detected
        phone_bbox = None
        if detections['phone']:
            # Use highest confidence phone detection
            detections['phone'].sort(key=lambda x: x[4], reverse=True)
            x, y, w, h, conf = detections['phone'][0]
            phone_bbox = (x, y, w, h)
            logger.debug(f"Phone detected at ({x}, {y}, {w}, {h}) with confidence {conf:.2f}")

        # Check for person (hand detection is implicit - person near phone = hand near phone)
        hand_touching_phone = False
        person_position = None

        if detections['person'] and phone_bbox:
            # Check if any person overlaps with phone
            for person_det in detections['person']:
                x, y, w, h, conf = person_det
                person_bbox = (x, y, w, h)

                if self._check_overlap(person_bbox, phone_bbox):
                    hand_touching_phone = True
                    logger.debug("Person touching phone detected!")

                    # Use this person's position for targeting
                    # Target the upper portion (head/face area)
                    person_center_x = (x + w / 2) / self.frame_width
                    person_top_y = (y + h * 0.2) / self.frame_height  # Upper 20% of person bbox

                    person_position = {
                        'x': person_center_x,
                        'y': person_top_y
                    }

                    logger.debug(f"Person/face detected at ({person_position['x']:.3f}, {person_position['y']:.3f})")
                    break

        return hand_touching_phone, person_position, frame

    def get_annotated_frame(self) -> Optional[cv2.Mat]:
        """
        Get a frame with phone and person detection drawn (for calibration/debugging).

        Returns:
            Annotated frame or None if read failed
        """
        ret, frame = self.cap.read()
        if not ret:
            return None

        # Detect objects (force=True to not skip frames during visualization)
        detections = self._detect_objects(frame, force=True)

        # Draw phone detections
        phone_bbox = None
        if detections['phone']:
            for x, y, w, h, conf in detections['phone']:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 3)
                cv2.putText(frame, f"PHONE {conf:.2f}", (x, y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                # Use first phone as the main one
                if phone_bbox is None:
                    phone_bbox = (x, y, w, h)
        else:
            # Show warning if no phone detected
            cv2.putText(frame, "NO PHONE DETECTED",
                       (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        # Draw person detections
        if detections['person']:
            for x, y, w, h, conf in detections['person']:
                # Check if overlapping with phone
                person_bbox = (x, y, w, h)
                is_touching = phone_bbox and self._check_overlap(person_bbox, phone_bbox)
                color = (0, 0, 255) if is_touching else (255, 255, 0)  # Red if touching, cyan if not

                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                cv2.putText(frame, f"PERSON {conf:.2f}", (x, y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

                if is_touching:
                    cv2.putText(frame, "TOUCHING!", (x, y - 35),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

                # Draw target point (upper portion of person)
                target_x = int(x + w / 2)
                target_y = int(y + h * 0.2)
                cv2.drawMarker(frame, (target_x, target_y), (255, 0, 0),
                              cv2.MARKER_CROSS, 20, 2)
                cv2.putText(frame, "TARGET", (target_x - 30, target_y - 20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

        return frame

    def cleanup(self):
        """Release camera resources."""
        self.cap.release()
        logger.info("Detector cleaned up")
