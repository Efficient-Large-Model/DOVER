import os
import json
import argparse
from tqdm import tqdm

parser = argparse.ArgumentParser()
parser.add_argument("-d","--data_path", type=str, required=True)
args = parser.parse_args()

data_path = args.data_path
zip_fns = sorted([f for f in os.listdir(data_path) if f.endswith(".zip")])
if not len(zip_fns):
    zip_fns = sorted([f for f in os.listdir(data_path) if f.endswith("_dover.json")])

num_files = 0
for zip_fn in tqdm(zip_fns):
    fn = zip_fn.split(".")[0]
    if fn.endswith("_dover"):
        fn = fn[:-6]
    vmaf = os.path.join(data_path, f"{fn}_vmafmotion.json")
    unimatch = os.path.join(data_path, f"{fn}_unimatch.json")
    dover = os.path.join(data_path, f"{fn}_dover.json")
    # check if all exist, and if not, print the missing one
    existing = {}
    missing = []
    if os.path.exists(vmaf):
        existing["vmaf"] = json.load(open(vmaf, "r"))
    if os.path.exists(unimatch):
        existing["unimatch"] = json.load(open(unimatch, "r"))
    if os.path.exists(dover):
        existing["dover"] = json.load(open(dover, "r"))
    if len(existing) != 3:
        missing = set(['vmaf', 'unimatch', 'dover']) - set(existing.keys())
        if 'dover' in missing:
            break
        print(f"missing files: {fn}, {missing}")
        
        for k in missing:
            existing[k] = {}

    print(f"{fn}, {len(existing['vmaf'])}, {len(existing['unimatch'])}, {len(existing['dover'])}")
    
    # check if the length is too short
    if len(existing['dover']) < 9900:
        print(f"Data length is less than 9900: {fn}, length: {len(existing['dover'])}")
        # continue
    num_files += len(existing['dover'])

print(f"num_files: {num_files}")
