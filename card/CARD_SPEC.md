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

# GSIP Node Card v1

A credit-card-size edition for people who order a printed card. It is optional. The free A6 card above stays the way in, and nobody has to buy anything to contribute.

**Do not use a node card in a submission yet.** The capture pipeline does not recognise it. A node card in a submitted photo is counted as soil: its marker and patches enter the sharpness, exposure and duplicate checks, and the photo is marked uncalibrated. That changes only when a separate package teaches the pipeline to find it.

The card is ISO ID-1 (CR80) landscape: 85.6 x 53.98 mm. The marker is ArUco `DICT_4X4_50`, ID 12, at 24 x 24 mm, with a light border at least 4 mm wide. ID 12 differs from the A6 card's ID 7, so a detector knows which layout it sees. Unlike IDs 8, 9, 17 and 47, it does not read as itself in a mirror, so a mirrored photo is refused.

## What is on it

- The same nine colour patches as the A6 card, same names and values, at 10 x 10 mm.
- A five-step neutral ramp, `ramp_0` to `ramp_4`, at sRGB 28, 78, 128, 180 and 232 on all three channels. Three steps repeat the black, grey and white patches, so a reading can be checked against itself. The other two add tones the A6 card lacks. Five printed greys of unmeasured reflectance are a guide to the photo's tone curve, not a measurement of it.
- A 20 mm scale line.
- A run code, such as `RUN AB12-0001`.

## Print requirements

| Requirement                                   | Why                                                                          |
| --------------------------------------------- | ---------------------------------------------------------------------------- |
| Matte finish                                  | A glossy card throws glare outdoors and spoils the reference                 |
| Opaque white stock                            | Clear or frosted stock lets the soil show through the patches                |
| 100% scale, no fit-to-page                    | The 20 mm line must measure 20 mm                                            |
| One printer and one setup for a run           | Two printers make two different cards                                        |
| The run code printed on every card in the run | It ties a card to its run's measured colours, once the run has been measured |

## What a run code is, and is not

A run code names a print run. Every card in the run carries the same code. The format is two capital letters, two digits, a dash and four digits; `HOME-0000` alone is reserved for a card nobody has characterised.

The format has no room for an e-mail address or a full name. It cannot stop someone choosing initials and a year, or numbering cards one by one. Whoever orders a run must give every card in it the same code, and must not issue a code to one person.

Card photos can be published, so a code links the observations of everyone who holds a card from that run. A small run, such as one household or one class, narrows that to a few people. Runs should be large and spread across unrelated holders. No minimum is enforced.

## What the detector refuses

`card.node_validate` refuses a photograph, without returning any colours, when:

- the node card's marker is not found exactly once, or the photograph is mirrored;
- the marker is less than 125 pixels on a side;
- any corner of the card, or any patch window, lies outside the photograph;
- a patch is not one flat colour, for example when a finger or the edge of a glare patch crosses it;
- the neutral ramp is out of order;
- a patch and the ramp step printed with nearly the same value differ by much more or less than they should, which also refuses strongly uneven light;
- any channel of any patch reads 0 or 255, because the photograph is too dark or too bright there.

It does not detect an even cover of one colour on the eight patches nothing repeats: the six colours and ramp steps 1 and 3. On the three repeated pairs it does not detect a cover within about 30 levels of the patch's own colour, such as pale skin over white. A speck over less than about a tenth of a patch window is ignored.

## Limits

- The patch values are digital targets, as for the A6 card. A run is characterised only when at least one card from it has been measured with an instrument, and one card says nothing about variation within the run. Until then a node card is no better known than a home print.
- No run has been printed or measured. No printer is chosen.
- One small marker locates the whole card, so the far corners carry the most error. The narrowest patch inset is 1.85 percent of the card's width. In synthetic photographs, cards accepted with a marker of 100 to 118 pixels had far corners off by up to 2.8 percent, though no wrong reading was seen. The limit is therefore 125 pixels, a card about 446 pixels wide seen square-on. At 560 pixels the corners are within 1.5 percent, and at 900 pixels within 0.8 percent.
- The 12-level flatness limit and the 30-level repeat limit come from synthetic photographs. A real print and a real phone will need them set again.
- `card.node_validate` reads the patches as photographed and reports the image scale at the middle of the card along its width and its height. It applies no colour correction.
- Tested on synthetic photographs only. No printed card and no phone was used.

## Open questions for the printer package

The print file is RGB, has no bleed and no corner-radius allowance, and uses text as small as 4.2 pt. Card printers commonly ask for CMYK, 3 mm of bleed and a 3 to 5 mm safe area, and plastic card printing is often glossy. None of that has been checked with a printer.

Generate with `python -m card.node_generate --run AB12-0001`. Read a photograph with `python -m card.node_validate photo.jpg`.
