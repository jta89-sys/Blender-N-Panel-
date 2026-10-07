# Experimental bottom N-panel build package

This is source and a macOS GitHub Actions build workflow, not an installable IPA.
The native sidebar is aligned at the bottom of the 3D viewport with an initial
height of 240 UI units. Existing startup and loaded blend sidebars migrate before
region sizing. The usual N toggle, panel categories and registered add-on panels
remain in the same UI region. Panel contents remain vertically arranged; this
is not a horizontal rewrite of third-party panels.

Includes the previously prepared viewport presets, Safari clipboard URL fix and
in-process extension runner for the experimental Blender 5.0 iOS port.

## Build
Upload this folder's contents, including .github/workflows, to your own GitHub
repository. In Actions run the build-ios-ipa workflow on a macOS runner with
Xcode. Download the resulting Blender-ios-ipa artifact and re-sign the IPA with
your sideloading tool before installation. Builds can be expensive and lengthy.
The workflow runs manually. Builds have been started in this repository and are
being debugged; a failed run's debug artifact is not an IPA. The workflow publishes
a Blender-ios-ipa artifact and a release only after compilation and validation succeed.

## Dependency compatibility
The current ios source expects newer dependencies than its precompiled iOS bundle.
The workflow selects the bundled Python 3.11 target SDK separately from the macOS
host interpreter, restores OpenEXR, OpenImageIO and OpenColorIO discovery and builds missing fmt,
Eigen, Abseil and Ceres for iOS arm64
from the versions and SHA256 checksums in Blender's dependency manifest.
Added dependencies are cached by manifest content. Optional Eigen BLAS/LAPACK,
demos and tests are excluded. Rubberband is disabled because the iOS port already
disables its parent Audaspace audio system. Native compilation
and device behavior remain unverified until a complete build and iPad test pass.

## Validation and limits
Patch anchors checked against the Blender ios branch fetched on 2026-10-07.
Patch application and Python syntax checked locally. No native compilation or
iPad testing performed. This is an experimental implementation, not a verified
UI fix. Test category tabs, panel scrolling, border resizing, portrait/landscape,
N hide/show, old blend loading and several add-on panels on the M1 iPad. Some
panel layout and snapping assumptions may still need native adjustments.
Upstream branch changes fail anchor checks instead of silently skipping patches.
Python fix files target Blender 5.0; update them before targeting other versions.
