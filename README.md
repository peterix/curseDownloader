# Curseforge Minecraft Modpack Downloader


A simple script to download mods from a CurseForge Minecraft modpack.

## Source Script Requirements

- Python 3.4+
- appdirs 
- python-tk

## Setup For Source Script

### Linux
- Debian based  
`sudo apt-get install python3 python3-tk python3-pip`  
`pip3 install appdirs`

#### How to use

  1. Find the modpack you want from the [CurseForge modpack list](http://www.curse.com/modpacks/minecraft)
  2. Unzip the download. There should be a manifest.json file.
  3. Run! `python3.4 /path/to/downloader.py /path/to/manifest.json`

    <python> /path/to/downloader.py --manifest <manifest.json file>

### Windows
 - #### Compiled exe
   #### Accepted Arguments

 	- `CMD> C:\someFolder\cursePackDownloader.exe --portable --nogui --manifest ["/path/to/manifest.json"]`

 	- portable - makes the downloader cache downloads in a sub folder of current directory it is inside.
 	 	ex: `CMD> C:\someFolder\cursePackDownloader.exe --portable`
 	 	ex folder: C:\someFolder\curseCache

 	- manifest - provides commandline option to select manifest.json file.
 	 	ex: `CMD> C:\someFolder\cursePackDownloader.exe --manifest [/path/to/manifest.json]`

 	- nogui - runs prgram in commandline only, and must include the manifest argument as well.
 	 	ex: `CMD> C:\someFolder\cursePackDownloader.exe --nogui --manifest [/path/to/manifest.json]`

  #### Python Script
  #### Accepted Arguments

   - CMD> `"path/to/python" "/path/to/downloader.py" --portable --nogui --manifest ["/path/to/manifest.json"]`

   - portable - makes the downloader cache downloads in a sub folder of current directory it is inside.
       ex: `CMD> C:\Python34\python.exe ["/path/to/downloader.py"] --portable`
       ex folder: C:\someFolder\curseCache

   - manifest - provides commandline option to select manifest.json file.
       ex:`CMD> /path/to/<python> ["/path/to/downloader.py"] --manifest ["/path/to/manifest.json"]`

   - nogui - runs program in commandline only, and manifest argument must be provided as well.
       ex: `CMD> /path/to/<python> ["/path/to/downloader.py"] --nogui --manifest ["/path/to/manifest.json"]`

