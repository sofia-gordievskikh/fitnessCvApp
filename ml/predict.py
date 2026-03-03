import argparse
import json
from pathlib import Path

from .inference import BodyAnalyzer


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--weights", default="ml/weights/body_parts_yolo.pt")
    args = parser.parse_args()

    analyzer = BodyAnalyzer(weights_path=args.weights)
    content = Path(args.image).read_bytes()
    result = analyzer.analyze_bytes(content, filename=Path(args.image).name)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
