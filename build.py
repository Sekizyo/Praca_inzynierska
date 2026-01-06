import PyInstaller.__main__
import os
import shutil
from PyInstaller.utils.hooks import collect_all

if os.path.exists('build'):
    shutil.rmtree('build')
if os.path.exists('dist'):
    shutil.rmtree('dist')

datas, binaries, hiddenimports = collect_all('taichi')

args = [
    'run.py',                        # Your entry point script
    '--name=DroneVoronoiSim',        # Name of the executable
    '--onedir',                      # Create a directory (faster startup than --onefile)
    '--noconsole',                   # Hide the console window
    '--clean',                       # Clean PyInstaller cache
    '--exclude-module=modules',      # Exclude modules from PYZ to force loading from source
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
