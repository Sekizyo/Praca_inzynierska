import PyInstaller.__main__
import os
import shutil
from PyInstaller.utils.hooks import collect_all

# Clean up previous build/dist folders
if os.path.exists('build'):
    shutil.rmtree('build')
if os.path.exists('dist'):
    shutil.rmtree('dist')

# Collect all data and binaries for taichi to ensure GPU backends work
datas, binaries, hiddenimports = collect_all('taichi')

# Define PyInstaller arguments
args = [
    'run.py',                        # Your entry point script
    '--name=DroneVoronoiSim',        # Name of the executable
    '--onefile',                     # Create a single executable file
    '--noconsole',                   # Hide the console window
    '--clean',                       # Clean PyInstaller cache
    '--exclude-module=modules',      # Exclude modules from PYZ to force loading from source
]

# Add collected taichi resources
for h in hiddenimports:
    args.append(f'--hidden-import={h}')
    
# PyInstaller expects add-data in "source;dest" format (Windows) or "source:dest" (Unix)
# Since we are on Windows (separater is ;), we format accordingly.
sep = ';' if os.name == 'nt' else ':'

# Add our source modules as data
datas.append(('modules', 'modules'))

for d in datas:
    source, dest = d
    args.append(f'--add-data={source}{sep}{dest}')

for b in binaries:
    source, dest = b
    args.append(f'--add-binary={source}{sep}{dest}')

# Run PyInstaller
PyInstaller.__main__.run(args)

print("Build complete. Executable is in the 'dist' folder.")
