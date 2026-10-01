from __future__ import annotations

import argparse
from io import BytesIO
from pathlib import Path

import cv2
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from card.design import (
    CARD_HEIGHT_MM,
    CARD_WIDTH_MM,
    MARKER_ID,
    MARKER_SIZE_MM,
    MARKER_X_MM,
    MARKER_Y_MM,
    PATCHES,
    grayscale,
)


def marker_png() -> bytes:
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    marker = cv2.aruco.generateImageMarker(dictionary, MARKER_ID, 720)
    ok, encoded = cv2.imencode(".png", marker)
    if not ok:
        raise RuntimeError("Could not encode ArUco marker")
    return encoded.tobytes()


def top_y(y_mm: float, height_mm: float = 0) -> float:
    return float((CARD_HEIGHT_MM - y_mm - height_mm) * mm)


def draw_card(path: Path, *, monochrome: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(
        str(path),
        pagesize=(CARD_WIDTH_MM * mm, CARD_HEIGHT_MM * mm),
        pageCompression=1,
        invariant=1,
    )
    pdf.setTitle("GSIP Reference Card v1")
    pdf.setAuthor("Global Soil Intelligence Project")
    pdf.setStrokeColorRGB(0, 0, 0)
    pdf.setLineWidth(0.35)
    pdf.rect(3 * mm, 3 * mm, 99 * mm, 142 * mm)

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(8 * mm, top_y(8), "GSIP REFERENCE CARD v1")
    pdf.setFont("Helvetica", 6.5)
    pdf.drawString(8 * mm, top_y(14), "Print at 100% / Actual Size. Keep the whole card in frame.")
    pdf.drawString(8 * mm, top_y(18), "Open soil estimate protocol - globalsoilintelligence.com")

    marker = ImageReader(BytesIO(marker_png()))
    pdf.drawImage(
        marker,
        MARKER_X_MM * mm,
        top_y(MARKER_Y_MM, MARKER_SIZE_MM),
        MARKER_SIZE_MM * mm,
        MARKER_SIZE_MM * mm,
        mask="auto",
    )
    pdf.setFont("Helvetica-Bold", 6)
    pdf.drawCentredString(26 * mm, top_y(64), f"ARUCO 4x4 / ID {MARKER_ID}")

    for patch in PATCHES:
        rgb = grayscale(patch.rgb) if monochrome else patch.rgb
        pdf.setFillColorRGB(*(channel / 255 for channel in rgb))
        pdf.rect(
            patch.x_mm * mm,
            top_y(patch.y_mm, patch.size_mm),
            patch.size_mm * mm,
            patch.size_mm * mm,
            fill=1,
            stroke=1,
        )
        pdf.setFillColorRGB(0, 0, 0)
        pdf.setFont("Helvetica", 4.7)
        pdf.drawCentredString(
            (patch.x_mm + patch.size_mm / 2) * mm,
            top_y(patch.y_mm + patch.size_mm + 2.3),
            patch.name.replace("_", " ").upper(),
        )

    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(8 * mm, top_y(81), "THREE QUICK SHOTS")
    pdf.setFont("Helvetica", 7)
    reminders = (
        "A  CONTEXT - undisturbed surface, about 30 cm away",
        "B  FRESH FACE - scrape 2-3 cm, card + soil, about 15 cm",
        "C  TEXTURE (optional) - moist soil ball or ribbon in hand",
        "Avoid shadows and glare. Do not cover the marker or patches.",
        "This produces a probabilistic estimate, not a laboratory result.",
    )
    for index, line in enumerate(reminders):
        pdf.drawString(8 * mm, top_y(88 + index * 7), line)

    pdf.setLineWidth(0.7)
    pdf.line(8 * mm, top_y(129), 28 * mm, top_y(129))
    pdf.setFont("Helvetica", 6)
    pdf.drawString(8 * mm, top_y(133), "20 mm print-scale check")
    pdf.drawRightString(97 * mm, top_y(137), "CC BY-SA 4.0 card artwork")
    pdf.showPage()
    pdf.save()


def generate(output_dir: Path) -> tuple[Path, Path]:
    color = output_dir / "gsip-reference-card-v1-color.pdf"
    monochrome = output_dir / "gsip-reference-card-v1-bw.pdf"
    draw_card(color, monochrome=False)
    draw_card(monochrome, monochrome=True)
    return color, monochrome


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate deterministic GSIP A6 reference cards")
    parser.add_argument("--output-dir", type=Path, default=Path("output/pdf"))
    args = parser.parse_args()
    for path in generate(args.output_dir):
        print(path)


if __name__ == "__main__":
    main()
