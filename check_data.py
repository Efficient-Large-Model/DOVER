import os
import json
import argparse
from tqdm import tqdm

parser = argparse.ArgumentParser()
parser.add_argument("-d","--data_path", type=str, required=True)
args = parser.parse_args()

data_path = args.data_path
zip_fns = sorted([f for f in os.listdir(data_path) if f.endswith(".zip")])
for zip_fn in tqdm(zip_fns):
    fn = zip_fn.split(".")[0]
    vmaf = os.path.join(data_path, f"{fn}_vmafmotion.json")
    unimatch = os.path.join(data_path, f"{fn}_unimatch.json")
    dover = os.path.join(data_path, f"{fn}_dover.json")
    # check if all exist, and if not, print the missing one
    missing = []
    if not os.path.exists(vmaf):
        missing.append(vmaf)
    if not os.path.exists(unimatch):
        missing.append(unimatch)
    if not os.path.exists(dover):
        missing.append(dover)
    if len(missing) > 0:
        print(f"missing files: {missing}")
        continue
    
    # check if the length of the three files are the same
    with open(vmaf, "r") as f:
        vmaf_data = json.load(f)
    with open(unimatch, "r") as f:
        unimatch_data = json.load(f)
    with open(dover, "r") as f:
        dover_data = json.load(f)
    if len(vmaf_data) != len(unimatch_data) or len(vmaf_data) != len(dover_data):
        print(f"lengths are not the same {fn}: vmaf {len(vmaf_data)}, unimatch {len(unimatch_data)}, dover {len(dover_data)}")
        continue
    # check if the length is too short
    if len(vmaf_data) < 9900:
        print(f"Data length is less than 9900: {fn}, length: {len(vmaf_data)}")
        continue
