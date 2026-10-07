"""Fail CI if selected app is a macOS/simulator build or missing iOS runtime data."""
import plistlib,subprocess,sys
from pathlib import Path

def choose_app(root):
    candidates=list(Path(root).rglob('Blender.app'))
    candidates.sort(key=lambda p:('iphoneos' not in str(p).lower(),'release' not in str(p).lower(),str(p)))
    if not candidates:raise ValueError('Blender.app not found')
    return candidates[0]

def validate(app,run=subprocess.check_output):
    with (app/'Info.plist').open('rb') as f:info=plistlib.load(f)
    binary=app/info['CFBundleExecutable']
    if not binary.is_file():raise ValueError('App executable missing')
    arch=run(['lipo','-archs',str(binary)],text=True)
    if 'arm64' not in arch.split():raise ValueError('Not an arm64 app')
    build=run(['xcrun','vtool','-show-build',str(binary)],text=True)
    platforms=[line.strip().split()[-1] for line in build.splitlines() if line.strip().startswith('platform ')]
    if not platforms or any(p not in {'IOS','2'} for p in platforms):raise ValueError('Not an iOS device binary: '+str(platforms))
    if not list(app.rglob('startup.blend')):raise ValueError('Bundled startup.blend missing')
    if not list(app.rglob('scripts/startup')):raise ValueError('Bundled Blender startup scripts missing')
    print('Validated iOS arm64 app:',app)

if __name__=='__main__':validate(choose_app(sys.argv[1]))
