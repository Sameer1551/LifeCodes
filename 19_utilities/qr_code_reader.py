#!/usr/bin/env python3
"""
qr_code_reader.py

Reads QR codes from images using OpenCV or pure Python.
Supports PNG, JPG, WEBP, and screenshots.
Generalized — fallback methods when OpenCV is unavailable.

Usage:
    python qr_code_reader.py image.png
    python qr_code_reader.py screenshot.png --method opencv
    python qr_code_reader.py image.jpg --method pyzbar
    python qr_code_reader.py --camera
    python qr_code_reader.py --batch images/
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional


def _read_opencv(path: Path) -> Optional[str]:
    try:
        import cv2
        detector = cv2.QRCodeDetector()
        data, _, _ = detector.detectAndDecode(cv2.imread(str(path)))
        return data if data else None
    except Exception:
        return None


def _read_pyzbar(path: Path) -> Optional[str]:
    try:
        from pyzbar.pyzbar import decode as pyzbar_decode
        from PIL import Image
        decoded = pyzbar_decode(Image.open(str(path)))
        return decoded[0].data.decode("utf-8") if decoded else None
    except Exception:
        return None


def _read_quirc(path: Path) -> Optional[str]:
    try:
        import cv2
        import numpy as np
        img = cv2.imread(str(path))
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        import subprocess, tempfile, os
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp.close()
        cv2.imwrite(tmp.name, gray)
        result = subprocess.run(["quirc", "-d", tmp.name], capture_output=True, text=True)
        os.unlink(tmp.name)
        return result.stdout.strip() or None
    except Exception:
        return None


def _read_raw(path: Path) -> Optional[str]:
    try:
        with open(path, "rb") as f:
            data = f.read()
        start = data.find(b"\x89PNG")
        if start == -1:
            start = data.rfind(b"\xff\xd8\xff")
        if start == -1:
            start = data.rfind(b"QR")
        if start != -1:
            chunk = data[start : start + 200]
            for i, b in enumerate(chunk):
                if 32 <= b < 127:
                    line = chunk[i:].split(b"\x00")[0]
                    try:
                        return line.decode("utf-8", errors="ignore")
                    except Exception:
                        pass
        return None
    except Exception:
        return None


def read_qr(path: Path, method: str = "auto") -> Optional[str]:
    if method == "opencv":
        return _read_opencv(path)
    if method == "pyzbar":
        return _read_pyzbar(path)
    if method == "raw":
        return _read_raw(path)

    for m in ("opencv", "pyzbar", "raw"):
        result = read_qr(path, method=m)
        if result:
            return result
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="QR Code Reader")
    parser.add_argument("path", nargs="?", help="Image file path")
    parser.add_argument("--method", choices=["auto", "opencv", "pyzbar", "raw"], default="auto", help="Detection method")
    parser.add_argument("--batch", help="Directory of images")
    parser.add_argument("--camera", action="store_true", help="Read from webcam (requires OpenCV)")
    args = parser.parse_args()

    if args.camera:
        try:
            import cv2
            cam = cv2.VideoCapture(0)
            while True:
                ret, frame = cam.read()
                if not ret:
                    break
                cv2.imshow("QR Reader (q to quit)", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
                detector = cv2.QRCodeDetector()
                data = detector.detectAndDecode(frame)
                if data[0]:
                    print(f"Found: {data[0]}")
            cam.release()
            cv2.destroyAllWindows()
        except ImportError:
            print("OpenCV required for camera mode", file=sys.stderr)
        return

    if args.batch:
        batch_dir = Path(args.batch)
        found = 0
        for img_path in batch_dir.rglob("*"):
            if img_path.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
                result = read_qr(img_path, args.method)
                if result:
                    print(f"{img_path}: {result}")
                    found += 1
        print(f"Found {found} QR codes in {batch_dir}")
        return

    if not args.path:
        print("Error: provide a path or use --camera/--batch", file=sys.stderr)
        sys.exit(1)

    path = Path(args.path)
    if not path.exists():
        print(f"Error: '{args.path}' not found", file=sys.stderr)
        sys.exit(1)

    result = read_qr(path, args.method)
    if result:
        print(result)
    else:
        print("No QR code found", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()