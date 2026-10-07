"""Build Ceres and Abseil for iOS from Blender's checksum-pinned dependency manifest."""
from pathlib import Path
import hashlib, re, subprocess, tarfile, urllib.request
root=Path("blender")
manifest=(root/"build_files/build_environment/cmake/versions.cmake").read_text()
def value(name):
    m=re.search(r"set\("+name+r"\s+([^\s)]+)\)",manifest)
    if not m: raise RuntimeError("Missing manifest value: "+name)
    return m[1]
sdk=(root/"lib/ios_arm64").resolve()
recipes=[
    ("ABSEIL","abseil",["-DABSL_BUILD_TESTING=OFF","-DABSL_ENABLE_INSTALL=ON","-DABSL_PROPAGATE_CXX_STD=ON"]),
    ("CERES","ceres",["-DBUILD_TESTING=OFF","-DBUILD_EXAMPLES=OFF","-DBUILD_BENCHMARKS=OFF",
                      "-DSUITESPARSE=OFF","-DLAPACK=OFF","-DACCELERATESPARSE=OFF","-DUSE_CUDA=OFF",
                      "-DCMAKE_PREFIX_PATH="+str(sdk/"abseil")+";"+str(sdk/"eigen"),
                      "-Dabsl_DIR="+str(sdk/"abseil/lib/cmake/absl"),
                      "-DEigen3_DIR="+str(sdk/"eigen/share/eigen3/cmake"),
                      "-DCMAKE_FIND_ROOT_PATH_MODE_PACKAGE=NEVER"]),
]
for name,folder,args in recipes:
    prefix=sdk/folder
    config="abslConfig.cmake" if name=="ABSEIL" else "CeresConfig.cmake"
    if list(prefix.glob("**/"+config)):
        print("Using installed",folder)
        continue
    version=value(name+"_VERSION")
    url=value(name+"_URI").replace("${"+name+"_VERSION}",version)
    archive=Path(folder+"-verified-source.tar.gz")
    urllib.request.urlretrieve(url,archive)
    if value(name+"_HASH_TYPE")!="SHA256" or hashlib.sha256(archive.read_bytes()).hexdigest()!=value(name+"_HASH"):
        raise RuntimeError(folder+" source checksum mismatch")
    dest=Path(folder+"-source")
    dest.mkdir(exist_ok=True)
    with tarfile.open(archive) as tf:
        for member in tf.getmembers():
            target=(dest/member.name).resolve()
            if not target.is_relative_to(dest.resolve()) or member.issym() or member.islnk():
                raise RuntimeError("Unsafe source archive member")
        tf.extractall(dest)
    roots=[p for p in dest.iterdir() if p.is_dir() and (p/"CMakeLists.txt").is_file()]
    if len(roots)!=1: raise RuntimeError("Expected one "+folder+" source root")
    build=folder+"-build"
    subprocess.run(["cmake","-S",str(roots[0]),"-B",build,"-G","Xcode",
                    "-DCMAKE_SYSTEM_NAME=iOS","-DCMAKE_OSX_SYSROOT=iphoneos",
                    "-DCMAKE_OSX_ARCHITECTURES=arm64","-DCMAKE_OSX_DEPLOYMENT_TARGET=15.0",
                    "-DCMAKE_CXX_STANDARD=20","-DCMAKE_INSTALL_PREFIX="+str(prefix),
                    "-DBUILD_SHARED_LIBS=OFF","-DCMAKE_XCODE_ATTRIBUTE_CODE_SIGNING_ALLOWED=NO",*args],check=True)
    subprocess.run(["cmake","--build",build,"--config","Release","--target","install","--parallel","3","--","-quiet"],check=True)
    print("Built",folder,version,"for iOS arm64")
