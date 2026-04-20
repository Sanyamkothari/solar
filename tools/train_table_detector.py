"""
Bootstrap trainer for a YOLO table detector.

This script auto-labels historical images using the current heuristic crop
window, then trains a one-class YOLO model and exports the best weights to
QC_Automation/models/table_detector.pt.

The model is intended as a practical bootstrap so the pipeline can run in
YOLO mode immediately. You can later replace it with a fully hand-labeled
model for higher detection quality.
"""
from __future__ import annotations

import argparse
import random
import shutil
from pathlib import Path
import sys

import cv2

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import (
    IMG_CROP_TOP,
    IMG_CROP_BOTTOM,
    IMG_CROP_LEFT,
    IMG_CROP_RIGHT,
)


def _is_image(path: Path) -> bool:
    return path.suffix.lower() in {".jpg", ".jpeg", ".png"}


def _write_yolo_label(label_path: Path, img_w: int, img_h: int) -> None:
    x1 = int(img_w * IMG_CROP_LEFT)
    y1 = int(img_h * IMG_CROP_TOP)
    x2 = int(img_w * IMG_CROP_RIGHT)
    y2 = int(img_h * IMG_CROP_BOTTOM)

    cx = ((x1 + x2) / 2.0) / img_w
    cy = ((y1 + y2) / 2.0) / img_h
    bw = (x2 - x1) / img_w
    bh = (y2 - y1) / img_h

    # class_id cx cy w h
    label_path.write_text(f"0 {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n", encoding="utf-8")


def build_dataset(source_dir: Path, dataset_dir: Path, val_split: float, seed: int) -> Path:
    images = sorted([p for p in source_dir.iterdir() if p.is_file() and _is_image(p)])
    if not images:
        raise RuntimeError(f"No images found in {source_dir}")

    random.seed(seed)
    random.shuffle(images)

    split_idx = max(1, int(len(images) * (1 - val_split)))
    train_imgs = images[:split_idx]
    val_imgs = images[split_idx:] if split_idx < len(images) else images[-1:]

    train_img_dir = dataset_dir / "images" / "train"
    val_img_dir = dataset_dir / "images" / "val"
    train_lbl_dir = dataset_dir / "labels" / "train"
    val_lbl_dir = dataset_dir / "labels" / "val"

    for d in [train_img_dir, val_img_dir, train_lbl_dir, val_lbl_dir]:
        d.mkdir(parents=True, exist_ok=True)

    def copy_and_label(paths: list[Path], img_out_dir: Path, lbl_out_dir: Path) -> int:
        count = 0
        for src in paths:
            img = cv2.imread(str(src))
            if img is None:
                continue

            h, w = img.shape[:2]
            dst_img = img_out_dir / src.name
            shutil.copy2(src, dst_img)

            dst_lbl = lbl_out_dir / f"{src.stem}.txt"
            _write_yolo_label(dst_lbl, w, h)
            count += 1
        return count

    n_train = copy_and_label(train_imgs, train_img_dir, train_lbl_dir)
    n_val = copy_and_label(val_imgs, val_img_dir, val_lbl_dir)

    data_yaml = dataset_dir / "data.yaml"
    data_yaml.write_text(
        "\n".join(
            [
                f"path: {dataset_dir.as_posix()}",
                "train: images/train",
                "val: images/val",
                "names:",
                "  0: table",
                "",
            ]
        ),
        encoding="utf-8",
    )

    print(f"Dataset created at: {dataset_dir}")
    print(f"Train images: {n_train} | Val images: {n_val}")
    print(f"Data YAML: {data_yaml}")
    return data_yaml


def train_model(data_yaml: Path, runs_dir: Path, epochs: int, imgsz: int, batch: int) -> Path:
    from ultralytics import YOLO

    model = YOLO("yolov8n.pt")
    results = model.train(
        data=str(data_yaml),
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        project=str(runs_dir),
        name="table_detector",
        exist_ok=True,
        device="cpu",
        verbose=True,
    )

    best = Path(results.save_dir) / "weights" / "best.pt"
    if not best.exists():
        raise RuntimeError(f"Training completed but best.pt not found at {best}")
    return best


def main() -> None:
    parser = argparse.ArgumentParser(description="Train bootstrap YOLO table detector")
    parser.add_argument("--source", type=str, default="processed", help="Source image directory")
    parser.add_argument("--dataset", type=str, default="models/table_dataset", help="Generated dataset directory")
    parser.add_argument("--runs", type=str, default="models/runs", help="YOLO runs output directory")
    parser.add_argument("--output", type=str, default="models/table_detector.pt", help="Final model path")
    parser.add_argument("--epochs", type=int, default=15, help="Training epochs")
    parser.add_argument("--imgsz", type=int, default=960, help="Training image size")
    parser.add_argument("--batch", type=int, default=8, help="Batch size")
    parser.add_argument("--val-split", type=float, default=0.2, help="Validation split ratio")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--rebuild", action="store_true", help="Delete and rebuild dataset directory")
    args = parser.parse_args()

    source_dir = (BASE_DIR / args.source).resolve()
    dataset_dir = (BASE_DIR / args.dataset).resolve()
    runs_dir = (BASE_DIR / args.runs).resolve()
    output_path = (BASE_DIR / args.output).resolve()

    if not source_dir.exists():
        raise RuntimeError(f"Source directory does not exist: {source_dir}")

    if args.rebuild and dataset_dir.exists():
        shutil.rmtree(dataset_dir, ignore_errors=True)

    data_yaml = build_dataset(source_dir, dataset_dir, args.val_split, args.seed)
    best_weights = train_model(data_yaml, runs_dir, args.epochs, args.imgsz, args.batch)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(best_weights, output_path)

    print(f"\nDone. Model saved to: {output_path}")


if __name__ == "__main__":
    main()
