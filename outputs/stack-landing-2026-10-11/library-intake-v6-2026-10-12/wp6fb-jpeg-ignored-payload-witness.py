"""Independent in-memory synthetic decoder witness; no network/models/image files."""
from __future__ import annotations
import hashlib,io,json,sys
from pathlib import Path
import numpy as np
from PIL import Image

snapshot=Path('/private/tmp/gsip-jpeg-independent-probe-24ghi1c_')
sys.path.insert(0,str(snapshot))
from pipeline.qa import has_embedded_metadata
from pipeline.photo_privacy import decode_sanitized
out=io.BytesIO()
Image.fromarray(np.random.default_rng(13).integers(0,256,(49,67,3),dtype=np.uint8)).save(out,format='JPEG')
clean=out.getvalue()
expected=decode_sanitized(clean)
end=4+int.from_bytes(clean[4:6],'big')
private=b'synthetic-private-channel'
base={0xDD:b'\x00\x00',0xDC:b'\x00\x31',0xDB:b'\x03'+b'\x01'*64,0xC4:b'\x13'+bytes([0,2]+[0]*14)+b'\x01\x02'}
records=[]
for marker,payload in base.items():
    for extra in [b'',b'\x00',b'\x00'*17,private]:
        for where in ['before_frame','after_scan']:
            segment=b'\xff'+bytes([marker])+(len(payload+extra)+2).to_bytes(2,'big')+payload+extra
            raw=clean[:end]+segment+clean[end:] if where=='before_frame' else clean[:-2]+segment+clean[-2:]
            try: dirty=has_embedded_metadata(raw)
            except Exception: dirty='unreadable'
            try:
                image=decode_sanitized(raw)
                accepted=True
                pixels_identical=bool(np.array_equal(image,expected))
            except Exception:
                accepted=False
                pixels_identical=None
            records.append({'marker':hex(marker),'extra_bytes':len(extra),'extra_is_private_ascii':extra==private,'position':where,'metadata_dirty':dirty,'full_decoder_accepted':accepted,'pixels_identical':pixels_identical})
receipt={
    'candidate_manifest':'/private/tmp/gsip-6fb-final-candidate-manifest.json',
    'candidate_manifest_sha256':hashlib.sha256(Path('/private/tmp/gsip-6fb-final-candidate-manifest.json').read_bytes()).hexdigest(),
    'scope':'32 synthetic in-memory full decoder probes; no HTTP/model loads/image persistence/source edits',
    'file_hashes':{name:hashlib.sha256((snapshot/name).read_bytes()).hexdigest() for name in ['pipeline/qa.py','pipeline/photo_privacy.py']},
    'results':records,
    'blocking_findings_remain':True,
}
print(json.dumps(receipt,indent=2))
