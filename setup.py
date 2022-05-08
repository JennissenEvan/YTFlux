from PyInstaller.__main__ import run
import shutil


run([
    "main.py",
    "--onefile",
    "--name", "YTFlux",
    "--distpath", "dist/raw"
])

shutil.make_archive("dist/YTFlux", "zip", "dist/raw")
