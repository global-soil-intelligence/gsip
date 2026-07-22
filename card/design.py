from dataclasses import dataclass

CARD_WIDTH_MM = 105.0
CARD_HEIGHT_MM = 148.0
MARKER_ID = 7
MARKER_X_MM = 8.0
MARKER_Y_MM = 25.0
MARKER_SIZE_MM = 36.0


@dataclass(frozen=True)
class Patch:
    name: str
    rgb: tuple[int, int, int]
    x_mm: float
    y_mm: float
    size_mm: float = 13.0


PATCHES = (
    Patch("dark_soil", (58, 43, 35), 52, 24),
    Patch("ochre", (181, 112, 55), 68, 24),
    Patch("clay_red", (154, 70, 55), 84, 24),
    Patch("sand", (210, 183, 128), 52, 41),
    Patch("leaf", (76, 112, 63), 68, 41),
    Patch("sky", (74, 112, 155), 84, 41),
    Patch("white", (232, 230, 220), 52, 58),
    Patch("black", (28, 29, 27), 68, 58),
    Patch("neutral_gray", (128, 128, 128), 84, 58),
)


def grayscale(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    value = round(0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2])
    return (value, value, value)
