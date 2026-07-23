"""Synthetic proof that complete unused trailing definitions are ignored by real decoding."""
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
Image.fromarray(np.random.default_rng(14).integers(0,256,(49,67,3),dtype=np.uint8)).save(out,format='JPEG')
clean=out.getvalue(); expected=decode_sanitized(clean)
private=b'synthetic-private-channel'
payloads={
    'valid_DQT_8bit_table3_with_private_ascii_values':(0xDB,b'\x03'+private+b'\x01'*(64-len(private))),
    'valid_DHT_AC_table3_four_3bit_codes':(0xC4,b'\x13'+bytes([0,0,4]+[0]*13)+b'\x31\x41\x51\x61'),
    'valid_DRI_interval_0x1337':(0xDD,b'\x13\x37'),
    'valid_DNL_49_lines':(0xDC,b'\x00\x31'),
    'valid_DAC_AC_table3_K63':(0xCC,b'\x13\x3f'),
}
results=[]
for name,(marker,payload) in payloads.items():
    segment=b'\xff'+bytes([marker])+(len(payload)+2).to_bytes(2,'big')+payload
    raw=clean[:-2]+segment+clean[-2:]
    assert raw.count(b'\xff\xda')==1
    try: dirty=has_embedded_metadata(raw)
    except Exception: dirty='unreadable'
    try: actual=decode_sanitized(raw); accepted=True; identical=bool(np.array_equal(actual,expected))
    except Exception: accepted=False; identical=None
    results.append({'case':name,'position':'after_final_scan_no_subsequent_SOS','metadata_dirty':dirty,'decoder_accepted':accepted,'pixels_identical':identical})
print(json.dumps({'qa_sha256':hashlib.sha256((snapshot/'pipeline/qa.py').read_bytes()).hexdigest(),'decoder_sha256':hashlib.sha256((snapshot/'pipeline/photo_privacy.py').read_bytes()).hexdigest(),'scope':'synthetic in-memory bytes, complete trailing definitions with no future scan; no network/models/image persistence','results':results,'blocking_findings_remain':True},indent=2))
