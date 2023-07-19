import sys
import os
import json

db = json.load(sys.stdin)

def write_db(db, path):
    os.makedirs(path, exist_ok=True)
    for key, value in db.items():
        key = key.replace(" ", "-")
        if isinstance(value, dict):
            write_db(value, f"{path}/{key}")
        else:
            with open(f"{path}/{key}", "w") as fd:
                fd.write(value + "\n")

write_db(db=db, path="/home/pi/src/hq/etc/kopi")
