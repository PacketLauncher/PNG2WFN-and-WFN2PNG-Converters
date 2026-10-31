PNGtoWFN and WFNtoPNG converters, by Gal Shemesh (PacketLauncher)

These Python script can convert a PNG file into an Adventure Game Studio (AGS) engine WFN font format and vice versa.

Refer to the README.txt to learn more.


Changelog
=========
Version 1.0.1.0
Released: 29 October, 2026
- Added a base-shade support for PNG2WFN (default to shade index 8 / dynamic in CLI)


Version 1.0.0
Released: 24 October, 2026
- Initial release.


Making an EXE from the source Python scripts:
---------------------------------------------
* This is for developers who wish to make adjustments to the source scripts for generating an EXE out of them.

1. Install Python.

2. Open CMD and install both pyinstaller and pillow library:
	py -m pip install pillow
	py -m pip install pyinstaller
	
3. Run either 'Build_WFN2PNG.bat', Build_PNG2WFN.bat or the following commands to build an EXE:
	py -m PyInstaller --onefile --console --clean --icon="PNG2WFN.ico" --name PNG2WFN PNG2WFN.py
	py -m PyInstaller --onefile --console --clean --icon="WFN2PNG.ico" --name WFN2PNG WFN2PNG.py
	
4. Run 'Build_Leftovers_CleanUp.bat' to clean up the directory to remove any leftovers.