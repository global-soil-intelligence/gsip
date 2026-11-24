# Field kit for standard soil photographs

**Status: proposed (WP-COLLECT-6).** A list, not a product: GSIP sells no kit and has chosen no
supplier. Nobody needs a kit to contribute ([SPEC §17.1, K4](SPEC.md#171-rules-added)). The kit
only makes the [standard capture procedure](capture-protocol.md) easy to follow. No item here
has been bought or tried for this document.

A phone photograph taken with this kit is still an RGB observation, not a spectrum, and the kit
yields no soil-property estimate.

## Prices

**Every price below is an estimate** in US dollars, written in November 2026, and will be wrong
somewhere. Only the commercial colour card was looked up, in a handful of online listings on
23 November 2026; the other figures are rough guesses for ordinary household or hardware-shop
items and were not checked. Check a real price before you budget.

## Low-cost kit

| Item                | What to get                                                                                       | Why                                                             | Estimate         |
| ------------------- | ------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- | ---------------- |
| Printed colour card | The GSIP A6 card or the node card, printed at 100 % on matte, opaque white paper or card stock    | The colour reference in every photo (rule 7)                    | Under $1 at home |
| Grey card           | A matte neutral grey card, about 18 % grey, at least 10 × 15 cm                                   | To lock exposure and white balance before the first photo       | $5–15            |
| Shade or diffuser   | A plain white or black umbrella, a tarp, or a white translucent diffuser panel about 60 cm across | Diffuse, even light on soil and card together (rule 1)          | $0–25            |
| Distance guide      | A 30 cm stick, dowel or folded rule, cut or marked once and used for every photo                  | The same distance every time (rule 3)                           | $0–5             |
| Sample tray         | A shallow, matte, dark or neutral tray, about 10 × 10 cm and at least 1 cm deep                   | One fixed sample shape and depth for prepared samples           | $2–10            |
| 2 mm sieve          | A sieve with a stated 2 mm opening                                                                | Prepared samples are sieved to 2 mm                             | $10–25           |
| Straight edge       | A ruler or a card with a clean edge                                                               | To level the tray without pressing the soil                     | $0–3             |
| Scale               | A tape or ruler with millimetre marks                                                             | Scale on a profile face; to check the card printed at true size | $0–5             |
| Pins or clips       | Four plain pins or two clips                                                                      | To hold the card flat against a profile face                    | $0–3             |
| Knife or trowel     | Any clean blade                                                                                   | To cut back a profile face                                      | $0–10            |

Estimated total: roughly $20 to $100, depending on what you already own. That range is a sum of
the guesses above, not a quote.

### About the printed card

- **Published reference values.** The patch values for both GSIP cards are published in
  [CARD_SPEC.md](../card/CARD_SPEC.md) and in `card/design.py` and `card/node_design.py`.
- **They are digital targets.** They are the sRGB numbers sent to the printer, not measurements
  of your print. Two printers make two different cards. Until a print has been measured with an
  instrument, a home print brings different phones and lights toward a common scale and adds an
  unknown error of its own.
- **Print rules.** Matte finish, opaque stock, 100 % scale with no "fit to page". The 20 mm
  scale line must measure 20 mm. Replace a card that is faded, stained, creased or wet.
- **Card ID and version.** The acquisition record names the card as `gsip-a6` or `gsip-node`,
  version `v1`. It does not record the node card's print-run code, which could link people who
  share a run ([SPEC §17.2](SPEC.md#172-two-card-editions)).
- **Which card.** The A6 card is easier to print at home. The node card has a five-step grey
  ramp and refuses more bad readings. Use one card per photo.

### About the grey card

The grey card is for setting the camera, not for the photo: fill the frame with it in the light
you will use, lock exposure and white balance, then put it away. A grey card left in the photo
is not read by GSIP.

## High-quality option: a commercial colour card

A manufactured colour reference target, such as the 24-patch Calibrite ColorChecker Classic
(formerly sold by X-Rite), in place of the printed card.

| Item                                  | Why                                                                         | Estimate                  |
| ------------------------------------- | --------------------------------------------------------------------------- | ------------------------- |
| 24-patch commercial colour target     | Pigmented patches made to a tolerance, with reference values from its maker | About $90–160 (see below) |
| Smaller "passport" or "mini" versions | Easier to hold flat against a profile face                                  | About $110–130            |

The $90–160 range is what a few United States listings showed on 23 November 2026 for the
full-size chart; other countries and other days differ. It is an estimate.

Limits, stated plainly:

- **GSIP's software does not read a commercial card.** The pipeline detects only the two GSIP
  cards, by their printed markers. A photo with only a commercial card is `uncalibrated` in GSIP
  today. Reading one is a separate, unbuilt package.
- **Its first use here is as a judge, not as the reference.** In the
  [validation plan](validation-plan.md) the commercial card sits beside the GSIP card as a set of
  known colours the normalisation was not fitted to.
- **Use the maker's own reference values** for your chart's production period, from the maker.
  Values copied from elsewhere may describe an older formulation. None are reproduced here.
- A commercial card is a colour reference for a camera. It does not turn a phone into an
  instrument: the result is still three colour channels, not a spectrum.
- Keep it clean, dry and out of the sun between uses, and replace it at the age its maker gives.

## Not in the kit

No spectrometer, no lamp with a certified output and no measured print run. Those belong to
instrument records ([soil library guide](SOIL_LIBRARY.md)), which GSIP keeps separate from
camera records.
