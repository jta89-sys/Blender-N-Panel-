"""Use one fmt header version across Blender and the OpenImageIO client API."""
from pathlib import Path
import re, subprocess
root=Path("blender/lib/ios_arm64")
oiio=root/"openimageio/include/OpenImageIO"
fmt=root/"fmt/include"
versions=set()
for name in ("base.h", "core.h", "format.h"):
    p=fmt/"fmt"/name
    if p.is_file():
        versions.update(re.findall(r"^#define FMT_VERSION (\d+)",p.read_text(),re.M))
assert versions == {"120100"}, f"Unexpected external fmt SDK: {versions}"
header=oiio/"detail/fmt.h"
source=header.read_text()
assert "#define OIIO_FMT_H" in source
for name in ("format.h", "ostream.h", "printf.h"):
    old="#include <OpenImageIO/detail/fmt/"+name+">"
    new="#include <fmt/"+name+">"
    assert source.count(old)+source.count(new)==1, "OpenImageIO fmt include changed: "+name
    source=source.replace(old,new)
header.write_text(source)
# These are header-only formatting wrappers. The public OIIO image/string ABI is retained.
probe=Path("fmt-compat-probe.cc")
probe.write_text("""#include <OpenImageIO/string_view.h>
#include <fmt/ranges.h>
#include <vector>
std::string probe() {
  return fmt::format("{} {}", OIIO::string_view("iPad"), std::vector<int>{1, 2});
}
""")
sdk=subprocess.check_output(["xcrun","--sdk","iphoneos","--show-sdk-path"],text=True).strip()
subprocess.run(["xcrun","--sdk","iphoneos","clang++","-target","arm64-apple-ios15.0",
                "-isysroot",sdk,"-std=c++20","-fsyntax-only",str(probe),
                "-I"+str(fmt.resolve()),"-I"+str((oiio.parent).resolve())],check=True)
print("OpenImageIO + fmt ranges compiled for iOS arm64 using fmt 12.1")
