"""Create the editable, self-contained GSIP announcement vector artwork."""
from pathlib import Path
from random import Random

OUT = Path(__file__).parent
rng = Random(41)
grain = ''.join(
    f'<ellipse cx="{rng.uniform(9, 241):.1f}" cy="{rng.uniform(7, 147):.1f}" '
    f'rx="{rng.uniform(1.1, 4.3):.1f}" ry="{rng.uniform(.7, 2.4):.1f}" '
    f'fill="{rng.choice(["#E3BD8B", "#553625", "#A16F48", "#C99660"])}" opacity=".68"/>'
    for _ in range(105)
)

svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" viewBox="0 0 1600 900" role="img" aria-labelledby="title desc">
  <title id="title">GSIP — An open soil spectral library</title>
  <desc id="desc">Project vision: smartphones capture soil photographs and context. Separate instruments measure spectra from the same physical sample. Sample-linked records form an open library for builders. Public uploads are not yet open.</desc>
  <metadata>GSIP LinkedIn announcement. Editable vector artwork. No embedded bitmap, external resource, private data, or scientific result. Created 2026-10-16.</metadata>
  <defs>
    <linearGradient id="paper" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#FAF8EF"/><stop offset="1" stop-color="#ECEEDE"/></linearGradient>
    <linearGradient id="soil" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#A7794D"/><stop offset=".52" stop-color="#785035"/><stop offset="1" stop-color="#473426"/></linearGradient>
    <linearGradient id="forest" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#254B3D"/><stop offset="1" stop-color="#112F28"/></linearGradient>
    <linearGradient id="metal" x1="0" y1="0" x2="1" y2="0"><stop stop-color="#A9BBB0"/><stop offset=".4" stop-color="#EAF0E7"/><stop offset="1" stop-color="#8FA699"/></linearGradient>
    <filter id="shadow" x="-35%" y="-30%" width="170%" height="175%"><feDropShadow dx="0" dy="12" stdDeviation="13" flood-color="#17372B" flood-opacity=".13"/></filter>
    <clipPath id="phone-photo"><rect x="23" y="44" width="186" height="170" rx="6"/></clipPath>
    <clipPath id="soil-crop"><rect width="250" height="155" rx="14"/></clipPath>
    <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M1 1 8 5 1 9" fill="none" stroke="#789467" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></marker>
    <g id="soil-texture"><rect width="250" height="155" rx="14" fill="url(#soil)"/>GRAIN</g>
    <g id="card"><rect width="51" height="112" rx="4" fill="#FAF7EC" stroke="#E5DCC9" stroke-width="2"/><rect x="8" y="8" width="35" height="18" fill="#293A31"/><rect x="8" y="34" width="35" height="18" fill="#9C9F8F"/><rect x="8" y="60" width="35" height="18" fill="#C39A72"/><rect x="8" y="86" width="35" height="18" fill="#ECE8D7"/></g>
    <g id="mini-spectrum"><path d="M0 58H126M0 58V0" stroke="#D7E4C8" stroke-opacity=".32" fill="none"/><path d="M0 51 10 48 18 45 27 39 36 35 44 29 54 25 64 23 73 18 81 24 90 21 98 29 106 26 115 34 126 37" stroke="#D9E8AF" stroke-width="3.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/></g>
  </defs>
  <style>
    text {font-family:Arial,Helvetica,sans-serif;fill:#17392F}
    .eyebrow {font-size:17px;font-weight:700;letter-spacing:3px}
    .hero {font-family:Georgia,'Times New Roman',serif;font-size:78px;letter-spacing:-2.2px}
    .step {font-size:12px;letter-spacing:2.1px;font-weight:700;fill:#65806A}
    .label {font-size:29px;font-weight:700;letter-spacing:-.8px}
    .detail {font-size:18px;fill:#60766A}
    .line {stroke:#789467;stroke-width:2;fill:none;stroke-linecap:round;stroke-linejoin:round}
  </style>
  <rect width="1600" height="900" fill="url(#paper)"/>
  <path d="M1220 0C1380 165 1435 360 1600 355V0Z" fill="#DCE5C9" opacity=".55"/>
  <path d="M0 454C210 402 277 676 518 664S926 556 1076 786H0Z" fill="#E0E5D2" opacity=".5"/>

  <!-- Brand and headline: editable live text. -->
  <g id="heading">
    <rect x="76" y="49" width="96" height="43" rx="21.5" fill="#17392F"/>
    <text x="124" y="77" fill="#F6F6E8" style="fill:#F6F6E8;font-size:23px;font-weight:700;letter-spacing:1px" text-anchor="middle">GSIP</text>
    <text class="eyebrow" x="191" y="77">GLOBAL SOIL INTELLIGENCE PROJECT</text>
    <text class="step" x="1520" y="76" text-anchor="end">OPEN SOURCE · BUILD WITH US</text>
    <text class="hero" x="76" y="183">An open soil</text>
    <text class="hero" x="76" y="266">spectral library.</text>
    <path d="M902 178H970" stroke="#A57646" stroke-width="3"/>
    <text x="902" y="220" style="font-size:25px;letter-spacing:-.3px">Images, spectra and sample context.</text>
    <text class="detail" x="902" y="254">A shared foundation for research and builders.</text>
  </g>

  <!-- Three equal visual areas preserve the distinct roles. -->
  <g id="field-capture">
    <rect x="76" y="322" width="446" height="379" rx="28" fill="#F8F7ED" stroke="#D9E1CD"/>
    <text class="step" x="103" y="357">01 / FIELD OBSERVATIONS</text>
    <ellipse cx="290" cy="595" rx="172" ry="19" fill="#132F25" opacity=".07"/>
    <g transform="translate(174 378) rotate(-7 105 116)" filter="url(#shadow)">
      <rect width="220" height="252" rx="32" fill="#20372F"/>
      <rect x="6" y="6" width="208" height="240" rx="27" fill="#12251F" stroke="#657A65" stroke-width="1.6"/>
      <rect x="17" y="32" width="186" height="170" rx="10" fill="#A47B54"/>
      <g clip-path="url(#phone-photo)" transform="translate(-5 -11)">
        <use href="#soil-texture" x="8" y="44"/>
        <path d="M10 192 46 139 63 145 93 111 123 121 141 166 171 189Z" fill="#84562F"/>
        <path d="M49 139 94 111 122 122 95 129 82 148 65 151Z" fill="#B5864F"/>
        <use href="#card" transform="translate(156 88) scale(.68) rotate(9)"/>
      </g>
      <rect x="73" y="14" width="74" height="10" rx="5" fill="#061A13"/>
      <circle cx="110" cy="222" r="16" fill="#E9EFDC"/>
      <circle cx="110" cy="222" r="12" fill="none" stroke="#264433" stroke-width="1.3"/>
      <path d="M24 218H47M174 218H195" stroke="#B0C3A8" stroke-width="2" stroke-linecap="round"/>
    </g>
    <text class="label" x="103" y="654">Smartphone capture</text>
    <text class="detail" x="103" y="682">Photographs + field context</text>
  </g>

  <g id="instrument-measurement">
    <rect x="559" y="322" width="446" height="379" rx="28" fill="#F8F7ED" stroke="#D9E1CD"/>
    <text class="step" x="586" y="357">02 / INSTRUMENT MEASUREMENTS</text>
    <ellipse cx="786" cy="597" rx="161" ry="17" fill="#132F25" opacity=".07"/>
    <g filter="url(#shadow)">
      <path d="M626 421 827 389 939 439 939 547 626 547Z" fill="#DDE5DA"/>
      <path d="M626 421 827 389 939 439 736 472Z" fill="#F4F5EB"/>
      <path d="M736 472 939 439V547H736Z" fill="#B9CBBB"/>
      <path d="M626 421 736 472V547H626Z" fill="#234333"/>
      <path d="M697 424 786 410 853 438 764 454Z" fill="#526D5A"/>
      <path d="M654 499H714M654 511H714M654 523H714" stroke="#91A58C" stroke-width="2"/>
      <circle cx="913" cy="489" r="5" fill="#567C4E"/>
      <!-- Soil cup is visibly separate from the phone. -->
      <path d="M747 420V449C747 464 825 464 825 449V420Z" fill="url(#metal)" stroke="#8A9F8C"/>
      <ellipse cx="786" cy="420" rx="39" ry="12" fill="#D8E2D5" stroke="#8A9F8C"/>
      <ellipse cx="786" cy="419" rx="33" ry="9" fill="#92613B"/>
      <path d="M758 419 766 412 774 415 783 408 791 412 804 409 816 418Z" fill="#AB7D50"/>
      <rect x="658" y="505" width="247" height="111" rx="13" fill="url(#forest)" stroke="#96AE83" stroke-width="1.5"/>
      <use href="#mini-spectrum" transform="translate(679 527) scale(1.62 1.15)"/>
    </g>
    <text class="label" x="586" y="654">Measured spectra</text>
    <text class="detail" x="586" y="682">Linked laboratory evidence</text>
  </g>

  <g id="shared-library">
    <rect x="1042" y="322" width="482" height="379" rx="28" fill="#E3EBCF" stroke="#D1DDBD"/>
    <text class="step" x="1069" y="357">03 / SHARED REFERENCE RECORDS</text>
    <g id="conceptual-globe" transform="translate(1306 474)" opacity=".64" stroke="#7F9B6A" stroke-width="1.3" fill="none">
      <circle r="100"/><ellipse rx="44" ry="100"/><ellipse rx="77" ry="100"/><ellipse rx="100" ry="34"/><ellipse rx="100" ry="67"/><path d="M-100 0H100M0-100V100"/>
      <path d="M-69-48-53-63-31-62-16-46-23-32-42-29-46-11-61-19ZM-39 1-19 7-9 26-18 43-18 59-29 75-38 48-43 22ZM1-45 13-57 31-51 40-40 64-45 83-22 70-5 47-12 33 1 20-8 11-26ZM6-17 27-13 36 7 25 29 10 43 0 21-7 4ZM56 41 77 36 86 51 72 61 55 53Z" fill="#A3B98B" stroke="none"/>
    </g>
    <g id="editable-records" filter="url(#shadow)">
      <rect x="1247" y="451" width="163" height="162" rx="13" fill="#E7EAD9" stroke="#B8CAAA" transform="rotate(10 1328 531)"/>
      <rect x="1182" y="444" width="163" height="162" rx="13" fill="#F0F2E4" stroke="#B8CAAA" transform="rotate(4 1263 525)"/>
      <rect x="1110" y="439" width="172" height="171" rx="13" fill="#FFFEF6" stroke="#B8CAAA"/>
      <g clip-path="url(#soil-crop)" transform="translate(1124 453) scale(.575 .48)"><use href="#soil-texture"/><use href="#card" transform="translate(185 15) scale(.9)"/></g>
      <path d="M1125 547H1265M1125 562H1246M1125 577H1256M1125 591H1211" stroke="#BCCAAE" stroke-width="5" stroke-linecap="round"/>
      <rect x="1295" y="481" width="119" height="91" rx="9" fill="#1C4031" stroke="#E4ECD6" stroke-width="3"/>
      <use href="#mini-spectrum" transform="translate(1307 493) scale(.75 .95)"/>
    </g>
    <text class="label" x="1069" y="654">Open library</text>
    <text class="detail" x="1069" y="682">Traceable records. Open tools.</text>
  </g>

  <!-- Shared sample identity joins the two evidence streams. -->
  <g id="sample-link">
    <path class="line" d="M299 702V724Q299 738 313 738H430M782 702V724Q782 738 768 738H697"/>
    <circle cx="299" cy="702" r="4" fill="#789467"/>
    <circle cx="782" cy="702" r="4" fill="#789467"/>
    <rect x="430" y="718" width="267" height="40" rx="20" fill="#F8F7ED" stroke="#C5D3B8"/>
    <text x="563.5" y="744" text-anchor="middle" style="font-size:18px;font-weight:700">Same physical sample</text>
    <path class="line" d="M798 738H1252Q1283 738 1283 707" marker-end="url(#arrow)"/>
    <text x="1013" y="768" text-anchor="middle" style="font-size:15px;fill:#60766A">Sample-linked images, spectra and metadata</text>
  </g>

  <g id="status-footer">
    <rect y="798" width="1600" height="102" fill="#17392F"/>
    <rect y="798" width="1600" height="2" fill="#B59659"/>
    <circle cx="264" cy="850" r="4.5" fill="#DCE9AB"/>
    <text x="800" y="858" text-anchor="middle" style="font-size:23px;font-weight:700;letter-spacing:2px;fill:#F5F5E7">PROJECT VISION · PUBLIC UPLOADS NOT YET OPEN</text>
  </g>
</svg>'''.replace('GRAIN', grain)

target = OUT / 'gsip-open-soil-library-linkedin-v1.svg'
with target.open('x', encoding='utf-8') as handle:
    handle.write(svg + '\n')
print(target)
