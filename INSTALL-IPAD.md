# Install on iPad from Windows

The build must finish successfully before there is an IPA to install. A debug-logs artifact is not an app.

1. Open this repository's Releases page after a successful build and download `Blender-ios.ipa` and `Blender-ios.ipa.sha256`.
2. Back up your Blender files on the iPad before replacing your existing experimental build.
3. Download Sideloadly from its official site: https://sideloadly.io/ . Follow that site's Windows prerequisites for iTunes and iCloud.
4. Connect the iPad to Windows by USB, unlock it, and accept the device's Trust prompt if shown.
5. Open Sideloadly, select the iPad, and drag the IPA into it. Use the Apple ID Sideload signing mode.
6. Enter your Apple account details directly in Sideloadly on your computer and start installation. Do not put credentials or signing private keys in this repository or in chat.
7. Follow any required developer trust and Developer Mode prompts on the iPad.

Use the same Apple account and bundle identifier as the old sideloaded Blender if you intend to update it in place. Keep the backup regardless.

A free Apple account's app signature normally expires after seven days; Sideloadly supports automatic refreshing while the computer and iPad can connect. The CI package's ad-hoc signature is only a packaging check and is not a trusted installation signature.

## Optional download check

Run PowerShell in the download folder:

```powershell
$actual = (Get-FileHash .\Blender-ios.ipa -Algorithm SHA256).Hash
$expected = ((Get-Content .\Blender-ios.ipa.sha256 -Raw).Trim() -split '\s+')[0]
if ($actual -ne $expected) { throw "IPA checksum mismatch. Download again." }
"IPA checksum matches."
```

## After installation

Test launch, opening and saving a blend file, the bottom N-panel's categories and resize handle, and enabling a simple pure-Python add-on. Native binary add-ons need iOS-compatible dependencies. These changes do not guarantee that all desktop add-ons work on iPad.

Official signing guidance: https://sideloadly.io/faq.html
