# Fire Detection Model (YOLOv8)

This folder contains a trainable fire detection model pipeline using your dataset in `data/`.

## Files

- `train_fire_model.py`: trains a YOLOv8 model on `data/train`, `data/valid`, and `data/test`
- `predict_fire.py`: runs inference on a single image/video with trained weights
- `requirements.txt`: model dependencies
- `fire_data_resolved.yaml`: auto-generated at training time

## 1. Install dependencies

```bash
pip install -r "ML model/requirements.txt"
```

## 2. Train model

Run from repository root:

```bash
python "ML model/train_fire_model.py" --epochs 50 --imgsz 640 --batch 16
```

Training output:
- Weights: `ML model/artifacts/fire_detector/weights/best.pt`
- Accuracy/loss report: printed in terminal after training

## 3. Predict fire on an image

```bash
python "ML model/predict_fire.py" --source "data/test/images/<your_image>.jpg"
```

Prediction output image:
- `ML model/predictions/prediction.jpg`

## Optional: custom base model

```bash
python "ML model/train_fire_model.py" --model yolov8s.pt --epochs 100
```
