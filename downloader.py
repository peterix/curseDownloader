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


def do_download(manifest):
    if manifest == '':
        print("Select a manifest file first!")
        return 1
    manifest_path = Path(manifest)
    target_dir_path = manifest_path.parent
    minecraft_path = Path(target_dir_path, "minecraft")
    mods_path = minecraft_path / "mods"

    manifest_text = manifest_path.open().read()
    manifest_text = manifest_text.replace('\r', '').replace('\n', '')

    manifest_json = json.loads(manifest_text)

    try:
        if not "minecraftModpack" == manifest_json['manifestType']:
            print('Manifest Error. manifestType is not "minecraftModpack"')
            return 1
    except KeyError as e:
        print('I got a KeyError - reason %s' % str(e))
        print("Manifest Error. Make sure you selected a valid pack manifest.json")
        return 1

    if "overrides" in manifest_json:
        override_path = Path(target_dir_path, manifest_json['overrides'])
        if override_path.exists():
            shutil.move(str(override_path), str(minecraft_path))

    if '__file__' in globals():
        cache_path = Path(os.path.dirname(os.path.realpath(__file__)), "curseCache")
    else:
        print("Portable data dir not supported for interpreter environment")
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
        print('I got a KeyError - reason %s' % str(e))
        print("Manifest Error. Make sure you selected a valid pack manifest.json")
        return 1

    print("Cached files are stored here:\n %s\n" % cache_path)
    print("%d files to download" % i_len)
    for dependency in manifest_json['files']:
        dep_cache_dir = cache_path / str(dependency['projectID']) / str(dependency['fileID'])
        if dep_cache_dir.is_dir():
            # File is cached
            dep_files = [f for f in dep_cache_dir.iterdir()]
            if len(dep_files) >= 1:
                dep_file = dep_files[0]
                target_file = mods_path / dep_file.name
                shutil.copyfile(str(dep_file), str(target_file))
                print("[%d/%d] %s (cached)" % (i, i_len, target_file.name))

                i += 1

                # Cache access is successful,
                # Don't download the file
                continue


        # File is not cached and needs to be downloaded

        global temp_file_name
        temp_file_name = str(minecraft_path / "curseDownloader-download.temp")

        # FIXME: add a config thing for this.
        if False:
            # resolve the project name from the ID using curse's website
            # example: https://minecraft.curseforge.com/projects/220308
            project_response = sess.get("https://minecraft.curseforge.com/projects/%s" % (dependency['projectID']), stream=True)
            project_response.url = project_response.url.replace('?cookieTest=1', '')

            # request the file by ID, now that we have the name-based URL, this is a redirect
            # example: https://minecraft.curseforge.com/projects/thaumic-infusion/files/2237176/download
            file_response = sess.get("%s/files/%s/download" % (project_response.url, dependency['fileID']), stream=True)

            # Get the redirected file
            # example: http://addons.cursecdn.com/files/2237/176/ThaumicInfusion-4.jar
            requested_file_sess = sess.get(file_response.url, stream=True)
            try:
                full_file_size = int(requested_file_sess.headers.get('content-length'))
            except TypeError:
                print(str("[%d/%d] " + "MISSING FILE SIZE") % (i, i_len))
                full_file_size = 100

            remote_url = Path(requested_file_sess.url)
            file_name = unquote(remote_url.name).split('?')[0]  # If query data strip it and return just the file name.
            if file_name == "download":
                print(str("[%d/%d] " + "ERROR FILE MISSING FROM SOURCE") % (i, i_len))
                print(str(project_response.url) + "/files/" + str(dependency['fileID']) + "/download")
                erred_mod_downloads.append(str(project_response.url) + "/files/" + str(dependency['fileID']) + "/download")
                i += 1
                continue
        else:
            # get the json from Dries:
            metabase = "https://cursemeta.dries007.net"
            metaurl = "%s/%s/%s.json" % (metabase, dependency['projectID'], dependency['fileID'])
            r = sess.get(metaurl)
            r.raise_for_status()
            main_json = r.json()
            if "code" in main_json:
                print(str("[%d/%d] " + "ERROR FILE") % (i, i_len))
                erred_mod_downloads.append(metaurl.url)
                i += 1
                continue
            fileurl = main_json["DownloadURL"]
            file_name = main_json["FileNameOnDisk"]
            requested_file_sess = sess.get(fileurl, stream=True)
            try:
                full_file_size = int(requested_file_sess.headers.get('content-length'))
            except TypeError:
                print(str("[%d/%d] " + "MISSING FILE SIZE") % (i, i_len))
                full_file_size = 100

        print(str("[%d/%d] " + file_name + " (DL: %d)") % (i, i_len, full_file_size))

        with open(temp_file_name, 'wb') as file_data:
            # maybe do something
            for chunk in requested_file_sess.iter_content(chunk_size=1024):
                if chunk:  # filter out keep-alive new chunks
                    file_data.write(chunk)
            file_data.close()
        shutil.move(temp_file_name, str(mods_path / file_name))  # Rename from temp to correct file name.

        # Try to add file to cache.
        if not dep_cache_dir.exists():
            dep_cache_dir.mkdir(parents=True)
            shutil.copyfile(str(mods_path / file_name), str(dep_cache_dir / file_name))

        i += 1

    if len(erred_mod_downloads) is not 0:
        print("\n!! WARNING !!\nThe following mod downloads failed.")
        for index in erred_mod_downloads:
            print("- " + index)
        # Create log of failed download links to pack manifest directory for user to inspect manually.
        log_file = open(str(target_dir_path / "cursePackDownloaderModErrors.log"), 'w')
        log_file.write("\n".join(str(elem) for elem in erred_mod_downloads))
        log_file.close()
        print("See log in manifest directory for list.\n!! WARNING !!\n")
        erred_mod_downloads.clear()
        return 1

    print("Unpacking Complete")
    return 0


if args.manifest is not None:
    sys.exit(do_download(args.manifest))
else:
    print( __file__ + ' --manifest "/path/to/manifest.json"')
    sys.exit(1)
