# Smartphone-only soil observations and an on-screen guide

Research and proposal, 2026-10-16. Source reviewed at merged main `33260db1ce49c50600942694e43269759e554e66`. This report changes no source, measurement protocol, account, production service or upload gate.

## Recommendation

Make participation start with a phone, with the printed card clearly optional. Use an on-screen outline to help framing; keep that outline separate from the captured image. Save phone photographs and declared context as unverified observations, and keep measured spectra, reconstructed spectra and laboratory evidence distinct.

This fits GSIP's existing policy. The gap is chiefly presentation and capture guidance, plus the distinction between an ordinary observation and an explicitly registered library sample. A digital reference graphic cannot supply the scene information observed by photographing a physical target. That conclusion is an inference from the image-formation model, which depends on illumination, material reflectance and camera response. [Nixon et al., 2020](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0230561)

## What the repository actually does

- [SPEC §5](https://github.com/global-soil-intelligence/gsip/blob/33260db1ce49c50600942694e43269759e554e66/docs/SPEC.md#L108) requires photos A and B, describes a card in both, then explicitly accepts missing cards as uncalibrated at line 118. The instructions can therefore make printing feel mandatory even though the acceptance policy does not.
- [QA](https://github.com/global-soil-intelligence/gsip/blob/33260db1ce49c50600942694e43269759e554e66/pipeline/qa.py#L580) does not fail a photo solely for a missing card: the detection check passes with score zero and records uncalibrated status. Without a located card, the candidate region is the whole frame. A sharp cardless synthetic fixture already passes. The independent source audit executed 11 existing QA/optics/schema cases successfully.
- [The current form guide](https://github.com/global-soil-intelligence/gsip/blob/33260db1ce49c50600942694e43269759e554e66/apps/capture-pwa/src/App.tsx#L145) is static CSS, outside the system camera/picker. There is no app-controlled live camera preview.
- [Library optical records](https://github.com/global-soil-intelligence/gsip/blob/33260db1ce49c50600942694e43269759e554e66/pipeline/phone_optics.py#L27) remain `camera_rgb`, with uncalibrated status even when a card is detected. Real field-photo feature extraction is separately held pending privacy integration.
- [The printed card specification](https://github.com/global-soil-intelligence/gsip/blob/33260db1ce49c50600942694e43269759e554e66/card/CARD_SPEC.md#L19) describes digital sRGB targets, without a claim of spectrophotometric print calibration. Printer, paper and lighting vary. Legacy QA's “calibrated” field means successful photographed-patch processing; SPEC L3 expressly says card detection alone does not certify reflectance calibration.
- [Library registration](https://github.com/global-soil-intelligence/gsip/blob/33260db1ce49c50600942694e43269759e554e66/apps/capture-pwa/src/LibrarySection.tsx#L74) is opt-in and requires declared depth bounds. SPEC §16.5 forbids inferred/defaulted depth. A photo submission does not automatically create a library sample; a phone namespace also does not enroll a federation peer.
- QA currently has no learned soil classifier in its worker. Passing sharpness/exposure checks is not proof that pixels depict soil. All new pilot records remain private and unverified, with publication/field training held.

## What each option provides

| Option | Useful contribution | Honest limit |
| --- | --- | --- |
| Phone photos without a card | Appearance, surface/condition/context, repeated observations and links to a later sample record | Uncalibrated camera evidence; cross-device color, physical scale and wavelengths are not established |
| Phone photos with a physical target | Better geometric reference and support for color/exposure normalization | An ordinary print still needs empirical validation; card detection supplies no traceable full-spectrum measurement |
| SVG/HTML guide over a camera preview | Framing, composition and step-by-step assistance | A screen graphic is not an observed calibration target |
| RAW flash/no-flash research | A candidate approach to more reproducible color measurements on supported devices | Requires device/control qualification; not universal browser functionality |
| A paired instrument/laboratory record | Wavelength-resolved measurement and independently characterized reference labels | Requires actual sample linkage, instrument context, rights and verification |

A single phone image contains three broad color channels. Additional AI-generated bands are estimates and must retain that identity. None of these photographs alone identifies biological composition. This is already reflected in GSIP L1–L4. Spectral recovery remains an underdetermined inverse problem requiring assumptions and validation. [Huo et al.](https://arxiv.org/html/2304.02162v2)

## Scientific evidence and limits

1. **Soil-specific smartphone study.** Gupta et al. used physical plastic reference panels characterized by a laboratory spectrometer, then modeled soil properties from calibrated RGB and synthetic features. The study supports a research path, without establishing virtual-card calibration or global accuracy. [2023 paper](https://www.sciencedirect.com/science/article/pii/S2772375523001569)

2. **Reference plates improve consistency without guaranteeing accuracy.** Li et al. found reduced variation between phones/lighting, while bias in actual soil measurements was not consistently removed. This supports keeping a physical target as an optional higher-control method. [2025 paper](https://www.mdpi.com/2571-8789/9/3/93)

3. **Card-free routine capture has a qualified precedent.** Nixon et al. used RAW flash/no-flash pairs with fixed ISO/exposure after one-time physical color/grey-target calibration for each device. It does not establish a zero-calibration, soil-validated method on arbitrary browsers. [2020 paper](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0230561)

4. **Device and encoding differences matter.** SPECTACLE reports substantial consumer-camera variation and distinguishes RAW/JPEG response. Device-independent color cannot be assumed from the image file alone. [Burggraaff et al., 2019](https://doi.org/10.1364/OE.27.019075)

5. **Controlled multi-illumination reconstruction is research.** Huo et al.'s real-image work used controlled measured illumination and camera/spectral-camera reference acquisition. Its special iPhone illumination-control example required jailbreak. It provides no ready universal-phone or browser capture solution. [Paper](https://arxiv.org/html/2304.02162v2)

6. **Interoperate with measured reference libraries.** OSSL provides harmonized instrument spectra and analytical reference data. It is a useful precedent for linked identifiers, units, methods and uncertainty. Source licences differ: no external dataset is imported or relicensed by this research. [OSSL paper](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0296545)

## Smallest next build

**First: optional-card guidance using today's camera/picker.** Clarify SPEC §5's existing allowance, align website/app instructions and make “no printed card needed” visible. Preserve A+B, consent, honest context, JPEG/size checks, private pilot membership, queue ownership and publication holds. Keep sample/library registration explicit; never fill missing depth with zero or quietly label an ordinary capture as a registered sample. No new dependency, native permission or measurement tier is needed for this limited change.

**Second: an optional live browser guide.** A page can display a camera stream beneath SVG/HTML through the standard media API. It needs explicit camera permission, HTTPS, feature detection and a camera/gallery fallback. Request no microphone. The guide must stay out of saved image bytes; stop streams on cancel, completion, navigation, backgrounding, account changes and lost admission, including late permission responses. The OS camera launched by today's picker/plugin cannot inherit a page overlay. [W3C Media Capture](https://www.w3.org/TR/mediacapture-streams/)

Still-photo capture and video-frame snapshots have different behavior; probe capabilities and retain fallback instead of assuming RAW, exposure or flash support. A new browser path must preserve the existing native permission policy. Custom native camera work would need its own reviewed permission/language scope. [W3C Image Capture](https://www.w3.org/TR/image-capture/), [Capacitor Camera](https://capacitorjs.com/docs/apis/camera)

**Separately decide default node registration.** If every phone observation should immediately become a library sample even when depth is unknown, prepare an explicit schema/protocol design for unknown context before implementing it. The existing namespace/sample contract requires declared bounds. Do not invent those facts to reduce taps.

## Research validation before stronger measurement claims

Proposed experiment, not an executed result or an approved purchase:

- Capture the same staged soils with ordinary cardless JPEG, a physical reference, and supported RAW flash/no-flash equipment. Include wet/dry states, variable lighting, several phone models and multiple units of a model.
- Obtain independent reference color, spectra and relevant laboratory measurements from the same specimens. Keep repeated views/sample twins in one partition; hold out whole samples, devices and sites.
- Predeclare color error, repeatability, device bias, failure/missingness and usability metrics. Evaluate spectral reconstruction and laboratory-property prediction separately. Do not invent accuracy thresholds after seeing model results.
- Measure capture completion/dropout and support/fallback rates on actual phones. A useful proposed usability target is completion without printing; any time or accuracy target must be agreed and measured.
- Never use location priors as gold labels or count spectral predictions as newly measured reference data. Retain consent/withdrawal, held-out truth, screening and private-data boundaries.

No field specimens, camera access, original spectrum downloads, device experiments or user data were used for this investigation. Browser emulation does not certify real-phone capture quality.

## Authority and assumptions

The owner authorized merges #83 then #84; both are merged. This research proposes follow-up source work and changes no runtime behavior. Pages runs generated by those merges were cancelled. Capture and library uploads remain closed.

Here “node” means a private linked soil record/sample namespace, not a remotely enrolled server. The intended low-friction experience is a phone observation first, optional documented sample linkage, then independently measured evidence when available. Public enrollment, migration/deployment, actual account creation, photo publication, field training and federation require their existing separate approvals.

No new dependency, paid/closed service, licence change or native-code exception is selected. A concise implementation brief and a device capability audit accompany this report.

