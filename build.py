import PyInstaller.__main__
import os
from PyInstaller.utils.hooks import collect_all


datas, binaries, hiddenimports = collect_all('taichi')

args = [
    'run.py',                       
    '--name=DroneSim',       
    '--onefile',
    '--noconsole',
    '--clean',
]

# Add collected taichi resources
for h in hiddenimports:
    args.append(f'--hidden-import={h}')
    
sep = ';' if os.name == 'nt' else ':'

datas.append(('modules', 'modules'))

for d in datas:
    source, dest = d
    args.append(f'--add-data={source}{sep}{dest}')

for b in binaries:
    source, dest = b
    args.append(f'--add-binary={source}{sep}{dest}')

PyInstaller.__main__.run(args)

print("Build complete. Executable is in the 'dist' folder.")
