"""Build missing eigen for iOS using the version and SHA256 in Blender's dependency manifest."""
from pathlib import Path
import hashlib, re, subprocess, tarfile, urllib.request
root=Path("blender")
manifest=(root/"build_files/build_environment/cmake/versions.cmake").read_text()
def value(name):
    match=re.search(r"set\("+name+r"\s+([^\s)]+)\)",manifest)
    if not match: raise RuntimeError("Missing dependency manifest value: "+name)
    return match[1]
version=value("EIGEN_VERSION")
digest=value("EIGEN_HASH")
if value("EIGEN_HASH_TYPE") != "SHA256": raise RuntimeError("Expected SHA256")
prefix=(root/"lib/ios_arm64/eigen").resolve()
if list((prefix/"share").glob("**/Eigen3Config.cmake")) or list((prefix/"lib").glob("**/Eigen3Config.cmake")):
    print("Using complete precompiled iOS eigen SDK")
else:
    archive=Path("eigen-source.tar.gz")
    url=value("EIGEN_URI").replace("${EIGEN_VERSION}",version)
    urllib.request.urlretrieve(url,archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=digest:
        raise RuntimeError("eigen source checksum mismatch")
    dest=Path("eigen-source")
    dest.mkdir(exist_ok=True)
    with tarfile.open(archive) as tf:
        for member in tf.getmembers():
            target=(dest/member.name).resolve()
            if not target.is_relative_to(dest.resolve()) or member.issym() or member.islnk():
                raise RuntimeError("Unsafe eigen archive member")
        tf.extractall(dest)
    source=dest/("eigen-"+version)
    subprocess.run(["cmake","-S",str(source),"-B","eigen-build","-G","Xcode",
                    "-DCMAKE_SYSTEM_NAME=iOS","-DCMAKE_OSX_SYSROOT=iphoneos",
                    "-DCMAKE_OSX_ARCHITECTURES=arm64","-DCMAKE_OSX_DEPLOYMENT_TARGET=15.0",
                    "-DCMAKE_INSTALL_PREFIX="+str(prefix),"-DBUILD_SHARED_LIBS=OFF",
                    "-DBUILD_TESTING=OFF","-DEIGEN_BUILD_TESTING=OFF","-DEIGEN_BUILD_DOC=OFF",
                    "-DEIGEN_BUILD_BLAS=OFF","-DEIGEN_BUILD_LAPACK=OFF","-DEIGEN_BUILD_DEMOS=OFF",
                    "-DCMAKE_XCODE_ATTRIBUTE_CODE_SIGNING_ALLOWED=NO"],check=True)
    subprocess.run(["cmake","--build","eigen-build","--config","Release","--target","install"],check=True)
    print("Built eigen",version,"for iOS arm64")
