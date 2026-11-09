#!/usr/bin/env python3
"""Build/restore a local immutable source candidate; does not sign or upload it."""
import argparse, hashlib, importlib.util, json, os, subprocess, sys
from pathlib import Path
s=importlib.util.spec_from_file_location('candidate',Path(__file__).with_name('prepare-upstream-candidate.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def command(args, log):
    env=dict(os.environ, GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT='0')
    result=subprocess.run(['git','-c','core.hooksPath=/dev/null',*args],env=env,capture_output=True,text=True,timeout=900)
    with log.open('a') as f:f.write(json.dumps({'operation':args[0], 'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr})+'\n')
    if result.returncode:raise ValueError('Git candidate operation failed; retained local log')
    return result.stdout.strip()
def build(repo, out):
    repo=Path(repo).resolve();out=Path(out).absolute()
    if out.exists() or any(p.is_symlink() for p in [out,*out.parents]):raise ValueError('New non-symlink output required')
    if m.git(repo,'rev-parse','--is-shallow-repository').decode().strip()!='false':
        raise ValueError('Shallow clone cannot establish a self-contained distribution bundle')
    m.read_inputs(repo)  # Verify official origin, exact tag/SHA and fixed source files.
    out.mkdir(parents=True,mode=0o700);log=out/'build-restore.jsonl'
    bundle=out/f'hermes-{m.TARGET}.bundle'
    command(['-C',str(repo),'bundle','create','--version=3',str(bundle),f'refs/tags/{m.TAG}'],log)
    restored=out/'restore-verification.git'
    command(['clone','--bare',str(bundle),str(restored)],log)
    actual=command(['--git-dir='+str(restored),'rev-parse',f'refs/tags/{m.TAG}^{{commit}}'],log)
    if actual!=m.TARGET:raise ValueError('Restored source commit mismatch')
    command(['--git-dir='+str(restored),'fsck','--full'],log)
    digest=hashlib.sha256()
    with bundle.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1<<20),b''):digest.update(chunk)
    receipt={'state':'LOCAL_RESTORE_VERIFIED_NOT_PUBLISHED','upstream_commit':actual,'tag':m.TAG,'format':'git-bundle','file':bundle.name,'sha256':digest.hexdigest(),'bytes':bundle.stat().st_size,'empty_repository_restore':'PASS','fsck':'PASS','china_network_download':'NOT_TESTED','published_url':None,'signature':None,'customer_delivery':'NO-GO','production_actions':False}
    (out/'bundle-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');return receipt
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--upstream-clone',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    try:print(json.dumps(build(a.upstream_clone,a.out)))
    except (OSError,ValueError,subprocess.SubprocessError) as e:p.exit(2,'BUNDLE_CANDIDATE_BLOCKED: '+str(e)+'\n')
