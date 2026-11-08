#!/usr/bin/env python3
"""Build a local replacement from the user's own, version-pinned Viewpoint JAR."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import tarfile
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parents[1]
VERSIONS=json.loads((ROOT/'config/versions.json').read_text())
LOCK=json.loads((ROOT/'config/sdk-lock.json').read_text())
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run(*args):subprocess.run([str(a) for a in args],check=True,cwd=ROOT)
def fetch(path,url,sha,offline):
    if path.is_file() and digest(path)==sha:return
    if offline:raise SystemExit(f'Missing or invalid cached dependency: {path}')
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.download')
    print(f'Downloading {url}',flush=True)
    with urllib.request.urlopen(url,timeout=90) as response,temporary.open('wb') as output:
        shutil.copyfileobj(response,output)
    if digest(temporary)!=sha:raise SystemExit(f'Checksum mismatch: {url}')
    os.replace(temporary,path)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--viewpoint-jar',type=Path,required=True)
    p.add_argument('--game-dir',type=Path,required=True,help='Folder containing projectzomboid.jar and jre64/')
    p.add_argument('--java',type=Path,help='Java 25 executable; defaults to the game runtime')
    p.add_argument('--deps-dir',type=Path,default=ROOT/'_work/deps')
    p.add_argument('--offline',action='store_true')
    a=p.parse_args()
    if platform.system()!='Linux' or platform.machine() not in ('x86_64','amd64'):raise SystemExit('Linux x86-64 only')
    original=a.viewpoint_jar.resolve();game=a.game_dir.resolve();java=(a.java or game/'jre64/bin/java').resolve()
    if digest(original)!=VERSIONS['viewpoint_original_sha256']:
        raise SystemExit('Unsupported original Viewpoint JAR fingerprint. Restore a supported unmodified copy; do not force this build onto a different version.')
    if not (game/'projectzomboid.jar').is_file() or not java.is_file():raise SystemExit('Invalid native game directory or Java runtime')
    if not shutil.which('g++'):raise SystemExit('g++ is required')
    deps=a.deps_dir.resolve();tools=deps/'tools';sdk=deps/'sdk'
    for name,info in VERSIONS['tools'].items():fetch(tools/name,info['url'],info['sha256'],a.offline)
    for name,sha in LOCK['files'].items():
        target=sdk/(name if name.startswith('include/') else 'lib/'+name.rsplit('/',1)[1])
        fetch(target,f'https://raw.githubusercontent.com/NVIDIA/DLSS/{LOCK["sdk_commit"]}/{name}',sha,a.offline)
    headers=sdk/'Vulkan-Headers-1.4.321'
    if not (headers/'include/vulkan/vulkan.h').is_file():
        with tarfile.open(tools/'vulkan-headers.tar.gz') as archive:archive.extractall(sdk,filter='data')
    work=ROOT/'_work/build';generated=work/'src/viewpoint/upscale';generated.mkdir(parents=True,exist_ok=True)
    # Each invocation starts from the pinned original, never from a previous patch.
    with zipfile.ZipFile(original) as archive:
        for entry in archive.namelist():
            if entry.startswith('viewpoint/upscale/') and entry.endswith('.class'):
                local=work/'input'/entry;local.parent.mkdir(parents=True,exist_ok=True);local.write_bytes(archive.read(entry))
        for name in ('VulkanDevice','Crossing','SharedImage','NativeFiles','Upscaling'):
            cls=work/'input/viewpoint/upscale'/f'{name}.class'
            run(java,'-Xmx128m','-jar',tools/'cfr.jar',cls,'--outputdir',work/'src','--silent','true')
    for script in ('patch_sources.py','harden_resources.py','patch_integration.py'):run('python3',ROOT/'scripts'/script,work)
    stage=ROOT/'dist/viewpoint-natives';stage.mkdir(parents=True,exist_ok=True)
    for source,target in (('viewpoint_ngx.cpp','libviewpoint_ngx.so'),('viewpoint_dlssg.cpp','libviewpoint_dlssg.so')):
        run('nice','-n','15','g++','-O1','-shared','-fPIC','-std=c++17','-Wall','-Wextra','-Wno-missing-field-initializers',
            '-I'+str(sdk/'include'),'-I'+str(headers/'include'),'-o',stage/target,ROOT/'native'/source,
            sdk/'lib/libnvsdk_ngx.a','-Wl,-z,defs,--exclude-libs,ALL','-l:libvulkan.so.1','-ldl','-lpthread')
    for name in ('libnvidia-ngx-dlss.so.310.9.16','libnvidia-ngx-dlssg.so.310.9.16'):shutil.copy2(sdk/'lib'/name,stage/name)
    records=[]
    for lib in sorted(stage.glob('*.so*')):
        url=(f'https://raw.githubusercontent.com/NVIDIA/DLSS/{LOCK["sdk_commit"]}/lib/Linux_x86_64/rel/{lib.name}'
             if lib.name.startswith('libnvidia') else lib.as_uri())
        records.append(f'new Library("{lib.name}", {lib.stat().st_size}L, "{digest(lib)}", "{url}", null)')
    import re
    f=generated/'NativeFiles.java';text=f.read_text()
    text,count=re.subn(r'        DLSS\("NVIDIA DLSS".*?;\n','        DLSS("NVIDIA DLSS", "NVIDIA (unofficial Linux adapter)", List.of('+', '.join(records)+'));\n',text,count=1)
    if count!=1:raise SystemExit('Unrecognized NativeFiles layout')
    marker='        Status status;\n'
    text=text.replace(marker,'''        if (set == Set.DLSS && (!NativeFiles.file("libviewpoint_ngx.so").isFile() || !NativeFiles.file("libviewpoint_dlssg.so").isFile())) {
            NativeFiles.failed(set, NativeFiles.status(set), new IOException("Local Linux adapters are missing; reinstall this patch."));
            return;
        }
'''+marker,1);f.write_text(text)
    classes=work/'classes';classes.mkdir(parents=True,exist_ok=True)
    sources=list((work/'src').rglob('*.java'))+list((ROOT/'java').rglob('*.java'))+list((ROOT/'tests').glob('*.java'))
    cp=str(original)+os.pathsep+str(game/'projectzomboid.jar')
    run(java,'-Xmx256m','-jar',tools/'ecj.jar','-25','-proc:none','-warn:none','-cp',cp,'-d',classes,*sources)
    output=ROOT/'dist/Viewpoint-linux-dlss.jar'
    replacements={str(f.relative_to(classes)):f for f in (classes/'viewpoint/upscale').glob('*.class')
                  if f.name.split('$')[0].split('.')[0] not in ('OfflineNgxTest','GpuNgxTest','GpuFrameGenTest')}
    allowed={'VulkanDevice','Crossing','SharedImage','NativeFiles','Upscaling','DlssVendor','LinuxNgx','FrameGeneration','LinuxFrameNgx','FrameGenConstants'}
    if any(n.rsplit('/',1)[1].split('$')[0].split('.')[0] not in allowed for n in replacements):raise SystemExit('Unexpected output class')
    with zipfile.ZipFile(original) as old,zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as new:
        for entry in old.infolist():new.writestr(entry,replacements[entry.filename].read_bytes() if entry.filename in replacements else old.read(entry.filename))
        for name in replacements.keys()-set(old.namelist()):new.writestr(name,replacements[name].read_bytes())
    test_classes=work/'test-classes/viewpoint/upscale';test_classes.mkdir(parents=True,exist_ok=True)
    for name in ('OfflineNgxTest','GpuNgxTest','GpuFrameGenTest'):shutil.copy2(classes/'viewpoint/upscale'/f'{name}.class',test_classes/f'{name}.class')
    run(java,'-Xmx128m','--enable-native-access=ALL-UNNAMED','-Xverify:all','-Dviewpoint.natives='+str(stage),
        '-cp',str(work/'test-classes')+os.pathsep+str(output)+os.pathsep+str(game/'projectzomboid.jar'),
        'viewpoint.upscale.OfflineNgxTest',stage/'libviewpoint_ngx.so')
    manifest={'upstream_version':VERSIONS['viewpoint_version'],'original_sha256':digest(original),'patched_sha256':digest(output),
              'files':{str(f.relative_to(ROOT/'dist')):digest(f) for f in [output,*sorted(stage.glob('*.so*'))]},
              'offline_verified':True,'gpu_verified':False,'game_scene_verified':False,'requires_game_exit_before_install':True}
    (ROOT/'dist/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (ROOT/'_work/local-build.json').write_text(json.dumps({'game_dir':str(game),'java':str(java),'viewpoint_jar':str(original)},indent=2)+'\n')
    print('Build and offline checks passed. Nothing installed. GPU tests and game exit are separate steps.')
if __name__=='__main__':main()
