import argparse
from pathlib import Path

import cv2
from ultralytics import YOLO


def main() -> None:
    parser = argparse.ArgumentParser(description="Run fire detection on an image/video.")
    parser.add_argument(
        "--weights",
        type=Path,
        default=Path("ML model") / "artifacts" / "fire_detector" / "weights" / "best.pt",
        help="Path to trained YOLO weights",
    )
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="Path to input image or video",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.25,
        help="Confidence threshold",
    )
    parser.add_argument(
        "--save-path",
        type=Path,
        default=Path("ML model") / "predictions" / "prediction.jpg",
        help="Where to save visualization output",
    )

    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    weights = args.weights if args.weights.is_absolute() else repo_root / args.weights
    source = args.source if args.source.is_absolute() else repo_root / args.source
    save_path = args.save_path if args.save_path.is_absolute() else repo_root / args.save_path

    if not weights.exists():
        raise FileNotFoundError(f"Model weights not found: {weights}")
    if not source.exists():
        raise FileNotFoundError(f"Input source not found: {source}")

    model = YOLO(str(weights))
    results = model.predict(source=str(source), conf=args.conf, verbose=False)

    if not results:
        print("No prediction results were returned.")
        return

    plotted = results[0].plot()
    save_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(save_path), plotted)

    boxes = results[0].boxes
    count = 0 if boxes is None else len(boxes)

    print(f"Detections: {count}")
    print(f"Output saved to: {save_path.resolve()}")


if __name__ == "__main__":
    main()
