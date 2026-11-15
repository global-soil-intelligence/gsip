"""Generate the print file for a GSIP Node Card run. Deterministic for a given run code."""

from __future__ import annotations

import argparse
from io import BytesIO
from pathlib import Path

import cv2
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from card.design import grayscale
from card.node_design import (
    ALL_PATCHES,
    CARD_HEIGHT_MM,
    CARD_WIDTH_MM,
    MARKER_ID,
    MARKER_SIZE_MM,
    MARKER_X_MM,
    MARKER_Y_MM,
    SCALE_LENGTH_MM,
    SCALE_X_MM,
    SCALE_Y_MM,
    TEXT_BASELINE_MM,
    UNCHARACTERISED_RUN,
    check_run_code,
)


def marker_png() -> bytes:
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    marker = cv2.aruco.generateImageMarker(dictionary, MARKER_ID, 720)
    ok, encoded = cv2.imencode(".png", marker)
    if not ok:
        raise RuntimeError("Could not encode ArUco marker")
    return encoded.tobytes()


def _top(y_mm: float, height_mm: float = 0) -> float:
    return float((CARD_HEIGHT_MM - y_mm - height_mm) * mm)


def draw_node_card(path: Path, *, run: str, monochrome: bool = False) -> None:
    run = check_run_code(run)
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(
        str(path),
        pagesize=(CARD_WIDTH_MM * mm, CARD_HEIGHT_MM * mm),
        pageCompression=1,
        invariant=1,
    )
    pdf.setTitle(f"GSIP Node Card v1 run {run}")
    pdf.setAuthor("Global Soil Intelligence Project")
    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont("Helvetica-Bold", 7.5)
    pdf.drawString(MARKER_X_MM * mm, _top(6.2), "GSIP NODE CARD v1")
    pdf.setFont("Helvetica", 4.6)
    pdf.drawRightString(
        80.5 * mm, _top(6.2), "Keep the whole card flat, in frame, beside the soil."
    )

    marker = ImageReader(BytesIO(marker_png()))
    pdf.drawImage(
        marker,
        MARKER_X_MM * mm,
        _top(MARKER_Y_MM, MARKER_SIZE_MM),
        MARKER_SIZE_MM * mm,
        MARKER_SIZE_MM * mm,
        mask="auto",
    )

    pdf.setStrokeColorRGB(0, 0, 0)
    pdf.setLineWidth(0.25)
    for patch in ALL_PATCHES:
        rgb = grayscale(patch.rgb) if monochrome else patch.rgb
        pdf.setFillColorRGB(*(channel / 255 for channel in rgb))
        pdf.rect(
            patch.x_mm * mm,
            _top(patch.y_mm, patch.height_mm),
            patch.width_mm * mm,
            patch.height_mm * mm,
            fill=1,
            stroke=1,
        )

    pdf.setFillColorRGB(0, 0, 0)
    pdf.setLineWidth(0.6)
    pdf.line(
        SCALE_X_MM * mm,
        _top(SCALE_Y_MM),
        (SCALE_X_MM + SCALE_LENGTH_MM) * mm,
        _top(SCALE_Y_MM),
    )
    pdf.setFont("Helvetica", 4.2)
    pdf.drawString(SCALE_X_MM * mm, _top(TEXT_BASELINE_MM), "20 mm")
    pdf.drawString(
        30 * mm, _top(SCALE_Y_MM), "An estimate with uncertainty, not a laboratory result."
    )
    pdf.drawString(30 * mm, _top(TEXT_BASELINE_MM), "Card artwork CC BY-SA 4.0")
    pdf.setFont("Helvetica-Bold", 4.6)
    pdf.drawRightString(80.5 * mm, _top(TEXT_BASELINE_MM), f"RUN {run}")
    pdf.showPage()
    pdf.save()


def generate_node(output_dir: Path, run: str = UNCHARACTERISED_RUN) -> tuple[Path, Path]:
    run = check_run_code(run)
    color = output_dir / f"gsip-node-card-v1-{run}-color.pdf"
    monochrome = output_dir / f"gsip-node-card-v1-{run}-bw.pdf"
    draw_node_card(color, run=run, monochrome=False)
    draw_node_card(monochrome, run=run, monochrome=True)
    return color, monochrome


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a GSIP node card print file for one run")
    parser.add_argument("--run", default=UNCHARACTERISED_RUN)
    parser.add_argument("--output-dir", type=Path, default=Path("output/pdf"))
    args = parser.parse_args()
    for path in generate_node(args.output_dir, args.run):
        print(path)


if __name__ == "__main__":
    main()
