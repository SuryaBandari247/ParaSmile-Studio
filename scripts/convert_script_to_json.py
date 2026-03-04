#!/usr/bin/env python3
"""Convert raw .txt script files in scripts/input/ to JSON in output/.

Watches for .txt files, converts each via ScriptConverter, writes
the JSON output, and moves the original to scripts/input/done/.
"""

import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env so OPENAI_API_KEY is available
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))


def main():
    input_dir = os.path.join("scripts", "input")
    done_dir = os.path.join(input_dir, "done")
    output_dir = "output"

    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(done_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    txt_files = glob.glob(os.path.join(input_dir, "*.txt"))
    if not txt_files:
        print("No .txt files found in scripts/input/")
        return

    from script_generator.converter import ScriptConverter
    from script_generator.serializer import ScriptSerializer

    converter = ScriptConverter()
    serializer = ScriptSerializer()

    for txt_path in txt_files:
        basename = os.path.splitext(os.path.basename(txt_path))[0]
        json_path = os.path.join(output_dir, f"{basename}_video_script.json")

        print(f"Converting: {txt_path} → {json_path}")
        try:
            with open(txt_path, "r") as f:
                raw_script = f.read()

            if not raw_script.strip():
                print(f"  Skipping empty file: {txt_path}")
                continue

            video_script = converter.convert(raw_script)
            json_str = serializer.serialize(video_script)

            with open(json_path, "w") as f:
                f.write(json_str)

            # Move processed file to done/
            done_path = os.path.join(done_dir, os.path.basename(txt_path))
            os.rename(txt_path, done_path)
            print(f"  Done. Output: {json_path}")

        except Exception as e:
            print(f"  FAILED: {e}")


if __name__ == "__main__":
    main()
