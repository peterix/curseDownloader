#!python3
from urllib.parse import urlparse, unquote

import appdirs
import argparse
import json
from pathlib import Path
import os
import requests
import shutil
from threading import Thread
from tkinter import *
from tkinter import ttk, filedialog

compiledExecutable = False

# If in frozen state(aka executable) then use this path, else use original path.
if getattr(sys, 'frozen', False):
    # if frozen, get embeded file
    cacert = os.path.join(os.path.dirname(sys.executable), 'cacert.pem')
    compiledExecutable = True
else:
    # else just get the default file
    cacert = requests.certs.where()
#https://stackoverflow.com/questions/15157502/requests-library-missing-file-after-cx-freeze
os.environ["REQUESTS_CA_BUNDLE"] = cacert

parser = argparse.ArgumentParser(description="Download Curse modpack mods")
parser.add_argument("--manifest", help="manifest.json file from unzipped pack")
parser.add_argument("--nogui", dest="gui", action="store_false", help="Do not use gui to to select manifest")
parser.add_argument("--portable", dest="portable", action="store_true", help="Use portable cache")
args, unknown = parser.parse_known_args()

class downloadUI(ttk.Frame):
    def __init__(self):
        self.root = Tk()
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.parent = ttk.Frame(self.root)
        self.parent.grid(column=0, row=0, sticky=(N, S, E, W))
        self.parent.columnconfigure(0, weight=1)
        self.parent.rowconfigure(0, weight=1)
        ttk.Frame.__init__(self, self.parent, padding=(6,6,14,14))
        self.grid(column=0, row=0, sticky=(N, S, E, W))
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        self.root.title("Curse Pack Downloader")

        self.manifestPath = StringVar()

        chooserContainer = ttk.Frame(self)
        self.chooserText = ttk.Label(chooserContainer, text="Locate 'manifest.json': ")
        chooserEntry = ttk.Entry(chooserContainer, textvariable=self.manifestPath)
        self.chooserButton = ttk.Button(chooserContainer, text="Browse", command=self.chooseFile)
        self.chooserText.grid(column=0, row=0, sticky=W)
        chooserEntry.grid(column=1, row=0, sticky=(E,W), padx=5)
        self.chooserButton.grid(column=2, row=0, sticky=E)
        chooserContainer.grid(column=0, row=0, sticky=(E,W))
        chooserContainer.columnconfigure(1, weight=1)
        self.downloadButton = ttk.Button(self, text="Download mods", command=self.goDownload)
        self.downloadButton.grid(column=0, row=1, sticky=(E,W))

        self.logText = Text(self, state="disabled", wrap="none")
        self.logText.grid(column=0, row=2, sticky=(N,E,S,W))

        self.logScroll = Scrollbar(self, command=self.logText.yview)
        self.logScroll.grid(column=1, row=2, sticky=(N,E,S,W))
        self.logText['yscrollcommand'] = self.logScroll.set

    def chooseFile(self):
        filePath = filedialog.askopenfilename(
                filetypes=(("Json files", "*.json"),),
                initialdir=os.path.expanduser("~"),
                parent=self)
        self.manifestPath.set(filePath)

    def goDownload(self):
        t = Thread(target=self.goDownloadBackground)
        t.start()

    def goDownloadBackground(self):
        self.downloadButton.configure(state="disabled")
        self.chooserButton.configure(state="disabled")
        doDownload(self.manifestPath.get())
        self.downloadButton.configure(state="enabled")
        self.chooserButton.configure(state="enabled")

    def setOutput(self, message):
        self.logText["state"] = "normal"
        self.logText.insert("end", message + "\n")
        self.logText.see(END)
        self.logText["state"] = "disabled"

    def setManifest(self, fileName):
        self.manifestPath.set(fileName)

class headlessUI():
    def setOutput(self, message):
        pass

programGui = None

def doDownload(manifest):
    if manifest == '':
        print("Select a manifest file first!")
        programGui.setOutput("Select a manifest file first!")
        return None
    manifestPath = Path(manifest)
    targetDirPath = manifestPath.parent

    manifestText = manifestPath.open().read()
    manifestText = manifestText.replace('\r', '').replace('\n', '')

    manifestJson = json.loads(manifestText)

    try:
        overridePath = Path(targetDirPath, manifestJson['overrides'])
        minecraftPath = Path(targetDirPath, "minecraft")
        modsPath = minecraftPath / "mods"
    except KeyError as e:
        print('I got a KeyError - reason %s' % str(e))
        print("Manifest Error. Make sure you selected a valid pack manifest.json")
        programGui.setOutput('I got a KeyError - reason %s' % str(e))
        programGui.setOutput("Manifest Error. Make sure you selected a valid pack manifest.json")
        return None

    if overridePath.exists():
        shutil.move(str(overridePath), str(minecraftPath))

    downloaderDirs = appdirs.AppDirs(appname="cursePackDownloader", appauthor="portablejim")
    cache_path = Path(downloaderDirs.user_cache_dir, "curseCache")

    # Attempt to set proper portable data directory if asked for
    if args.portable:
        if getattr(sys, 'frozen', False):
            # if frozen, get embeded file
            cache_path = Path(os.path.join(os.path.dirname(sys.executable), 'curseCache'))
        else:
            if '__file__' in globals():
                cache_path = Path(os.path.dirname(os.path.realpath(__file__)), "curseCache")
            else:
                print("Portable data dir not supported for interpreter environment")
                sys.exit(2)

    if not cache_path.exists():
        cache_path.mkdir(parents=True)

    if not minecraftPath.exists():
        minecraftPath.mkdir()
        
    if not modsPath.exists():
        modsPath.mkdir()

    sess = requests.session()

    i = 1
    try:
        iLen = len(manifestJson['files'])
    except KeyError as e:
        print('I got a KeyError - reason %s' % str(e))
        print("Manifest Error. Make sure you selected a valid pack manifest.json")
        programGui.setOutput('I got a KeyError - reason %s' % str(e))
        programGui.setOutput("Manifest Error. Make sure you selected a valid pack manifest.json")
        return None

    print("Cached files are stored here:\n %s\n" % (cache_path))
    programGui.setOutput("Cached files are stored here:\n %s\n" % (cache_path))
    print("%d files to download" % (iLen))
    programGui.setOutput("%d files to fetch" % (iLen))

    for dependency in manifestJson['files']:
        depCacheDir = cache_path / str(dependency['projectID']) / str(dependency['fileID'])
        if depCacheDir.is_dir():
            # File is cached
            depFiles = [f for f in depCacheDir.iterdir()]
            if len(depFiles) >= 1:
                depFile = depFiles[0]
                targetFile = minecraftPath / "mods" / depFile.name
                shutil.copyfile(str(depFile), str(targetFile))
                programGui.setOutput("[%d/%d] %s (cached)" % (i, iLen, targetFile.name))
                print("[%d/%d] %s (cached)" % (i, iLen, targetFile.name))

                i += 1

                # Cache access is successful,
                # Don't download the file
                continue

        # File is not cached and needs to be downloaded
        projectResponse = sess.get("http://minecraft.curseforge.com/mc-mods/%s" % (dependency['projectID']), stream=True)
        projectResponse.url = projectResponse.url.replace('?cookieTest=1', '')
        fileResponse = sess.get("%s/files/%s/download" % (projectResponse.url, dependency['fileID']), stream=True)
        while fileResponse.is_redirect:
            source = fileResponse
            fileResponse = sess.get(source, stream=True)
        filePath = Path(fileResponse.url)
        fileName = unquote(filePath.name)
        print("[%d/%d] %s" % (i, iLen, fileName))
        programGui.setOutput("[%d/%d] %s" % (i, iLen, fileName))
        with open(str(minecraftPath / "mods" / fileName), "wb") as mod:
            mod.write(fileResponse.content)

        # Try to add file to cache.
        if not depCacheDir.exists():
            depCacheDir.mkdir(parents=True)
        with open(str(depCacheDir / fileName), "wb") as mod:
            mod.write(fileResponse.content)

        i += 1

    # This is not available in curse-only packs
    if 'directDownload' in manifestJson:
        i = 1
        i_len = len(manifestJson['directDownload'])
        programGui.setOutput("%d additional files to download." % i_len)
        for download_entry in manifestJson['directDownload']:
            if "url" not in download_entry or "filename" not in download_entry:
                programGui.setOutput("[%d/%d] <Error>" % (i, i_len))
                i += 1
                continue
            source_url = urlparse(download_entry['url'])
            download_cache_children = Path(source_url.path).parent.relative_to('/')
            download_cache_dir = cache_path / "directdownloads" / download_cache_children
            cache_target = Path(download_cache_dir / download_entry['filename'])
            if cache_target.exists():
                # Cached
                target_file = minecraftPath / "mods" / cache_target.name
                shutil.copyfile(str(cache_target), str(target_file))

                i += 1

                # Cache access is successful,
                # Don't download the file
                continue
            # File is not cached and needs to be downloaded
            file_response = sess.get(source_url, stream=True)
            while file_response.is_redirect:
                source = file_response
                file_response = sess.get(source, stream=True)
            programGui.setOutput("[%d/%d] %s" % (i, i_len, download_entry['filename']))
            with open(str(minecraftPath / "mods" / download_entry['filename']), "wb") as mod:
                mod.write(file_response.content)

            i += 1

    programGui.setOutput("Unpacking Complete")
    print("Unpacking Complete")

if args.gui:
    programGui = downloadUI()
    if args.manifest is not None:
        programGui.setManifest(args.manifest)
    programGui.root.mainloop()
else:
    programGui = headlessUI()
    if not args.manifest == None:
        doDownload(args.manifest)
    else:
        if compiledExecutable:
            print('C:\someFolder\cursePackDownloader.exe --portable --nogui --manefest ["/path/to/manifest.json"]')
        else:
            print('CMD>"path/to/python" "/path/to/downloader.py" --portable --nogui --manefest ["/path/to/manifest.json"]')
            sys.exit()