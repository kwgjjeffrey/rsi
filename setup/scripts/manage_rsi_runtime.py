#!/usr/bin/env python3
"""Own discovery, lifecycle and private state; does not download unverified binaries."""
import argparse,json,os,subprocess,sys,time,urllib.request,signal
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('action',choices=['start','status','stop','build']);p.add_argument('--data-dir',type=Path,required=True);a=p.parse_args();skill=Path(__file__).resolve().parents[2];data=a.data_dir.resolve();data.mkdir(parents=True,exist_ok=True);discovery=data/'runtime.json'
import fcntl
lock=open(data/'runtime.lock','a');fcntl.flock(lock,fcntl.LOCK_EX)
def healthy():
 try:
  d=json.loads(discovery.read_text())
  with urllib.request.urlopen(d['url']+'/health',timeout=2) as r:
   return d if json.load(r).get('protocol')==1 else None
 except Exception:return None
if a.action=='build':
 subprocess.run(['cargo','build','--release','--locked','--manifest-path',str(skill/'local-runtime/Cargo.toml')],check=True);out=skill/'local-runtime/bin';out.mkdir(exist_ok=True);import shutil;shutil.copy2(skill/'local-runtime/target/release/rsi-runtime',out/'rsi-runtime.staged');os.replace(out/'rsi-runtime.staged',out/'rsi-runtime');print(out/'rsi-runtime');sys.exit()
d=healthy()
if a.action=='status':print(json.dumps({'running':bool(d),'discovery':str(discovery),'url':d['url'] if d else None}));sys.exit()
if a.action=='stop':
 if d:os.kill(d['pid'],signal.SIGTERM)
 discovery.unlink(missing_ok=True);print('{"stopped":true}');sys.exit()
if d:print(d['url']+'/');sys.exit()
binary=skill/'local-runtime/bin/rsi-runtime'
if not binary.is_file():sys.exit('runtime binary missing; developers use build, consumers install a platform release')
env=dict(os.environ,RSI_DATA_DIR=str(data));log=open(data/'runtime.log','ab');os.chmod(data,0o700)
proc=subprocess.Popen([str(binary),'serve'],env=env,stdout=log,stderr=log,start_new_session=True)
for _ in range(100):
 d=healthy()
 if d:print(d['url']+'/');break
 if proc.poll() is not None:sys.exit('runtime exited; inspect runtime.log')
 time.sleep(.05)
else:sys.exit('runtime start timeout; inspect runtime.log')
