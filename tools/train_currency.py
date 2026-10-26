"""
Train the currency classifier on your laptop CPU (YOLOv8-nano classification).

    .venv\\Scripts\\python tools\\train_currency.py [--epochs 25] [--data path\\to\\folder]

Expected input (default data/currency_dataset):
    currency_dataset/
        10/ *.jpg      20/ *.jpg     50/ ...   100/   200/   500/   background/

You can also merge a public dataset (e.g. Kaggle "Indian Currency Notes") into these
folders - just copy the images into the matching denomination folder.

The script makes an 80/20 train/val split and saves the best model to
models/currency_cls.pt, which main.py picks up automatically.
"""
import argparse
import random
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402

IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def make_split(src: Path, dst: Path, val_ratio=0.2):
    if dst.exists():
        shutil.rmtree(dst)
    classes = [d for d in src.iterdir() if d.is_dir()]
    if len(classes) < 2:
        sys.exit(f"Need at least 2 class folders in {src}")
    for c in classes:
        imgs = [p for p in c.iterdir() if p.suffix.lower() in IMG_EXT]
        if len(imgs) < 5:
            print(f"  skipping '{c.name}' (only {len(imgs)} images)")
            continue
        random.shuffle(imgs)
        n_val = max(1, int(len(imgs) * val_ratio))
        for split, items in (("val", imgs[:n_val]), ("train", imgs[n_val:])):
            out = dst / split / c.name
            out.mkdir(parents=True, exist_ok=True)
            for p in items:
                shutil.copy2(p, out / p.name)
        print(f"  {c.name:>10}: {len(imgs) - n_val} train / {n_val} val")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(config.CURRENCY_DATASET_DIR))
    ap.add_argument("--epochs", type=int, default=25)
    ap.add_argument("--imgsz", type=int, default=224)
    a = ap.parse_args()

    random.seed(42)
    split_dir = config.DATA_DIR / "currency_split"
    print("Preparing train/val split...")
    make_split(Path(a.data), split_dir)

    from ultralytics import YOLO
    model = YOLO("yolov8n-cls.pt")
    model.train(data=str(split_dir), epochs=a.epochs, imgsz=a.imgsz, batch=16,
                device="cpu", workers=0, project=str(config.BASE_DIR / "runs"),
                name="currency", exist_ok=True,
                # augmentations that mimic real usage
                degrees=15, fliplr=0.5, flipud=0.2, hsv_v=0.4, hsv_s=0.4, scale=0.3)
    best = config.BASE_DIR / "runs" / "currency" / "weights" / "best.pt"
    config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(best, config.CURRENCY_MODEL)
    print(f"\nDone! Model saved to {config.CURRENCY_MODEL}")


if __name__ == "__main__":
    main()
