#!/usr/bin/env python3

import requests
import time
import json
import sys
import os
import re
import logging

__forked_by__       = "Zilexa"
__original_author__ = "Jan-Piet Mens"
__copyright__       = "Copyright 2019"
__license__         = "GNU General Public License"

last_id = 0
folders = {}

# Get folder label (used later to check against pattern) and folder path (used later to create a full filepath):
def getfolders(data):

    global folders

    for f in data['folders']:
        folders[f["id"]] = {
            "label" : f["label"],
            "path"  : f["path"],
        }
# Probably required to check the attribute used at script execution (for example 'Photos') against folder label.
def process(array, pat=None):
    """ process if pattern `pat' (regular expression) can be found in
        folder label or item """

    global last_id

    # For each event, select ItemFinished event and read its parameters
    for event in array:
        if "type" in event and event["type"] == "ItemFinished":
            last_id = event["id"]
            
            folder_id = event["data"]["folder"]
            folder_label = folders[folder_id]["label"]
            folder_path = folders[folder_id]["path"]
            
            # Create a variable with path+filename
            file_path = os.path.join(folder_path, event["data"]["item"])

            e = {
                "time"          : event["time"],
                "type"          : event["type"],
                "action"        : event["data"]["action"],
                "error"         : event["data"]["error"],
                "item"          : event["data"]["item"],
                "folder_label"  : folder_label,
                "folder_path"   : folder_path,
                "file_path"     : file_path,
            }
            
            # Probably required to check the attribute used at script execution (for example 'Photos') against folder label.
            if pat:
                s = "{folder_label}".format(**e)
                if not re.search(pat, s):
                    continue
                    
            # Continue if it this event is a successful file update operation.
            if event["data"]["action"] == "update" and event["data"]["error"]==None:
              
              # NOT WORKING: (Backup file if source file is newer or does not exist at destination).
              cp -u --preserve=timestamps "file_path" /mnt/pool/Collections/Pictures/Test/
              # NOT WORKING Move file to source/archive. 
              mv "file_path" "folder_path"/archive
              # WORKS Logging.
              logging.basicConfig(level=logging.DEBUG, filename="syncthing-backup.log", filemode="a+",
                          format="%(asctime)-15s %(levelname)-8s %(message)s")
              logging.info("{time:>20} {type:>10} {action:>10} {folder_label:>15} {folder_path:>50} {file_path:>50}".format(**e))


def main(url, apikey, pat):
    headers = { "X-API-Key" : apikey }

    r = requests.get("{0}/rest/system/config".format(url), headers=headers)
    getfolders(json.loads(r.text))

    while True:

        params = {
            "since" : last_id,
            "limit" : 1,
            "events" : "ItemFinished",
        }

        r = requests.get("{0}/rest/events".format(url), headers=headers, params=params)
        if r.status_code == 200:
            process(json.loads(r.text), pat)
        elif r.status_code != 304:
            time.sleep(60)
            continue
        time.sleep(10.0)

if __name__ == "__main__":

    url = os.getenv("SYNCTHING_URL", "http://localhost:8384")
    apikey = os.getenv("SYNCTHING_APIKEY")
    if apikey is None:
        print("Missing SYNCTHING_APIKEY in environment", file=sys.stderr)
        exit(2)

    pattern = None
    if len(sys.argv) > 1:
        pattern = sys.argv[1]
    try:
        main(url, apikey, pattern)
    except KeyboardInterrupt:
        exit(1)
    except:
        raise
