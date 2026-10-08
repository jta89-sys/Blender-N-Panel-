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

# Blender's current source uses the public Python 3.13 integer conversion API.
# Older bundled CPython SDKs expose the same int conversion as _PyLong_AsInt.
if tuple(map(int, version.split("."))) < (3, 13):
    header = root/"source/blender/python/generic/py_capi_utils.hh"
    source = header.read_text()
    anchor = "  return int32_t(PyLong_AsInt(value));"
    assert source.count(anchor) == 1, "Python integer API patch anchor changed"
    replacement = """#if PY_VERSION_HEX < 0x030D0000
  return int32_t(_PyLong_AsInt(value));
#else
  return int32_t(PyLong_AsInt(value));
#endif"""
    header.write_text(source.replace(anchor, replacement))
    print("Enabled pre-3.13 CPython integer API compatibility")

# Python 3.11/3.12 already expose _PyArg_CheckPositional as a macro.
# Re-declaring it expands that macro where a function name is expected.
compat = root/"source/blender/python/generic/python_compat.hh"
source = compat.read_text()
anchor = "int _PyArg_CheckPositional(const char *name, Py_ssize_t nargs, Py_ssize_t min, Py_ssize_t max);"
assert source.count(anchor) == 1, "Python argument API patch anchor changed"
compat.write_text(source.replace(anchor, "#ifndef _PyArg_CheckPositional\n" + anchor + "\n#endif"))
print("Guarded existing CPython argument-check macro")

# The matching implementation must also be excluded when CPython supplies it.
compat_impl = root/"source/blender/python/generic/python_compat.cc"
source = compat_impl.read_text()
marker = "/* Removed in Python 3.13. */"
assert source.count(marker) == 1, "Python compatibility implementation anchor changed"
assert source.rstrip().endswith("}"), "Unexpected Python compatibility implementation ending"
compat_impl.write_text(source.replace(marker, "#ifndef _PyArg_CheckPositional\n" + marker) + "\n#endif\n")
print("Guarded existing CPython argument-check implementation")

# Freestyle copies a PyLong using the 3.12+ layout (long_value); 3.11 stores
# the sign/size in ob_size and the digits in ob_digit.
fs_convert = root/"source/blender/freestyle/intern/python/BPy_Convert.cpp"
source = fs_convert.read_text()
old = "  memcpy(&result->long_value, &value_py->long_value, sizeof(result->long_value));\n"
assert source.count(old) == 1, "Freestyle PyLong anchor changed"
new = ("#if PY_VERSION_HEX >= 0x030C0000\n" + old +
       "#else\n"
       "  Py_SET_SIZE(result, Py_SIZE(value_py));\n"
       "  result->ob_digit[0] = value_py->ob_digit[0];\n"
       "#endif\n")
fs_convert.write_text(source.replace(old, new))
print("Patched Freestyle PyLong subtype copy for pre-3.12 CPython")

# Supply newer public APIs to the older iOS SDK through a pinned compatibility header.
import hashlib
from urllib.request import urlopen
compat_sha = "ebbf075e3bd317e11a39215c50debd3f301590de"
compat_hash = "bac7a94e7625cf3eed5ff54104f46d370f9d82e1c5acf2af1e11d0e3029c15a6"
with urlopen(f"https://raw.githubusercontent.com/python/pythoncapi-compat/{compat_sha}/pythoncapi_compat.h", timeout=60) as response:
    data = response.read()
assert hashlib.sha256(data).hexdigest() == compat_hash, "Python C API compatibility checksum mismatch"
sdk_include = ios/"include"/("python"+version)
(sdk_include/"pythoncapi_compat.h").write_bytes(data)
shim = """#pragma once
#define BLENDER_IPAD_PYTHON_COMPAT 1
#include "pythoncapi_compat.h"
/* Python 3.11 stores the raised exception as type/value/traceback. */
#if PY_VERSION_HEX < 0x030C0000
static inline PyObject *PyErr_GetRaisedException(void)
{
  PyObject *type = NULL, *value = NULL, *traceback = NULL;
  PyErr_Fetch(&type, &value, &traceback);
  if (type == NULL) {
    return NULL;
  }
  PyErr_NormalizeException(&type, &value, &traceback);
  if (value != NULL && traceback != NULL) {
    PyException_SetTraceback(value, traceback);
  }
  Py_XDECREF(type);
  Py_XDECREF(traceback);
  return value;
}
static inline void PyErr_SetRaisedException(PyObject *exception)
{
  if (exception == NULL) {
    PyErr_Clear();
    return;
  }
  PyObject *type = (PyObject *)Py_TYPE(exception);
  Py_INCREF(type);
  PyObject *traceback = PyException_GetTraceback(exception);
  PyErr_Restore(type, exception, traceback);
}
#endif
"""
(sdk_include/"blender_ipad_python_compat.h").write_text(shim)
python_header = sdk_include/"Python.h"
source = python_header.read_text()
include = '#include "blender_ipad_python_compat.h"'
if include not in source:
    python_header.write_text(source + "\n" + include + "\n")
print("Installed pinned Python C API compatibility in iOS target SDK")

# Permit the older target only when the audited compatibility layer is present.
intern_header = root/"source/blender/python/intern/bpy_capi_utils.hh"
source = intern_header.read_text()
anchor = "#if PY_VERSION_HEX < 0x030d0000"
assert source.count(anchor) == 1, "Python minimum-version guard changed"
intern_header.write_text(source.replace(anchor,
    "#if PY_VERSION_HEX < 0x030d0000 && !defined(BLENDER_IPAD_PYTHON_COMPAT)"))

# Driver opcode safety remains enabled. Only compile cases present in this SDK.
# Python 3.11 spellings below are from Blender v3.6's approved opcode list.
driver = root/"source/blender/python/intern/bpy_driver_bytecode.cc"
source = driver.read_text()
assert source.count("static bool is_opcode_secure") == 1
assert source.count("  switch (opcode) {") == 1
legacy = (
    "UNARY_POSITIVE", "LIST_TO_TUPLE", "JUMP_IF_FALSE_OR_POP",
    "JUMP_IF_TRUE_OR_POP", "POP_JUMP_FORWARD_IF_FALSE",
    "POP_JUMP_FORWARD_IF_TRUE", "POP_JUMP_FORWARD_IF_NONE",
    "POP_JUMP_FORWARD_IF_NOT_NONE", "POP_JUMP_BACKWARD_IF_FALSE",
    "POP_JUMP_BACKWARD_IF_TRUE", "POP_JUMP_BACKWARD_IF_NONE",
    "POP_JUMP_BACKWARD_IF_NOT_NONE", "KW_NAMES", "PRECALL",
)
cases = "\n".join("    OK_OP(" + op + ")" for op in legacy)
source = source.replace("  switch (opcode) {",
    "  switch (opcode) {\n#  if PY_VERSION_HEX < 0x030C0000\n" + cases + "\n#  endif")
source, count = re.subn(r"(?m)^(    OK_OP\(([A-Z_0-9]+)\).*)$",
    lambda m: "#  ifdef " + m.group(2) + "\n" + m.group(1) + "\n#  endif", source)
assert count > 60, "Unexpected driver opcode whitelist"
driver.write_text(source)
print("Matched driver safety whitelist to target Python opcodes")

# The prebuilt Python 3.11 archive contains _blake2 wrappers but omits the
# portable BLAKE2 implementations. Supply CPython's matching 3.11 reference
# implementations instead of disabling hashlib or replacing its algorithms.
if version == "3.11":
    import subprocess
    from urllib.request import urlopen

    archive = ios/"lib"/("libpython"+version+".a")
    required = {
        "_blake2b_final", "_blake2b_init_param", "_blake2b_update",
        "_blake2s_final", "_blake2s_init_param", "_blake2s_update",
    }

    def defined_symbols():
        output = subprocess.check_output(
            ["xcrun", "nm", "-g", "-U", str(archive)], text=True)
        return {line.split()[-1] for line in output.splitlines()
                if line.split() and not line.rstrip().endswith(":")}

    present = required & defined_symbols()
    if present != required:
        assert not present, f"Partial BLAKE2 implementation in Python SDK: {present}"
        work = Path("build_python_blake2")
        work.mkdir(exist_ok=True)
        # CPython v3.11.9, pinned to its immutable source commit.
        commit = "de54cf5be371a6f5e2e9f208c38def5f81d3ef02"
        base = f"https://raw.githubusercontent.com/python/cpython/{commit}/Modules/_blake2/impl/"
        for name in ("blake2.h", "blake2-impl.h", "blake2b-ref.c", "blake2s-ref.c"):
            with urlopen(base + name, timeout=60) as response:
                (work/name).write_bytes(response.read())
        # Verify both reference implementations against the host hashlib.
        import hashlib
        probe = work/"probe.c"
        probe.write_text(
            '#include "blake2.h"\n#include <stdio.h>\n#include <string.h>\n'
            'int main(void) { unsigned char out[64]; '
            'const char *inputs[] = {"", "abc"}; '
            'for (int n=0; n<2; ++n) { '
            'if(blake2b(out,inputs[n],NULL,64,strlen(inputs[n]),0)) return 1; '
            'for(int i=0;i<64;++i) printf("%02x",out[i]); puts(""); '
            'if(blake2s(out,inputs[n],NULL,32,strlen(inputs[n]),0)) return 1; '
            'for(int i=0;i<32;++i) printf("%02x",out[i]); puts(""); } return 0; }\n')
        executable = (work/"probe").resolve()
        subprocess.run([
            "xcrun", "--sdk", "macosx", "clang", "-O2", "-std=c99",
            str(probe), str(work/"blake2b-ref.c"), str(work/"blake2s-ref.c"),
            "-o", str(executable),
        ], check=True)
        actual = subprocess.check_output([str(executable)], text=True).splitlines()
        expected = [digest(data).hexdigest() for data in (b"", b"abc")
                    for digest in (hashlib.blake2b, hashlib.blake2s)]
        assert actual == expected, "BLAKE2 reference digest verification failed"
        sdk = subprocess.check_output(
            ["xcrun", "--sdk", "iphoneos", "--show-sdk-path"], text=True).strip()
        objects = []
        for name in ("blake2b-ref", "blake2s-ref"):
            obj = work/(name + ".o")
            subprocess.run([
                "xcrun", "--sdk", "iphoneos", "clang",
                "-target", "arm64-apple-ios15.0", "-isysroot", sdk,
                "-O2", "-std=c99", "-c", str(work/(name + ".c")),
                "-o", str(obj),
            ], check=True)
            objects.append(str(obj))
        subprocess.run(["xcrun", "ar", "-r", str(archive), *objects], check=True)
        subprocess.run(["xcrun", "ranlib", str(archive)], check=True)
        assert required <= defined_symbols(), "Python BLAKE2 symbols still missing"
        print("Restored six missing Python BLAKE2 symbols for iOS arm64")
    else:
        print("Python BLAKE2 symbols already present")
