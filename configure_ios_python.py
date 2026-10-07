from pathlib import Path
import re
root=Path("blender")
ios=root/"lib/ios_arm64/python"
choices=[]
for inc in (ios/"include").glob("python3.*"):
    version=inc.name.removeprefix("python")
    if (ios/"lib"/("libpython"+version+".a")).is_file() and (inc/"Python.h").is_file() and (inc/"pyconfig.h").is_file():
        choices.append(version)
assert len(choices)==1, f"Expected one complete iOS Python SDK, got {choices}"
version=choices[0]
hosts=[p for p in (root/"lib/macos_arm64/python/bin").glob("python3.*") if re.fullmatch(r"python3\.\d+",p.name)]
assert hosts, "Missing macOS host Python"
host=max(hosts,key=lambda p:int(p.name.split(".")[-1])).resolve()
p=root/"build_files/cmake/platform/platform_apple.cmake"
s=p.read_text()
assert s.count("set(PYTHON_VERSION 3.13)")==1
s=s.replace("set(PYTHON_VERSION 3.13)",f"set(PYTHON_VERSION {version})")
s=s.replace('set(PYTHON_EXECUTABLE "${CROSSCOMPILE_HOST_LIBDIR}/python/bin/python3.13")',f'set(PYTHON_EXECUTABLE "{host}")')
s=s.replace('set(PYTHON_EXECUTABLE "${CROSSCOMPILE_HOST_LIBDIR}/python/bin/python${PYTHON_VERSION}")',f'set(PYTHON_EXECUTABLE "{host}")')
s=s.replace("WARNING Manually defining Python Version to 3.13 for iOS build",f"iOS Python SDK: {version}; macOS host interpreter selected separately")

# FindPythonLibsUnix writes a cache default; provide complete target SDK cache values.
sdk_cache = (
    f'set(PYTHON_VERSION {version} CACHE STRING "iOS Python SDK version" FORCE)\n'
    f'set(PYTHON_LIBRARY "{(ios/"lib"/("libpython"+version+".a")).resolve()}" CACHE FILEPATH "" FORCE)\n'
    f'set(PYTHON_INCLUDE_DIR "{(ios/"include"/("python"+version)).resolve()}" CACHE PATH "" FORCE)\n'
    f'set(PYTHON_INCLUDE_CONFIG_DIR "{(ios/"include"/("python"+version)).resolve()}" CACHE PATH "" FORCE)\n'
)
anchor = '  set(CROSSCOMPILE_HOST_LIBDIR "${CMAKE_SOURCE_DIR}/lib/macos_arm64")\n'
assert s.count(anchor)==1
s=s.replace(anchor,anchor+sdk_cache)

p.write_text(s)
print("Configured target Python",version,"host",host)
