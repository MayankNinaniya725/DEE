import json
import os

def load_vendor_config(vendor_id):
    config_path = os.path.join("vendor_configs", f"{vendor_id}.json")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config for vendor '{vendor_id}' not found.")
    with open(config_path, 'r') as file:
        return json.load(file)
