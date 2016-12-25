# Curseforge Minecraft Modpack Downloader

A **simple** script to download mods from a CurseForge Minecraft modpack.

## Requirements

- Python 3.4+

## Usage

Example:
```
$ ./downloader.py --manifest ~/curseisevil/FTBPresentsDirewolf20110-1.1.4-1.10.2/manifest.json
Cached files are stored here:
 /home/peterix/minecraft/curseDownloader/curseCache

71 files to download
[1/71] appliedenergistics2-rv4-alpha-8.jar (DL: 3.19MB)

.
.
.

[71/71] Draconic-Evolution-1.10.2-2.0.3.137-universal.jar (DL: 6.43MB)
Unpacking Complete
[peterix ~/minecraft/curseDownloader]$ echo $?
0

```

It returns `0` on success and `1` on failure. It should be suitable for automation.

Getting the zip file and extracting it is out of scope of this tool.