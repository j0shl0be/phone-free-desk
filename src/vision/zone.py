import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PhoneZone:
    """Represents the phone detection zone in the camera frame."""

    # Normalized coordinates (0-1)
    x: float
    y: float
    width: float
    height: float

    @classmethod
    def from_config(cls, config: dict):
        """Create PhoneZone from config dict."""
        return cls(
            x=config['x'],
            y=config['y'],
            width=config['width'],
            height=config['height']
        )

    def get_pixel_coords(self, frame_width: int, frame_height: int) -> tuple:
        """
        Convert normalized coordinates to pixel coordinates.

        Returns:
            (x1, y1, x2, y2) in pixels
        """
        x1 = int(self.x * frame_width)
        y1 = int(self.y * frame_height)
        x2 = int((self.x + self.width) * frame_width)
        y2 = int((self.y + self.height) * frame_height)
        return (x1, y1, x2, y2)

    def contains_point(self, x: float, y: float) -> bool:
        """
        Check if a normalized point (0-1) is inside the zone.

        Args:
            x: Normalized x coordinate (0-1)
            y: Normalized y coordinate (0-1)

        Returns:
            True if point is inside zone
        """
        return (
            self.x <= x <= (self.x + self.width) and
            self.y <= y <= (self.y + self.height)
        )

    def contains_pixel_point(self, px: int, py: int, frame_width: int, frame_height: int) -> bool:
        """
        Check if a pixel coordinate is inside the zone.

        Args:
            px: Pixel x coordinate
            py: Pixel y coordinate
            frame_width: Frame width in pixels
            frame_height: Frame height in pixels

        Returns:
            True if point is inside zone
        """
        # Normalize pixel coordinates
        norm_x = px / frame_width
        norm_y = py / frame_height
        return self.contains_point(norm_x, norm_y)
