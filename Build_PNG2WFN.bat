@echo off

py -m PyInstaller --onefile --console --clean --icon="PNG2WFN.ico" --name PNG2WFN PNG2WFN.py

if exist PNG2WFN.exe del PNG2WFN.exe

move dist\PNG2WFN.exe