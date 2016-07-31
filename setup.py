#!python3
#http://cx-freeze.readthedocs.io/en/latest/distutils.html#build-exe
#http://cx-freeze.readthedocs.io/en/latest/faq.html#using-data-files
from cx_Freeze import setup, Executable
import requests
import sys


# Includes cpcert.pem with package so it can verify with file server.
#http://stackoverflow.com/questions/15157502/requests-library-missing-file-after-cx-freeze
#http://stackoverflow.com/questions/23354628/python-requests-and-cx-freeze
build_exe_options = {"include_files":[(requests.certs.where(),'cacert.pem')]}

base = None
targetName = "cursePackDownloader"
if sys.platform == "win32":
    base = "Win32GUI"
    targetName = "cursePackDownloader.exe"

setup(
    name = "cursePackDownloader",
    version = "0.3",
    description = "Download extra mods from Curse-hosted Minecraft modpacks",
    options = {"build_exe": build_exe_options},
    executables = [Executable("downloader.py", targetName=targetName)])