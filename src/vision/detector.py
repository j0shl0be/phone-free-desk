import cv2
import logging
import mediapipe as mp
import numpy as np
import time
from typing import Optional, Tuple, Dict, List
from pathlib import Path
from ultralytics import YOLO

logger = logging.getLogger(__name__)


class HandDetector:
    """
    Hybrid detection system:
    - YOLOv8 for phone detection (robust, any phone)
    - MediaPipe Hands for hand detection (precise trigger)
    - MediaPipe Face for face targeting (precise aiming)
    """

    def __init__(self, camera_config: dict, vision_config: dict = None):
        """
        Initialize hybrid detector.

        Args:
            camera_config: Camera configuration dict
            vision_config: Vision configuration dict (optional, for backwards compat)
        """
        self.camera_config = camera_config

        # Handle both old and new API
        if vision_config is None:
            vision_config = {'phone_confidence': 0.3, 'hand_confidence': 0.7, 'face_confidence': 0.7}
        elif isinstance(vision_config, (int, float)):
            # Old API: second param was confidence_threshold
            conf = float(vision_config)
            vision_config = {'phone_confidence': 0.3, 'hand_confidence': conf, 'face_confidence': conf}

        self.vision_config = vision_config

        # Get config values
        model_path = vision_config.get('model', 'yolov8n.pt')
        self.phone_confidence = vision_config.get('phone_confidence', 0.3)
        self.hand_confidence = vision_config.get('hand_confidence', 0.7)
        self.face_confidence = vision_config.get('face_confidence', 0.7)
        self.phone_detection_interval = vision_config.get('phone_detection_interval', 60)
        self.yolo_imgsz = vision_config.get('yolo_imgsz', 320)
        self.debug = vision_config.get('debug', False)
        self.show_timing = vision_config.get('show_timing', False)

        # Phone detection tracking (phone is stationary, rarely update)
        self.frame_counter = 0
        self.last_phone_bbox = None  # Cached phone position
        self.phone_detect_counter = 0  # Force re-detection periodically

        # Initialize YOLOv8 model (for phone detection only)
        logger.info(f"Loading YOLOv8 model: {model_path}")
        logger.info(f"Phone confidence: {self.phone_confidence}")
        logger.info(f"Phone detection interval: every {self.phone_detection_interval} frames (phone is stationary)")
        logger.info(f"YOLOv8 image size: {self.yolo_imgsz} (lower = faster)")
        self.model = YOLO(model_path)
        self.CLASS_PHONE = 67  # cell phone in COCO dataset

        # Initialize MediaPipe Hands
        logger.info(f"Initializing MediaPipe Hands (confidence: {self.hand_confidence})")
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=self.hand_confidence,
            min_tracking_confidence=self.hand_confidence
        )

        # Initialize MediaPipe Face Detection
        logger.info(f"Initializing MediaPipe Face Detection (confidence: {self.face_confidence})")
        self.mp_face = mp.solutions.face_detection
        self.face_detection = self.mp_face.FaceDetection(
            min_detection_confidence=self.face_confidence
        )

        logger.info(f"Debug: {self.debug}, Show timing: {self.show_timing}")

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

    def _detect_phone(self, frame: cv2.Mat, force: bool = False) -> Optional[Tuple[int, int, int, int]]:
        """
        Detect phone using YOLOv8.

        Phone is stationary, so we cache detection and only re-run occasionally.

        Args:
            frame: Input frame
            force: Force detection even if cached

        Returns:
            (x, y, w, h) bounding box or None if no phone detected
        """
        # Check if we should re-detect phone (unless forced)
        if not force:
            self.phone_detect_counter += 1

            # Return cached phone position if available and not expired
            if self.last_phone_bbox is not None and self.phone_detect_counter < self.phone_detection_interval:
                return self.last_phone_bbox

            # Reset counter and re-detect
            self.phone_detect_counter = 0

        # Run YOLOv8 inference with smaller image size for speed
        if self.show_timing:
            start_time = time.time()

        results = self.model(frame, conf=0.1, verbose=False, imgsz=self.yolo_imgsz)[0]

        if self.show_timing:
            yolo_time = (time.time() - start_time) * 1000
            logger.info(f"YOLOv8 inference: {yolo_time:.1f}ms (cached for {self.phone_detection_interval} frames)")

        phone_detections = []

        # Parse detections
        for box in results.boxes:
            cls_id = int(box.cls[0])
            confidence = float(box.conf[0])

            if cls_id == self.CLASS_PHONE and confidence >= self.phone_confidence:
                # Get bounding box coordinates (xyxy format)
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                # Convert to xywh format
                x, y, w, h = x1, y1, x2 - x1, y2 - y1
                phone_detections.append((x, y, w, h, confidence))

                if self.debug:
                    logger.info(f"PHONE detected: conf={confidence:.3f}, bbox=({x},{y},{w},{h})")

        if self.debug and not phone_detections:
            logger.info("No phone detected in this frame")

        # Cache and return highest confidence phone
        if phone_detections:
            phone_detections.sort(key=lambda x: x[4], reverse=True)
            x, y, w, h, conf = phone_detections[0]
            self.last_phone_bbox = (x, y, w, h)
            return (x, y, w, h)

        # No phone found - clear cache
        self.last_phone_bbox = None
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
        if self.show_timing:
            frame_start = time.time()

        ret, frame = self.cap.read()
        if not ret:
            logger.warning("Failed to read frame from camera")
            return False, None, None

        # Detect phone using YOLOv8
        if self.show_timing:
            phone_start = time.time()
        phone_bbox = self._detect_phone(frame)
        if self.show_timing:
            phone_time = (time.time() - phone_start) * 1000

        # Convert BGR to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Detect hands using MediaPipe
        if self.show_timing:
            hand_start = time.time()
        hand_results = self.hands.process(rgb_frame)
        if self.show_timing:
            hand_time = (time.time() - hand_start) * 1000

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
                    if self.debug:
                        logger.info("HAND touching phone detected!")

        # Detect face using MediaPipe (for targeting)
        if self.show_timing:
            face_start = time.time()
        face_results = self.face_detection.process(rgb_frame)
        if self.show_timing:
            face_time = (time.time() - face_start) * 1000

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

            if self.debug:
                logger.info(f"FACE detected at ({face_position['x']:.3f}, {face_position['y']:.3f})")

        if self.show_timing:
            total_time = (time.time() - frame_start) * 1000
            logger.info(f"Frame timing: Phone={phone_time:.1f}ms, Hand={hand_time:.1f}ms, Face={face_time:.1f}ms, Total={total_time:.1f}ms")

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

        # Detect phone using YOLOv8 (force=True to not skip frames during visualization)
        phone_bbox = self._detect_phone(frame, force=True)

        if phone_bbox:
            x, y, w, h = phone_bbox
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 3)
            cv2.putText(frame, "PHONE (cached)", (x, y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        else:
            # Show warning if no phone detected
            cv2.putText(frame, "NO PHONE DETECTED",
                       (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        # Convert BGR to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Draw hand landmarks and bounding boxes using MediaPipe
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

        # Draw face detections using MediaPipe
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
        logger.info("Detector cleaned up")
