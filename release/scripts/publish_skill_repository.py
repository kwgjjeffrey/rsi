"""Publish the verified consumer archive on a GitHub branch for npx skills."""
import argparse,json,shutil,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from utils.skill_project_toolkit import verify_archive,extract_archive

p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--checkout',type=Path,required=True);a=p.parse_args();repo=a.repo.resolve();manifest=repo/'dist/rsi-release.json';m=json.loads(manifest.read_text());archive=repo/'dist'/m['asset'];verify_archive(archive,manifest)
def git(*args,cwd=repo):
    return subprocess.check_output(['git',*args],cwd=cwd,text=True).strip()
assert git('rev-parse','HEAD')==m['sourceCommit'],'Archive must match source HEAD'
remote=git('remote','get-url','origin');assert 'kwgjjeffrey/rsi' in remote
assert not a.checkout.exists(),'Use a fresh isolated consumer checkout'
subprocess.run(['git','clone','--no-checkout',remote,str(a.checkout)],check=True)
refs=git('branch','-r',cwd=a.checkout)
if 'origin/distribution' in refs:
    subprocess.run(['git','checkout','-B','distribution','origin/distribution'],cwd=a.checkout,check=True)
else:
    subprocess.run(['git','checkout','--orphan','distribution'],cwd=a.checkout,check=True)
for child in a.checkout.iterdir():
    if child.name=='.git':continue
    if child.is_dir():shutil.rmtree(child)
    else:child.unlink()
stage=a.checkout.parent/(a.checkout.name+'-extract');assert not stage.exists();stage.mkdir();extract_archive(archive,stage)
for child in (stage/'package').iterdir():
    if child.is_dir():shutil.copytree(child,a.checkout/child.name)
    else:shutil.copy2(child,a.checkout/child.name)
(a.checkout/'release-manifest.json').write_text(json.dumps(m,indent=2)+'\n')
subprocess.run(['git','add','-A'],cwd=a.checkout,check=True)
subprocess.run(['git','commit','-m','release: consumer artifacts '+m['version']],cwd=a.checkout,check=True)
subprocess.run(['git','push','origin','HEAD:refs/heads/distribution'],cwd=a.checkout,check=True)
print(json.dumps({'version':m['version'],'sourceCommit':m['sourceCommit'],'consumerCommit':git('rev-parse','HEAD',cwd=a.checkout),'install':'npx skills add https://github.com/kwgjjeffrey/rsi/tree/distribution --skill rsi --global --yes'}))
