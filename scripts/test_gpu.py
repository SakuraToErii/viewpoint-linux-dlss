#!/usr/bin/env python3
"""Explicit, separate hidden-context GPU test; it never installs the patch."""
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from manage import require_exit

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--kind',choices=('sr','fg'),default='fg')
    p.add_argument('--width',type=int,default=1280);p.add_argument('--height',type=int,default=720)
    p.add_argument('--game-exited',action='store_true');a=p.parse_args()
    require_exit(a)
    local=json.loads((ROOT/'_work/local-build.json').read_text());game=Path(local['game_dir'])
    env=os.environ.copy()
    if not env.get('DISPLAY'):
        result=subprocess.run(['systemctl','--user','show-environment'],capture_output=True,text=True)
        for line in result.stdout.splitlines():
            key,separator,value=line.partition('=')
            if separator and key in ('DISPLAY','WAYLAND_DISPLAY','XDG_RUNTIME_DIR'):env[key]=value
    env['__NV_PRIME_RENDER_OFFLOAD']='1';env['__GLX_VENDOR_LIBRARY_NAME']='nvidia'
    cp=os.pathsep.join(str(p) for p in (ROOT/'_work/build/test-classes',ROOT/'dist/Viewpoint-linux-dlss.jar',game/'projectzomboid.jar'))
    cmd=[local['java'],'-Xmx256m','--enable-native-access=ALL-UNNAMED','-Xverify:all',
         '-Dviewpoint.natives='+str(ROOT/'dist/viewpoint-natives'),'-cp',cp,
         'viewpoint.upscale.'+('GpuFrameGenTest' if a.kind=='fg' else 'GpuNgxTest')]
    if a.kind=='fg':cmd.extend((str(a.width),str(a.height)))
    logdir=ROOT/'_work/gpu';logdir.mkdir(parents=True,exist_ok=True)
    # timeout bounds driver hangs; output is local-only and may contain paths.
    with (logdir/f'{a.kind}.log').open('w') as log:
        process=subprocess.Popen(['timeout','120s',*cmd],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,cwd=ROOT,env=env)
        for line in process.stdout:print(line,end='',flush=True);log.write(line)
        status=process.wait()
    if status:raise SystemExit(status)
    manifest_path=ROOT/'dist/manifest.json';manifest=json.loads(manifest_path.read_text())
    manifest.setdefault('gpu_tests',{})[a.kind]={'passed':True,'scope':'hidden-context fixture; actual game scenes and presentation not verified'}
    manifest['gpu_verified']=True
    manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
if __name__=='__main__':main()
