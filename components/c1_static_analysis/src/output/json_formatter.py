import json
import os


def format_as_json(data):
    return json.dumps(data, indent=4)


def save_json_to_file(data, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)