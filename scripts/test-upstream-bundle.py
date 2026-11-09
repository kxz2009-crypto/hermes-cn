"""Synthetic safety boundaries; not real installation or download evidence."""
import importlib.util, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
s=importlib.util.spec_from_file_location('bundle',Path(__file__).with_name('build-upstream-bundle.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class BundleTests(unittest.TestCase):
    def test_shallow_repository_refused_before_output(self):
        with tempfile.TemporaryDirectory() as t,patch.object(m.m,'git',return_value=b'true\n'),patch.object(m,'command') as call:
            out=Path(t)/'new'
            with self.assertRaisesRegex(ValueError,'Shallow'):m.build(Path(t),out)
            self.assertFalse(out.exists());call.assert_not_called()
    def test_existing_output_refused(self):
        with tempfile.TemporaryDirectory() as t,patch.object(m,'command') as call:
            with self.assertRaises(ValueError):m.build(Path(t),Path(t))
            call.assert_not_called()
    def test_symlink_parent_refused(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'target').mkdir();(p/'link').symlink_to(p/'target',target_is_directory=True)
            with self.assertRaises(ValueError):m.build(p,p/'link'/'new')
    def test_failed_restore_cannot_write_success_receipt(self):
        with tempfile.TemporaryDirectory() as t,patch.object(m.m,'git',return_value=b'false\n'),patch.object(m.m,'read_inputs',return_value={}),patch.object(m,'command',side_effect=['',ValueError('restore failed')]):
            out=Path(t)/'new'
            with self.assertRaises(ValueError):m.build(Path(t),out)
            self.assertFalse((out/'bundle-receipt.json').exists())
    def test_wrong_restored_commit_cannot_pass(self):
        with tempfile.TemporaryDirectory() as t,patch.object(m.m,'git',return_value=b'false\n'),patch.object(m.m,'read_inputs',return_value={}),patch.object(m,'command',side_effect=['','','0'*40]):
            out=Path(t)/'new'
            with self.assertRaisesRegex(ValueError,'commit mismatch'):m.build(Path(t),out)
            self.assertFalse((out/'bundle-receipt.json').exists())
if __name__=='__main__':unittest.main()
