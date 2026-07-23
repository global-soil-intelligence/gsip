from pathlib import Path, PurePosixPath
from html.parser import HTMLParser
import hashlib
import html
import io
import json
import re
import tarfile
import zipfile

out = Path(__file__).resolve().parent
metadata = json.loads((out/'artifact-metadata.json').read_text())
archive = out/'github-pages.zip'
zip_bytes = archive.read_bytes()
zip_sha = hashlib.sha256(zip_bytes).hexdigest()
assert metadata['name'] == 'github-pages' and metadata['expired'] is False
if metadata.get('digest'):
    assert metadata['digest'] == 'sha256:' + zip_sha, 'Artifact digest differs from GitHub metadata'
limit = 50 * 1024 * 1024
with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
    members = z.infolist()
    assert len(members) == 1 and members[0].filename == 'artifact.tar', 'Unexpected artifact zip layout'
    assert not members[0].is_dir() and members[0].file_size < limit
    tar_bytes = z.read(members[0])
files = {}
with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode='r:') as tar:
    total = 0
    for member in tar.getmembers():
        path = PurePosixPath(member.name)
        assert not path.is_absolute() and '..' not in path.parts, 'Unsafe artifact member path'
        assert member.isfile() or member.isdir(), 'Links and special archive entries refused'
        if member.isdir():
            continue
        name = str(path)
        assert name not in files, 'Duplicate normalized artifact path'
        total += member.size
        assert 0 <= member.size < limit and total < limit, 'Artifact exceeds review size bound'
        f = tar.extractfile(member)
        assert f is not None
        content = f.read()
        assert len(content) == member.size
        files[name] = content

def strict_object(pairs):
    value = {}
    for key, item in pairs:
        assert key not in value, 'Duplicate JSON field'
        value[key] = item
    return value

activation = json.loads(files['capture/gsip-activation.json'], object_pairs_hook=strict_object)
assert set(activation) == {'capture_live', 'library_intake_live'}
assert all(type(value) is bool and value is False for value in activation.values()), 'Activation must remain closed'

class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = 0
        self.heading = None
        self.headings = []
        self.parts = []
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.skip += 1
        if tag == 'h1':
            self.heading = []
    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.skip -= 1
        if tag == 'h1':
            assert self.heading is not None
            self.headings.append(''.join(self.heading))
            self.heading = None
    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)
            if self.heading is not None:
                self.heading.append(data)

headlines = {
    'index.html': 'Build the world’s open soil spectral library.',
    'about/index.html': 'A shared library for the ground we depend on.',
    'card/index.html': 'Give every phone camera a reference point.',
    'data/index.html': 'A dataset designed to be used—and scrutinized.',
    'methods/index.html': 'Scientific honesty is part of the architecture.',
}
visible = {}
for path, expected in headlines.items():
    markup = files[path].decode('utf-8')
    parsed = VisibleText()
    parsed.feed(markup)
    assert parsed.headings == [expected], f'Wrong prerendered headline: {path}'
    text = re.sub(r'\s+', ' ', ' '.join(parsed.parts))
    assert 'Public capture closed' in text
    assert 'https://global-soil-intelligence.github.io/gsip/og-library.png' in markup
    graphs = re.findall(r'<script type="application/ld\+json">([\s\S]*?)</script>', markup)
    assert len(graphs) == 1
    graph = json.loads(graphs[0], object_pairs_hook=strict_object)['@graph']
    assert any(item.get('@type') == 'Organization' for item in graph)
    if path in ('index.html', 'data/index.html'):
        datasets = [item for item in graph if item.get('@type') == 'Dataset']
        assert len(datasets) == 1
        dataset = datasets[0]
        assert dataset['creativeWorkStatus'] == 'In development; public releases gated'
        assert 'spatialCoverage' not in dataset and 'distribution' not in dataset
    visible[path] = text
assert 'The whole stack is open source.' in visible['index.html']
assert 'Public capture and library uploads remain closed.' in visible['index.html']
assert 'Your records and credentials remain protected.' in visible['index.html']
assert 'structured data only until photo screening is deployed and its calibration approved' in visible['data/index.html']
assert 'Individual spectra remain private pending a fingerprinting and privacy review' in visible['data/index.html']
assert 'RGB images, not wavelength-resolved spectra' in visible['methods/index.html']
llms = files['llms.txt'].decode('utf-8')
for fragment in ('open soil spectral reference library in development', 'Public capture and library uploads remain closed', 'full GSIP app, backend, library, modelling, API and test source under MIT', '/docs/SOIL_LIBRARY.md', 'untrusted'):
    assert fragment in llms, 'Missing agent-readable boundary'
assert files['og-library.png'][:8] == b'\x89PNG\r\n\x1a\n'
source_image = Path('/Users/justinhart/.codex/worktrees/gsip-spec-followups/GSIP 2.0/apps/site-web/public/og-library.png').read_bytes()
assert files['og-library.png'] == source_image
for name, value in files.items():
    assert not any(item in value for item in (b'https://supabase.test', b'e2e-access-token', b'e2e-refresh-token')), 'Synthetic test fixture found in release artifact'
assert 'capture/index.html' in files and 'map/index.html' in files
assert any(name.endswith('gsip-reference-card-v1-color.pdf') for name in files)
receipt = {
    'status': 'VERIFIED_CLOSED_ARTIFACT_NOT_DEPLOYED',
    'run_id': 38821460183,
    'run_url': 'https://github.com/global-soil-intelligence/gsip/actions/runs/38821460183',
    'source_commit': '73088050d6fc68baedf893990ab3fbe76d5e749c',
    'reviewed_source_tree': '43c74ca13b889a561e0e23463b9706c064cf48a8',
    'artifact_id': metadata['id'],
    'github_digest': metadata.get('digest'),
    'zip_sha256': zip_sha,
    'tar_sha256': hashlib.sha256(tar_bytes).hexdigest(),
    'file_count': len(files),
    'total_bytes': total,
    'activation': activation,
    'prerendered_pages': list(headlines),
    'checks': ['safe archive layout', 'GitHub artifact digest', 'closed activation', 'five prerendered headlines and Organization JSON-LD', 'gated Dataset JSON-LD', 'whole-stack builder copy', 'photo and spectral privacy boundaries', 'agent-readable library/terms copy', 'reviewed social image bytes', 'no synthetic capture fixture', 'map/capture/reference-card assets'],
    'deployment_approval': 'NOT_GRANTED',
    'files': [{'path': name, 'bytes': len(value), 'sha256': hashlib.sha256(value).hexdigest()} for name, value in sorted(files.items())],
}
(out/'artifact-verification.json').write_text(json.dumps(receipt, indent=2)+'\n')
print(json.dumps({key: receipt[key] for key in ('status', 'artifact_id', 'file_count', 'total_bytes', 'activation', 'zip_sha256')}))
