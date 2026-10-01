# GSIP Reference Card v1

The card is A6 portrait: 105 x 148 mm. Print at 100% / Actual Size. The 20 mm scale line must measure 20 mm after printing. The marker is ArUco `DICT_4X4_50`, ID 7, at 36 x 36 mm.

## Patch targets

| Patch        | sRGB          |
| ------------ | ------------- |
| dark soil    | 58, 43, 35    |
| ochre        | 181, 112, 55  |
| clay red     | 154, 70, 55   |
| sand         | 210, 183, 128 |
| leaf         | 76, 112, 63   |
| sky          | 74, 112, 155  |
| white        | 232, 230, 220 |
| black        | 28, 29, 27    |
| neutral gray | 128, 128, 128 |

These values are reproducible digital targets, not claims of spectrophotometric print calibration. Printer, paper, illumination, and camera differences are estimated from the neutral and color patches. The B&W edition is for geometry and exposure support when color printing is unavailable; it cannot provide color calibration.

Generate with `python -m card.generate`. Validate a photograph with `python -m card.validate photo.jpg`.
