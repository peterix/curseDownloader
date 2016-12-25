#!/usr/bin/python3
# -*- coding: utf-8 -*-
import appdirs
import argparse
import json
import os
import sys
import time
import requests
import shutil
from urllib.parse import urlparse, unquote
from pathlib import Path
from threading import Thread

temp_file_name = "curseDownloader-download.temp"
sess = requests.session()
erred_mod_downloads = []

# else just get the default file
CA_Certificates = requests.certs.where()
os.environ["REQUESTS_CA_BUNDLE"] = CA_Certificates

parser = argparse.ArgumentParser(description="Download Curse modpack mods")
parser.add_argument("--manifest", help="manifest.json file from unzipped pack")
args, unknown = parser.parse_known_args()


# Simplify output text for both console and GUI.
def print_text(message):
    message == str(message)
    print(message)  # For the console output


def get_human_readable(size, precision=2, requestz=-1):
    suffixes = ['B', 'KB', 'MB', 'GB', 'TB']
    suffix_index = 0
    if requestz == -1:
        while size > 1024 and suffix_index < 4:
            suffix_index += 1  # increment the index of the suffix
            size /= 1024.0  # apply the division
    elif (requestz >= 1 or requestz == 4):
        i = 0
        while i < requestz:
            suffix_index += 1  # increment the index of the suffix
            size /= 1024.0  # apply the division
            i += 1

    return "%s%s" % (str("{:.3g}".format(round(size, 2))), suffixes[suffix_index])


class HeadlessUI:
    def set_output(self, message):
        pass


programGui = HeadlessUI()


def do_download(manifest):
    if manifest == '':
        print_text("Select a manifest file first!")
        return 1
    manifest_path = Path(manifest)
    target_dir_path = manifest_path.parent

    manifest_text = manifest_path.open().read()
    manifest_text = manifest_text.replace('\r', '').replace('\n', '')

    manifest_json = json.loads(manifest_text)

    try:
        if not "minecraftModpack" == manifest_json['manifestType']:
            print_text('Manifest Error. manifestType is not "minecraftModpack"')
            return 1
    except KeyError as e:
        print_text('I got a KeyError - reason %s' % str(e))
        print_text("Manifest Error. Make sure you selected a valid pack manifest.json")
        return 1

    try:
        override_path = Path(target_dir_path, manifest_json['overrides'])
        minecraft_path = Path(target_dir_path, "minecraft")
        mods_path = minecraft_path / "mods"
    except KeyError as e:
        print_text('I got a KeyError - reason %s' % str(e))
        print_text("Manifest Error. Make sure you selected a valid pack manifest.json")
        return 1

    if override_path.exists():
        shutil.move(str(override_path), str(minecraft_path))

    downloader_dirs = appdirs.AppDirs(appname="cursePackDownloader", appauthor="portablejim")
    cache_path = Path(downloader_dirs.user_cache_dir, "curseCache")

    if '__file__' in globals():
        cache_path = Path(os.path.dirname(os.path.realpath(__file__)), "curseCache")
    else:
        print_text("Portable data dir not supported for interpreter environment")
        return 1

    if not cache_path.exists():
        cache_path.mkdir(parents=True)

    if not minecraft_path.exists():
        minecraft_path.mkdir()

    if not mods_path.exists():
        mods_path.mkdir()

    i = 1
    try:
        i_len = len(manifest_json['files'])
    except KeyError as e:
        print_text('I got a KeyError - reason %s' % str(e))
        print_text("Manifest Error. Make sure you selected a valid pack manifest.json")
        return 1

    print_text("Cached files are stored here:\n %s\n" % cache_path)
    print_text("%d files to download" % i_len)
    for dependency in manifest_json['files']:
        dep_cache_dir = cache_path / str(dependency['projectID']) / str(dependency['fileID'])
        if dep_cache_dir.is_dir():
            # File is cached
            dep_files = [f for f in dep_cache_dir.iterdir()]
            if len(dep_files) >= 1:
                dep_file = dep_files[0]
                target_file = minecraft_path / "mods" / dep_file.name
                shutil.copyfile(str(dep_file), str(target_file))
                print_text("[%d/%d] %s (cached)" % (i, i_len, target_file.name))

                i += 1

                # Cache access is successful,
                # Don't download the file
                continue

        # File is not cached and needs to be downloaded
        project_response = sess.get("http://minecraft.curseforge.com/projects/%s"
                                    % (dependency['projectID']), stream=True)
        project_response.url = project_response.url.replace('?cookieTest=1', '')
        file_response = sess.get("%s/files/%s/download"
                                 % (project_response.url, dependency['fileID']), stream=True)
        global temp_file_name
        temp_file_name = str(minecraft_path / "curseDownloader-download.temp")

        requested_file_sess = sess.get(file_response.url, stream=True)
        try:
            full_file_size = int(requested_file_sess.headers.get('content-length'))
        except TypeError:
            print_text(str("[%d/%d] " + "MISSING FILE SIZE") % (i, i_len))
            full_file_size = 100

        remote_url = Path(requested_file_sess.url)
        file_name = unquote(remote_url.name).split('?')[0]  # If query data strip it and return just the file name.
        if file_name == "download":
            print_text(str("[%d/%d] " + "ERROR FILE MISSING FROM SOURCE") % (i, i_len))
            print_text(str(project_response.url) + "/files/" + str(dependency['fileID']) + "/download")
            erred_mod_downloads.append(str(project_response.url) + "/files/" + str(dependency['fileID']) + "/download")
            i += 1
            continue

        print_text(str("[%d/%d] " + file_name +
                   " (DL: " + get_human_readable(full_file_size) + ")") % (i, i_len))
        time.sleep(0.1)

        with open(temp_file_name, 'wb') as file_data:
            dl = 0
            # maybe do something
            for chunk in requested_file_sess.iter_content(chunk_size=1024):
                if dl < full_file_size:
                    dl += len(chunk)
                elif dl > full_file_size:
                    dl = full_file_size
                if chunk:  # filter out keep-alive new chunks
                    file_data.write(chunk)
            file_data.close()
        shutil.move(temp_file_name, str(mods_path / file_name))  # Rename from temp to correct file name.

        # Try to add file to cache.
        if not dep_cache_dir.exists():
            dep_cache_dir.mkdir(parents=True)
            shutil.copyfile(str(mods_path / file_name), str(dep_cache_dir / file_name))

        i += 1

    # This is not available in curse-only packs
    if 'directDownload' in manifest_json:
        i = 1
        i_len = len(manifest_json['directDownload'])
        programGui.set_output("%d additional files to download." % i_len)
        for download_entry in manifest_json['directDownload']:
            if "url" not in download_entry or "filename" not in download_entry:
                programGui.set_output("[%d/%d] <Error>" % (i, i_len))
                i += 1
                continue
            source_url = urlparse(download_entry['url'])
            download_cache_children = Path(source_url.path).parent.relative_to('/')
            download_cache_dir = cache_path / "directdownloads" / download_cache_children
            cache_target = Path(download_cache_dir / download_entry['filename'])
            if cache_target.exists():
                # Cached
                target_file = minecraft_path / "mods" / cache_target.name
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
            programGui.set_output("[%d/%d] %s" % (i, i_len, download_entry['filename']))
            with open(str(minecraft_path / "mods" / download_entry['filename']), "wb") as mod:
                mod.write(file_response.content)
            i += 1

    if len(erred_mod_downloads) is not 0:
        print_text("\n!! WARNING !!\nThe following mod downloads failed.")
        for index in erred_mod_downloads:
            print_text("- " + index)
        # Create log of failed download links to pack manifest directory for user to inspect manually.
        log_file = open(str(target_dir_path / "cursePackDownloaderModErrors.log"), 'w')
        log_file.write("\n".join(str(elem) for elem in erred_mod_downloads))
        log_file.close()
        print_text("See log in manifest directory for list.\n!! WARNING !!\n")
        erred_mod_downloads.clear()
        return 1

    print_text("Unpacking Complete")
    return 0


if args.manifest is not None:
    sys.exit(do_download(args.manifest))
else:
    print( __file__ + ' --manifest "/path/to/manifest.json"')
    sys.exit(1)
