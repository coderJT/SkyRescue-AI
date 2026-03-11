import argparse
import csv
from pathlib import Path
from typing import Dict, Any

import yaml
from ultralytics import YOLO


def load_dataset_config(dataset_yaml: Path) -> Dict[str, Any]:
    """Load and minimally validate the Roboflow/YOLO dataset config."""
    if not dataset_yaml.exists():
        raise FileNotFoundError(f"Dataset YAML not found: {dataset_yaml}")

    with dataset_yaml.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if "names" not in config or "nc" not in config:
        raise ValueError("Dataset YAML must contain both 'names' and 'nc'.")

    return config


def build_resolved_yaml(dataset_root: Path, source_cfg: Dict[str, Any], out_yaml: Path) -> Path:
    """Write a training YAML with absolute paths to avoid relative path mismatches."""
    train_images = dataset_root / "train" / "images"
    val_images = dataset_root / "valid" / "images"
    test_images = dataset_root / "test" / "images"

    missing = [
        p for p in [train_images, val_images, test_images]
        if not p.exists()
    ]
    if missing:
        raise FileNotFoundError(f"Missing dataset directories: {missing}")

    resolved_cfg = {
        "train": str(train_images.resolve()),
        "val": str(val_images.resolve()),
        "test": str(test_images.resolve()),
        "nc": int(source_cfg["nc"]),
        "names": source_cfg["names"],
    }

    out_yaml.parent.mkdir(parents=True, exist_ok=True)
    with out_yaml.open("w", encoding="utf-8") as f:
        yaml.safe_dump(resolved_cfg, f, sort_keys=False)

    return out_yaml


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def log_training_report(run_dir: Path, dataset_cfg: Dict[str, Any], best_weights: Path) -> None:
    """Log final accuracy and loss values to the console."""
    results_csv = run_dir / "results.csv"
    if not results_csv.exists():
        print(f"Warning: results.csv not found at {results_csv}. Skipping report logging.")
        return

    with results_csv.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print("Warning: results.csv is empty. Skipping report logging.")
        return

    last = rows[-1]

    accuracy = _safe_float(last.get("metrics/mAP50(B)"))
    train_loss = _safe_float(last.get("train/box_loss"))
    val_loss = _safe_float(last.get("val/box_loss"))

    print("\n=== Training Report ===")
    print(f"Epochs:    {len(rows)}")
    print(f"Accuracy:  {accuracy:.4f}  (mAP@50)")
    print(f"Train Loss:{train_loss:.4f}  (box loss)")
    print(f"Val Loss:  {val_loss:.4f}  (box loss)")
    print("======================")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train fire detection model using YOLOv8.")
    parser.add_argument(
        "--dataset-yaml",
        type=Path,
        default=Path("data") / "data.yaml",
        help="Path to original dataset yaml (default: data/data.yaml)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="yolov8n.pt",
        help="YOLO base model checkpoint (default: yolov8n.pt)",
    )
    parser.add_argument("--epochs", type=int, default=50, help="Training epochs")
    parser.add_argument("--imgsz", type=int, default=640, help="Image size")
    parser.add_argument("--batch", type=int, default=16, help="Batch size")
    parser.add_argument(
        "--project",
        type=Path,
        default=Path("ML model") / "artifacts",
        help="Output project directory",
    )
    parser.add_argument(
        "--name",
        type=str,
        default="fire_detector",
        help="Run name inside project directory",
    )

    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    dataset_yaml = args.dataset_yaml if args.dataset_yaml.is_absolute() else repo_root / args.dataset_yaml
    dataset_root = dataset_yaml.parent

    source_cfg = load_dataset_config(dataset_yaml)
    resolved_yaml = build_resolved_yaml(
        dataset_root=dataset_root,
        source_cfg=source_cfg,
        out_yaml=repo_root / "ML model" / "fire_data_resolved.yaml",
    )

    model = YOLO(args.model)

    results = model.train(
        data=str(resolved_yaml),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        project=str((repo_root / args.project).resolve()),
        name=args.name,
    )

    run_dir = repo_root / args.project / args.name
    best_weights = run_dir / "weights" / "best.pt"
    log_training_report(run_dir=run_dir, dataset_cfg=source_cfg, best_weights=best_weights)

    print("\nTraining complete.")
    print(f"Best model path: {best_weights.resolve()}")
    print(f"Metrics summary: {results.results_dict if hasattr(results, 'results_dict') else 'N/A'}")


if __name__ == "__main__":
    main()
