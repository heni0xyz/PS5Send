# ps5send.spec
import platform
from PyInstaller.utils.hooks import collect_all, collect_submodules

datas_ctk, binaries_ctk, hiddenimports_ctk = collect_all("customtkinter")
datas_dn, binaries_dn, hiddenimports_dn = collect_all("desktop_notifier")

hidden_dn_extra = collect_submodules("desktop_notifier")

datas = datas_ctk + datas_dn
binaries = binaries_ctk + binaries_dn
hiddenimports = list(set(
    hiddenimports_ctk + 
    hiddenimports_dn + 
    hidden_dn_extra + 
    [
        'desktop_notifier.resources',
        'desktop_notifier.winrt',
        'winsdk',
        'winsdk.windows.foundation',
        'winsdk.windows.ui.notifications'
    ]
))

datas.append(('assets', 'assets'))
datas.append(('PS5Send.ico', '.'))

app_icon = 'PS5Send.ico' if platform.system() == 'Windows' else 'PS5Send.icns'

a = Analysis(
    ['ps5send.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name='PS5Send-Windows' if platform.system() == 'Windows' else 'PS5Send',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=app_icon,
)

if platform.system() == 'Windows':
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=False,
        upx_exclude=[],
        name='PS5Send-Windows',
    )

if platform.system() == 'Darwin':
    app = BUNDLE(
        exe,
        a.binaries,
        a.datas,
        name='PS5Send.app',
        icon=app_icon,
        bundle_identifier='com.heni0xyz.ps5send',
        info_plist={
            'CFBundleDisplayName': 'PS5Send',
            'CFBundleName': 'PS5Send',
            'CFBundleIdentifier': 'com.heni0xyz.ps5send',
            'CFBundleExecutable': 'PS5Send',
            'CFBundlePackageType': 'APPL',
            'CFBundleShortVersionString': '0.0.2',
            'LSUIElement': False,
            'NSHighResolutionCapable': True,
            'CFBundleDocumentTypes': [
                {
                    'CFBundleTypeName': 'Automated Executable and Linkable Format',
                    'CFBundleTypeIconFile': 'PS5Send.icns',
                    'LSItemContentTypes': ['com.heni0xyz.ps5send.aelf'],
                    'LSHandlerRank': 'Owner',
                    'CFBundleTypeRole': 'Editor'
                }
            ],
            'UTExportedTypeDeclarations': [
                {
                    'UTTypeIdentifier': 'com.heni0xyz.ps5send.aelf',
                    'UTTypeDescription': 'Automated Executable and Linkable Format',
                    'UTTypeConformsTo': ['public.data'],
                    'UTTypeTagSpecification': {
                        'public.filename-extension': ['aelf']
                    }
                }
            ]
        },
    )