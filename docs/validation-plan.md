# Validation plan: first test with a real print and real phones

**Status: proposed (WP-COLLECT-6). Nothing in this plan has been run.** Every number GSIP has
about its reference cards and colour normalisation comes from generated photographs. This is the
plan for the first test with a printed card, real phones and real light.

It is a bench test by the project owner or an invited helper, on their own soil samples, with
files kept on their own machine. It collects no contributor data, opens no hosted capture and
needs no production system.

## The question

When the [standard capture procedure](capture-protocol.md) is followed, do different phones and
different diffuse light give the same normalised colour for the same soil, and how much worse is
it when the procedure is not followed?

What this test cannot show: a phone photograph is an RGB observation, not a spectrum, and the
test produces no soil-property estimate. Repeatable colour is a precondition for later work, not
evidence that any soil property can be read from a photo.

## What to prepare

| Item              | Minimum                                                                                                 |
| ----------------- | ------------------------------------------------------------------------------------------------------- |
| Phones            | 3, from at least 2 makers and both major operating systems; note make, model and OS version by hand     |
| GSIP cards        | The A6 colour card from 2 different printers, and 1 home-printed node card; label each print            |
| Judge card        | 1 commercial 24-patch colour card with its maker's reference values (see the [field kit](field-kit.md)) |
| Prepared samples  | 6 air-dried, 2 mm sieved soils chosen to differ: dark, pale, red, yellow-brown, sandy, clayey           |
| Controls          | The grey card as a "sample" with a known neutral colour; one tray photographed with no card at all      |
| Field profile     | 1 cleaned face, if a safe one with permission is available; otherwise leave part B out and say so       |
| The rest of a kit | Tray, distance guide, shade, diffuser, one indoor lamp                                                  |

Before any photo, measure the 20 mm line on every print and write down what it measures.

## Part A: prepared samples

Follow procedure (a). For every combination below take **3 photos**, resetting the phone and
turning the tray a quarter turn between photos. Each photo has the soil tray, one GSIP card and
the judge card, all in one plane.

| Factor | Levels                                                                                        |
| ------ | --------------------------------------------------------------------------------------------- |
| Sample | 6 soils and the grey-card control                                                             |
| Phone  | 3                                                                                             |
| Light  | Open shade, overcast sky, diffuser in sun, indoor lamp, and **direct sun** as the bad case    |
| Card   | A6 print 1 for the full set. Repeat one phone and one light with A6 print 2 and the node card |

Full set: 7 samples × 3 phones × 5 lights × 3 photos = 315 photos. Card comparison: 7 samples ×
2 extra cards × 3 photos = 42 photos. One no-card photo per phone: 3. About 360 photos.

Then break the rules one at a time, on one phone, one soil, in open shade, 3 photos each:
automatic white balance; automatic exposure; HDR on; flash on; a filter on; camera tilted about
30°; distance halved; distance doubled; card tilted about 20° out of the soil's plane; card
half in sun; a finger on one patch. That is 33 photos.

## Part B: field profile

Follow procedure (b) on one face: 3 phones × 2 lights (shaded, and unshaded as the bad case) ×
3 photos × 2 distances (30 cm section, 100 cm whole face) = 36 photos.

## Record for every photo

File name, phone, card print, sample, light, procedure, distance, the ticks from the capture
checklist, and the time. Keep photos and the sheet in a private folder outside the repository.
Keep people, faces, documents and house numbers out of every frame. Record no location.

## How to score

Run each photo through `pipeline.qa_cards.evaluate_photo_with_cards` on your own machine and
keep its private colour record. Colour differences are CIE76 in CIELAB (D65), the measure the
pipeline already uses; report CIEDE2000 beside it if you can.

Two things the pipeline does not do for you, so do them by hand and say how:

- **Soil colour.** The pipeline's own soil colour is the median of everything near the card that
  is not a card. With a tray and a judge card in the frame that includes background. For this
  test, take the median of a fixed square inside the tray instead, and apply the photo's fitted
  normalisation to it with `pipeline.colour_correction.apply`.
- **Judge card patches.** No GSIP code finds a commercial card. Take the median of a fixed
  square inside each of its patches the same way.

A short script that does both from hand-marked corners is part of running this plan and does not
exist yet.

1. **Detection.** For each card print, phone and light: the share of photos where exactly one
   card was found and read, the share refused, and the share where no card was found. The
   no-card photos must come back `uncalibrated`.
2. **Fit.** The share marked `normalised`, and the spread of the leave-one-patch-out residual,
   by phone and light.
3. **Repeatability** (same phone, same light, same sample): the mean colour difference between
   each of the 3 photos and their average, before and after normalisation. This is the floor:
   nothing across phones can be better than it.
4. **Across phones** (same light, same sample): the mean pairwise colour difference between the
   3 phones' averages, before and after normalisation.
5. **Across light** (same phone, same sample): the same, between the four diffuse lights.
   Report direct sun separately.
6. **Against the judge card.** Apply each photo's fitted normalisation to the judge card's
   patches, which the fit never saw, and compare with the maker's reference values. This is the
   only score that speaks to accuracy and not just agreement. Report it per patch.
7. **Between prints.** The same soil, phone and light with the three GSIP cards: how far apart
   are the normalised colours? That is the cost of unmeasured prints.
8. **Broken rules.** For each broken rule, the change in scores 3, 4 and 6 from the unbroken
   case, and whether the card reader refused the photo.
9. **Determinism.** Run every photo twice. `pipeline.capture_acquisition.calibration_digest`
   must be identical both times, on the same machine. Then run a sample of 20 on a second
   machine and report whether the digests match.

Report medians and 90th percentiles, with counts, in one table per score. Report every photo
taken, including the ones that went badly.

## What would count as good enough

Written down before the test so the result cannot move the target. All four are provisional
proposals for the owner to set.

- After normalisation, the across-phone difference (score 4) has a median of at most 5 and is at
  least half the size it was before normalisation.
- Repeatability (score 3) has a median of at most 2.
- Under the four diffuse lights, at least 90 % of photos with a whole, flat, unobstructed card
  are read.
- Direct sun and each broken rule are measurably worse on score 4 or 6, or are refused. If a
  broken rule makes no difference, the rule is not earning its place and should be questioned.

If the first target fails, the honest conclusion is that card-referenced phone photos are not
yet comparable across phones, and the thresholds in
[SPEC §17.3](SPEC.md#173-colour-normalisation) must not be relied on.

## What stays unknown after this test

- Any link between colour and a soil property. No laboratory value is involved.
- Behaviour on phones, printers, papers and soils that were not in the test.
- Moist and wet soil, unless they are added as samples.
- The true colours of the GSIP prints. That needs an instrument measurement of a print, which
  this plan does not include. If a spectrophotometer can be borrowed, measure each print's
  patches and report them: that single addition would turn score 7 from a comparison into a
  correction.
- Whether the three papers cited in the capture procedure recommend anything this plan omits.
  Read them and amend the procedure before the test, not after.

## Reporting back

Open a pull request that adds the summary tables and the method as run to this file, under a
new heading with the date. Do not add photos, file names that name a place, or the per-photo
sheet. Update the README's "Where the science stands" to say what was tested and what was found.
