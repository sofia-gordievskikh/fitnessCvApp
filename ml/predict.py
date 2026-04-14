import argparse
import json
from pathlib import Path

from .inference import BodyAnalyzer


def main() -> None:
    parser = argparse.ArgumentParser(description="анализ одного кадра")
    parser.add_argument("--image", default="samples/squat.jpg")
    parser.add_argument("--weights", default="ml/weights/body_parts_yolo.pt")
    parser.add_argument("--exercise", default=None, help="squat | lunge | push_up")
    args = parser.parse_args()

    analyzer = BodyAnalyzer(weights_path=args.weights)
    content = Path(args.image).read_bytes()
    result = analyzer.analyze_bytes(content, filename=Path(args.image).name, exercise=args.exercise)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
