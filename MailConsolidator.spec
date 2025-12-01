import sys
import os
from os.path import join, dirname, exists

block_cipher = None

a = Analysis(
    ['main.py', 'gui.py', 'core.py', 'mail_client.py', 'crypto_helper.py', 'tray_icon.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'pystray',
        'PIL',
        'psutil',
        'yaml',
        'cryptography',
        'tkinter',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Miniconda/Anaconda環境向けのTcl/Tkパス設定
# sys.prefix/Library/lib にあることが多い
conda_lib_path = join(sys.prefix, 'Library', 'lib')
tcl_dir = None
tk_dir = None

if exists(conda_lib_path):
    # Library/lib 内を探索して tcl8.x, tk8.x を探す
    for item in os.listdir(conda_lib_path):
        full_path = join(conda_lib_path, item)
        if not os.path.isdir(full_path):
            continue
            
        if item.startswith('tcl8'):
            tcl_dir = full_path
        elif item.startswith('tk8'):
            tk_dir = full_path

# 見つからない場合は標準的な場所も探す
if not tcl_dir or not tk_dir:
    base_tcl = join(sys.prefix, 'tcl')
    if exists(base_tcl):
        tcl_dir = join(base_tcl, 'tcl8.6') # バージョンは決め打ち気味だが...
        tk_dir = join(base_tcl, 'tk8.6')

# Treeとして追加
if tcl_dir and exists(tcl_dir):
    print(f"Found Tcl dir: {tcl_dir}")
    a.datas += Tree(tcl_dir, prefix='tcl', excludes=['*.lib', '*.sh', '*.txt'])
else:
    print("WARNING: Tcl directory not found!")

if tk_dir and exists(tk_dir):
    print(f"Found Tk dir: {tk_dir}")
    a.datas += Tree(tk_dir, prefix='tk', excludes=['*.lib', '*.sh', '*.txt'])
else:
    print("WARNING: Tk directory not found!")

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MailConsolidator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
