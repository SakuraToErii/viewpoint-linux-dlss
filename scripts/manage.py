#!/usr/bin/env python3
"""Dry-run installation and hash-guarded rollback. Never launches the game."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import os
import shutil
import uuid

ROOT=Path(__file__).resolve().parents[1]
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def atomic(source,target):
    target.parent.mkdir(parents=True,exist_ok=True)
    temporary=target.with_name(target.name+'.linux-dlss-'+uuid.uuid4().hex+'.tmp')
    shutil.copy2(source,temporary);os.replace(temporary,target)
def game_processes():
    found=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            args=(p/'cmdline').read_bytes().split(b'\0')
            exe=Path(args[0].decode(errors='replace')).name.lower()
            if exe in ('projectzomboid64','projectzomboid64.exe'):found.append(p.name)
        except (OSError,IndexError):pass
    return found
def require_exit(a):
    if not a.game_exited:raise SystemExit('Confirm game exit with the user before passing --game-exited.')
    running=game_processes()
    if running:raise SystemExit('Project Zomboid is still running: '+', '.join(running))
def install(a):
    manifest=json.loads((ROOT/'dist/manifest.json').read_text())
    for name,sha in manifest['files'].items():
        if digest(ROOT/'dist'/name)!=sha:raise SystemExit('Build output changed: '+name)
    target=a.viewpoint_jar.resolve();gamehash=digest(target)
    accepted={manifest['original_sha256']}
    # Fingerprints of the two local, tested proof-of-concept predecessors.
    accepted.update(('8c6a5c91399e4d08d5e5beafc318b44eeef4dbc8cbabab784d14cb3f65f0d9cf',
                     '51f86b02462a021d2335bd3c151f785c1af4a429b9736d5ec98448a14c13d78b'))
    active=ROOT/'state/active.json'
    if active.exists():accepted.add(json.loads(active.read_text())['patched_sha256'])
    if gamehash not in accepted:raise SystemExit('Unsupported installed JAR fingerprint; inspect the update before applying this patch.')
    changes=[(ROOT/'dist'/name,a.zomboid_dir.resolve()/name) for name in manifest['files'] if name.startswith('viewpoint-natives/')]
    changes.append((ROOT/'dist/Viewpoint-linux-dlss.jar',target))
    for source,destination in changes:print(f'{source} -> {destination}')
    if not a.apply:print('DRY RUN. No files changed.');return
    require_exit(a)
    backup=ROOT/'state/backups'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');backup.mkdir(parents=True)
    entries=[]
    for i,(source,destination) in enumerate(changes):
        saved=backup/f'{i}-{destination.name}'
        if destination.exists():shutil.copy2(destination,saved)
        entries.append({'target':str(destination),'backup':str(saved) if saved.exists() else None,'new_sha256':digest(source)})
    (backup/'rollback.json').write_text(json.dumps(entries,indent=2)+'\n')
    try:
        for source,destination in changes:atomic(source,destination)
    except BaseException:
        for item in reversed(entries):
            destination=Path(item['target'])
            if item['backup']:atomic(Path(item['backup']),destination)
            elif destination.exists():os.replace(destination,backup/('failed-'+destination.name))
        raise
    active.write_text(json.dumps({'backup':str(backup),'patched_sha256':manifest['patched_sha256'],'game_jar':str(target)},indent=2)+'\n')
    print('Installed with backup: '+str(backup))
    print('Review any changed-JAR approval prompt in ZombieBuddy yourself. No approval records were edited.')
def rollback(a):
    active=ROOT/'state/active.json';state=json.loads(active.read_text());backup=Path(state['backup'])
    entries=json.loads((backup/'rollback.json').read_text())
    for item in entries:
        target=Path(item['target'])
        if not target.exists() or digest(target)!=item['new_sha256']:raise SystemExit('File changed since install; review before restoring: '+str(target))
        print('Restore '+str(target))
    if not a.apply:print('DRY RUN. No files changed.');return
    require_exit(a)
    for item in reversed(entries):
        target=Path(item['target'])
        if item['backup']:atomic(Path(item['backup']),target)
        else:os.replace(target,backup/('removed-'+target.name))
    os.replace(active,backup/'rolled-back-active.json')
    print('Previous installation restored. Removed patch files retained in the backup directory.')
def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    install_parser=sub.add_parser('install');install_parser.add_argument('--viewpoint-jar',type=Path,required=True)
    install_parser.add_argument('--zomboid-dir',type=Path,default=Path.home()/'Zomboid')
    rollback_parser=sub.add_parser('rollback')
    for s in (install_parser,rollback_parser):s.add_argument('--apply',action='store_true');s.add_argument('--game-exited',action='store_true')
    a=p.parse_args();install(a) if a.action=='install' else rollback(a)
if __name__=='__main__':main()
