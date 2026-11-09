"""Synthetic boundary tests; actual Git-object build is a separate acceptance command."""
import copy, hashlib, importlib.util, json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
s=importlib.util.spec_from_file_location('candidate',Path(__file__).with_name('prepare-upstream-candidate.py'))
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class CandidateTests(unittest.TestCase):
    def setUp(self):
        packages={k:{'version':v,'artifacts':{t:{'url':f'https://github.com/astral-sh/{k}/releases/download/SYNTHETIC/{t}', 'sha256':'a'*64} for t in m.PLATFORMS}} for k,v in [('python','3.14.9+20261021'),('uv','0.13.5')]}
        self.files={'pyproject.toml':b'[project]\nversion="0.0.0"\nrequires-python=">=3.11,<3.15"\n','.python-version':b'3.14\n','pm/lock.json':json.dumps({'packages':packages}).encode(),'uv.lock':b'SYNTHETIC-LOCK-NOT-UPSTREAM','package.json':b'{"engines":{"node":">=26"}}','scripts/install.sh':('UV_PIN_VERSION="0.13.5"\n'+'\n'.join(x['url']+' '+x['sha256'] for x in packages['uv']['artifacts'].values())).encode(),'LICENSE':b'SYNTHETIC-NOT-LEGAL-APPROVAL'}
    def test_packaging_placeholder_not_release_authority(self):
        x=m.build_inputs(self.files);self.assertEqual(x['upstream']['tag'],'v0.23.0');self.assertEqual(x['upstream']['python_package_metadata_version'],'0.0.0')
    def test_no_unsigned_candidate_becomes_delivery(self):
        x=m.build_inputs(self.files);self.assertFalse(x['production_actions']);self.assertIsNone(x['signature']);self.assertIsNone(x['source_distribution']['approved_published_url']);self.assertTrue(all(p['customer_delivery']=='NO-GO' for p in x['platforms'].values()))
    def test_wrong_runtime_pin_rejected(self):
        self.files['.python-version']=b'3.11'
        with self.assertRaises(ValueError):m.build_inputs(self.files)
    def test_changed_bootstrap_version_rejected(self):
        self.files['scripts/install.sh']=self.files['scripts/install.sh'].replace(b'0.13.5',b'0.12.3')
        with self.assertRaises(ValueError):m.build_inputs(self.files)
    def test_missing_platform_artifact_rejected(self):
        x=json.loads(self.files['pm/lock.json']);del x['packages']['python']['artifacts']['darwin-arm64'];self.files['pm/lock.json']=json.dumps(x).encode()
        with self.assertRaises(KeyError):m.build_inputs(self.files)
    def test_hash_and_origin_required(self):
        for item in [{'url':'https://github.com/a','sha256':'short'}, {'url':'http://github.com/a','sha256':'a'*64}, {'url':'https://user:secret@github.com/a','sha256':'a'*64}, {'url':'https://example.invalid/a','sha256':'a'*64}]:
            with self.subTest(item=item):
                with self.assertRaises(ValueError):m.validate_artifact(item)
    def test_bootstrap_hash_must_match_pm(self):
        self.files['scripts/install.sh']=self.files['scripts/install.sh'].replace(b'a'*64,b'b'*64)
        with self.assertRaises(ValueError):m.build_inputs(self.files)
    def test_existing_output_never_overwritten(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'keep').write_text('keep')
            with self.assertRaises(ValueError):m.prepare(p,p)
            self.assertEqual((p/'keep').read_text(),'keep')
    def test_symlink_ancestor_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'target').mkdir();(p/'link').symlink_to(p/'target',target_is_directory=True)
            with self.assertRaises(ValueError):m.prepare(p,p/'link'/'new')
    def test_generated_content_manifest_is_complete(self):
        with tempfile.TemporaryDirectory() as t,patch.object(m,'read_inputs',return_value=self.files):
            out=Path(t)/'new';m.prepare(Path(t),out);hashes=json.loads((out/'SHA256SUMS.json').read_text())
            self.assertEqual(len(hashes),8)
            for name,digest in hashes.items():self.assertEqual(hashlib.sha256((out/name).read_bytes()).hexdigest(),digest)
    def test_wrong_git_origin_rejected(self):
        with patch.object(m,'git',return_value=b'https://example.invalid/hermes.git'):
            with self.assertRaises(ValueError):m.read_inputs(Path('.'))
    def test_wrong_tag_commit_rejected(self):
        with patch.object(m,'git',side_effect=[b'https://github.com/NousResearch/hermes-agent.git',b'b'*40]):
            with self.assertRaises(ValueError):m.read_inputs(Path('.'))
if __name__=='__main__':unittest.main()
