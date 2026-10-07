# iOS SDK compatibility: discover the bundled static fmt library.
find_path(fmt_INCLUDE_DIR fmt/format.h HINTS "${fmt_ROOT}/include" NO_DEFAULT_PATH)
find_library(fmt_LIBRARY NAMES fmt HINTS "${fmt_ROOT}/lib" NO_DEFAULT_PATH)
include(FindPackageHandleStandardArgs)
find_package_handle_standard_args(fmt REQUIRED_VARS fmt_INCLUDE_DIR fmt_LIBRARY)
if(fmt_FOUND AND NOT TARGET fmt::fmt)
  add_library(fmt::fmt UNKNOWN IMPORTED)
  set_target_properties(fmt::fmt PROPERTIES
    IMPORTED_LOCATION "${fmt_LIBRARY}"
    INTERFACE_INCLUDE_DIRECTORIES "${fmt_INCLUDE_DIR}")
endif()
if(fmt_FOUND AND NOT TARGET fmt::fmt-header-only)
  add_library(fmt::fmt-header-only INTERFACE IMPORTED)
  set_target_properties(fmt::fmt-header-only PROPERTIES
    INTERFACE_INCLUDE_DIRECTORIES "${fmt_INCLUDE_DIR}"
    INTERFACE_COMPILE_DEFINITIONS FMT_HEADER_ONLY)
endif()
set(FMT_INCLUDE_DIRS "${fmt_INCLUDE_DIR}")
set(FMT_LIBRARIES "${fmt_LIBRARY}")
