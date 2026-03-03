import argparse
from pathlib import Path

import yaml


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="ml/configs/body_parts.yaml")
    args = parser.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text())
    print("train config:", cfg["name"])
    print("dataset:", cfg["dataset"])
    print("model:", cfg["model"])
    print("epochs:", cfg["epochs"])
    print("run command:")
    print(
        "yolo segment train "
        f"model={cfg['model']} data={cfg['dataset']} "
        f"epochs={cfg['epochs']} imgsz={cfg['imgsz']} batch={cfg['batch']}"
    )


if __name__ == "__main__":
    main()
