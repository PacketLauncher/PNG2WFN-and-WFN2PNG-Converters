@echo off

py -m PyInstaller --onefile --console --clean --icon="WFN2PNG.ico" --name WFN2PNG WFN2PNG.py

if exist WFN2PNG.exe del WFN2PNG.exe

move dist\WFN2PNG.exe