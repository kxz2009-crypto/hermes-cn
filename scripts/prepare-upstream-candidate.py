#!/usr/bin/env python3
"""Extract review-only upgrade inputs from pinned official Git objects; never installs/signs/publishes."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tomllib
from urllib.parse import urlsplit

TARGET = '2bd378ed1b8d6bf2192cb26e0a55ff3091e6bd19'
TAG = 'v0.23.0'
FILES = ['pyproject.toml', '.python-version', 'pm/lock.json', 'uv.lock', 'package.json', 'scripts/install.sh', 'LICENSE']
PLATFORMS = ['linux-x64', 'darwin-arm64', 'darwin-x64']
HEX = re.compile(r'^[0-9a-f]{64}$')

def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.PIPE, timeout=90)

def read_inputs(repo):
    # This tool reads fixed Git objects, not modified worktree contents or .env files.
    origin = git(repo, 'remote', 'get-url', 'origin').decode().strip()
    if origin not in ['https://github.com/NousResearch/hermes-agent.git', 'https://github.com/NousResearch/hermes-agent']:
        raise ValueError('Expected official upstream origin')
    commit = git(repo, 'rev-parse', f'refs/tags/{TAG}^{{commit}}').decode().strip()
    if commit != TARGET:
        raise ValueError('Official tag does not match approved full SHA')
    return {name: git(repo, 'show', f'{TARGET}:{name}') for name in FILES}

def validate_artifact(item):
    if not isinstance(item, dict) or not HEX.fullmatch(str(item.get('sha256', ''))):
        raise ValueError('Missing official artifact digest')
    url = urlsplit(item.get('url', ''))
    if url.scheme != 'https' or url.username or url.password or url.hostname != 'github.com' or url.query or url.fragment:
        raise ValueError('Unexpected official artifact origin')
    return {'url': item['url'], 'sha256': item['sha256'], 'network_verified': False}

def build_inputs(files):
    metadata = tomllib.loads(files['pyproject.toml'].decode())['project']
    lock = json.loads(files['pm/lock.json'])
    packages = lock['packages']
    py = packages['python']; uv = packages['uv']
    pin = files['.python-version'].decode().strip()
    if pin != '3.14':
        raise ValueError('Pinned project version/runtime mismatch')
    if not re.fullmatch(r'3\.14\.\d+\+\d{8}', py['version']):
        raise ValueError('Unexpected exact Python build')
    script = files['scripts/install.sh'].decode()
    uv_pin = re.search(r'^UV_PIN_VERSION="([^"]+)"$', script, re.M)
    if not uv_pin or uv_pin[1] != uv['version']:
        raise ValueError('Official installer and PM disagree on uv version')
    platforms = {}
    for platform in PLATFORMS:
        uv_artifact = validate_artifact(uv['artifacts'][platform])
        py_artifact = validate_artifact(py['artifacts'][platform])
        if uv_artifact['url'] not in script or uv_artifact['sha256'] not in script:
            raise ValueError('Official bootstrap and PM uv artifacts disagree')
        platforms[platform] = {'uv': uv_artifact, 'python': py_artifact,
                               'actual_installation': 'NOT_TESTED', 'customer_delivery': 'NO-GO'}
    return {
        'schema': 'localvram-hermes-cn/unsigned-upgrade-inputs/1',
        'release_id': 'LV-HERMES-0230-FIRST-UPGRADE-20261109',
        'state': 'UNSIGNED_REVIEW_ONLY_NOT_INSTALLABLE',
        'upstream': {'tag': TAG, 'commit': TARGET, 'requires_python': metadata['requires-python'],
                     'python_runtime_pin': pin, 'python_exact_build': py['version'], 'uv_version': uv['version'],
                     'python_package_metadata_version': metadata.get('version'),
                     'version_authority': 'Git tag and full commit; pyproject version may be a packaging placeholder'},
        'dependency_facts': {'node_package_engines': json.loads(files['package.json']).get('engines', {}),
                             'scope_note': 'Package engines are not proof every Python CLI path requires Node; Electron restrictions apply to Desktop.'},
        'official_files': {name: {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)} for name, raw in files.items()},
        'platforms': platforms,
        'source_distribution': {'format_required': 'git-bundle', 'approved_published_url': None,
                                'verified_download_sha256': None, 'status': 'BLOCKED_UNPUBLISHED_V0230'},
        'legacy_assets_reusable_without_revalidation': False,
        'required_integration': ['Reconcile uncommitted R3 changes in their owning branch before merging.',
                                 'Use new uv/Python exact builds, never inherit v0.22.2 download acceptance.',
                                 'Measure a new Git bundle and approved CN delivery URL before descriptor signing.',
                                 'Use isolated test signing; production signing requires separate approval.',
                                 'Keep regional/platform real installation evidence separate.'],
        'production_actions': False, 'source_fallback': 'NO_GITHUB_INSTALL_FALLBACK',
        'signature': None, 'download_or_install_performed': False,
    }

def prepare(repo, out):
    out = Path(out).absolute()
    if out.exists() or any(p.is_symlink() for p in [out, *out.parents]):
        raise ValueError('New non-symlink output directory required')
    files = read_inputs(repo); doc = build_inputs(files)
    out.mkdir(parents=True, mode=0o700)
    for name, raw in files.items():
        path = out/'official-source-evidence'/name; path.parent.mkdir(parents=True, exist_ok=True);path.write_bytes(raw)
    (out/'unsigned-upgrade-inputs.json').write_text(json.dumps(doc, indent=2)+'\n')
    hashes = {str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob('*')) if p.is_file()}
    (out/'SHA256SUMS.json').write_text(json.dumps(hashes, indent=2)+'\n')
    return {'result': 'CANDIDATE_INPUT_BUILD_PASS', 'release_id': doc['release_id'], 'customer_delivery': 'NO-GO', 'file_count': len(hashes)+1}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__);parser.add_argument('--upstream-clone', type=Path, required=True);parser.add_argument('--out', type=Path, required=True);args=parser.parse_args()
    try: print(json.dumps(prepare(args.upstream_clone, args.out)))
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as exc: parser.exit(2, f'CANDIDATE_BLOCKED: {type(exc).__name__}: {exc}\n')
