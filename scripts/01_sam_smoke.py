"""Try SAM 3.1 on one image.   python scripts/01_sam_smoke.py <image path or URL> "<noun phrase>" """
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np  # noqa: E402
import requests  # noqa: E402
from PIL import Image  # noqa: E402

from lifeline.perception.sam import segment  # noqa: E402


def load(src: str) -> Image.Image:
    if src.startswith("http"):
        return Image.open(io.BytesIO(requests.get(src, timeout=60).content)).convert("RGB")
    return Image.open(src).convert("RGB")


def main() -> None:
    if len(sys.argv) < 3:
        print('Usage: python scripts/01_sam_smoke.py <image path or URL> "<noun phrase>"')
        sys.exit(1)
    image = load(sys.argv[1])
    prompt = sys.argv[2]
    dets = segment(image, prompt)
    print(f"{len(dets)} match(es) for '{prompt}' on a {image.width}x{image.height} image")
    for d in dets:
        print(f"  id={d.object_id} box={d.box} mask_pixels={int(d.mask.sum())}")
    out = Path("out")
    out.mkdir(exist_ok=True)
    overlay = np.array(image).astype(float)
    for d in dets:
        overlay[d.mask] = 0.5 * overlay[d.mask] + 0.5 * np.array([255.0, 0.0, 0.0])
    Image.fromarray(overlay.astype("uint8")).save(out / "sam_overlay.png")
    print("Saved overlay to out/sam_overlay.png")


if __name__ == "__main__":
    main()
