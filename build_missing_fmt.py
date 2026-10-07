"""Build missing fmt for iOS using the version and SHA256 in Blender's dependency manifest."""
from pathlib import Path
import hashlib, re, subprocess, tarfile, urllib.request
root=Path("blender")
manifest=(root/"build_files/build_environment/cmake/versions.cmake").read_text()
def value(name):
    match=re.search(r"set\("+name+r"\s+([^\s)]+)\)",manifest)
    if not match: raise RuntimeError("Missing dependency manifest value: "+name)
    return match[1]
version=value("FMT_VERSION")
digest=value("FMT_HASH")
if value("FMT_HASH_TYPE") != "SHA256": raise RuntimeError("Expected SHA256")
prefix=(root/"lib/ios_arm64/fmt").resolve()
if (prefix/"lib/libfmt.a").is_file() and (prefix/"include/fmt/format.h").is_file():
    print("Using complete precompiled iOS fmt SDK")
else:
    archive=Path("fmt-source.tar.gz")
    url="https://github.com/fmtlib/fmt/archive/refs/tags/"+version+".tar.gz"
    urllib.request.urlretrieve(url,archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=digest:
        raise RuntimeError("fmt source checksum mismatch")
    dest=Path("fmt-source")
    dest.mkdir(exist_ok=True)
    with tarfile.open(archive) as tf:
        for member in tf.getmembers():
            target=(dest/member.name).resolve()
            if not target.is_relative_to(dest.resolve()) or member.issym() or member.islnk():
                raise RuntimeError("Unsafe fmt archive member")
        tf.extractall(dest)
    source=dest/("fmt-"+version)
    subprocess.run(["cmake","-S",str(source),"-B","fmt-build","-G","Xcode",
                    "-DCMAKE_SYSTEM_NAME=iOS","-DCMAKE_OSX_SYSROOT=iphoneos",
                    "-DCMAKE_OSX_ARCHITECTURES=arm64","-DCMAKE_OSX_DEPLOYMENT_TARGET=15.0",
                    "-DCMAKE_INSTALL_PREFIX="+str(prefix),"-DBUILD_SHARED_LIBS=OFF",
                    "-DFMT_TEST=OFF","-DFMT_DOC=OFF",
                    "-DCMAKE_XCODE_ATTRIBUTE_CODE_SIGNING_ALLOWED=NO"],check=True)
    subprocess.run(["cmake","--build","fmt-build","--config","Release","--target","install"],check=True)
    print("Built fmt",version,"for iOS arm64")
