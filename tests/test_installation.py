"""Exercise real hash guards, file replacement and rollback on disposable fixtures only."""
from pathlib import Path
from types import SimpleNamespace
import importlib.util
import json
import shutil
import tempfile

repo=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('patch_manage',repo/'scripts/manage.py')
manage=importlib.util.module_from_spec(spec);spec.loader.exec_module(manage)
local=json.loads((repo/'_work/local-build.json').read_text())
with tempfile.TemporaryDirectory(prefix='install-fixture-',dir=repo/'_work') as temporary:
    fixture=Path(temporary);(fixture/'dist').symlink_to(repo/'dist',target_is_directory=True)
    target=fixture/'mock-workshop/Viewpoint.jar';target.parent.mkdir()
    shutil.copy2(local['viewpoint_jar'],target)
    native=fixture/'mock-cache/viewpoint-natives';native.mkdir(parents=True)
    sentinel=native/'libviewpoint_ngx.so';sentinel.write_bytes(b'previous mock library')
    manage.ROOT=fixture
    # The targets are disposable fixture files, never the installed game.
    manage.game_processes=lambda:[]
    a=SimpleNamespace(viewpoint_jar=target,zomboid_dir=native.parent,apply=False,game_exited=True)
    before=manage.digest(target);manage.install(a)
    assert not (fixture/'state').exists() and manage.digest(target)==before
    a.apply=True;manage.install(a)
    assert manage.digest(target)==json.loads((repo/'dist/manifest.json').read_text())['patched_sha256']
    target.write_bytes(b'changed after installation')
    try:manage.rollback(SimpleNamespace(apply=False,game_exited=True))
    except SystemExit:pass
    else:raise AssertionError('rollback accepted a changed file')
    shutil.copy2(repo/'dist/Viewpoint-linux-dlss.jar',target)
    manage.rollback(SimpleNamespace(apply=True,game_exited=True))
    assert manage.digest(target)==before
    assert sentinel.read_bytes()==b'previous mock library'
    assert not (native/'libviewpoint_dlssg.so').exists()
    assert not (fixture/'state/active.json').exists()
print('PASS: dry run, backed-up installation, changed-file rollback guard, restoration and new-library removal on disposable fixtures.')
