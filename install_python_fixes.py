from pathlib import Path
import shutil,sys
from validate_app import choose_app, validate
app = choose_app(sys.argv[1])
validate(app)
scripts = list((app/'Assets').glob('*/scripts'))
assert len(scripts) == 1
base=scripts[0]
for filename,dest in [('ipad_viewport_tools.py','startup/ipad_viewport_tools.py'),('wm.py','startup/bl_operators/wm.py'),('ipad_command_runner.py','addons_core/bl_pkg/ipad_command_runner.py'),('bl_extension_utils.py','addons_core/bl_pkg/bl_extension_utils.py')]:
    target=base/dest
    assert target.parent.is_dir(), target
    shutil.copyfile(Path('python_fixes')/filename,target)
print('Installed Blender 5.0 Python fixes; use matching ios upstream source.')
