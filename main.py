import argparse
import os

import cv2
import numpy as np

try:
    import mss
except ImportError:
    mss = None

try:
    from PIL import ImageGrab
except ImportError:
    ImageGrab = None


TEMPLATE_DIR = "Karty_new"
DEBUG_DIR = "debug"
MIN_SCORE = 0.80
NORMALIZED_SIZE = (90, 125)

# Card slot rectangles are measured as (x, y, width, height) in screenshot pixels.
# The bundled sample image is configured for these two visible card slots.
CARD_SLOTS = [
    (573, 764, 92, 127),
    (951, 773, 90, 125),
]


def load_templates(template_dir=TEMPLATE_DIR):
    templates = {}

    for filename in sorted(os.listdir(template_dir)):
        if not filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            continue

        card_name = os.path.splitext(filename)[0].upper()
        path = os.path.join(template_dir, filename)
        img = cv2.imread(path)

        if img is None:
            print(f"Warning: could not read template {path}")
            continue

        templates[card_name] = img

    return templates


def normalize_card(img, size=NORMALIZED_SIZE):
    img = cv2.resize(img, size)
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def compare_card(slot_img, template_img):
    slot_norm = normalize_card(slot_img)
    template_norm = normalize_card(template_img)
    result = cv2.matchTemplate(slot_norm, template_norm, cv2.TM_CCOEFF_NORMED)
    return float(result.max())


def classify_card(slot_img, templates):
    best_name = None
    best_score = -1.0
    results = []

    for name, template_img in templates.items():
        score = compare_card(slot_img, template_img)
        results.append((name, score))

        if score > best_score:
            best_score = score
            best_name = name

    results.sort(key=lambda item: item[1], reverse=True)
    return best_name, best_score, results[:5]


def format_card_name(name):
    name = name.upper()
    return f"{name[:-1]}-{name[-1]}"


def take_screenshot():
    if mss is not None:
        with mss.mss() as screen_capture:
            monitor = screen_capture.monitors[0]
            screenshot = screen_capture.grab(monitor)
            bgra = np.array(screenshot)
            return cv2.cvtColor(bgra, cv2.COLOR_BGRA2BGR)

    if ImageGrab is not None:
        screenshot = ImageGrab.grab()
        rgb = np.array(screenshot)
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

    raise RuntimeError(
        "No screenshot backend is available. Install mss with: pip install mss"
    )


def load_image(path):
    if path:
        img = cv2.imread(path)
        if img is None:
            raise RuntimeError(f"Could not read image: {path}")
        return img

    return take_screenshot()


def crop_slot(img, slot):
    x, y, w, h = slot
    crop = img[y:y + h, x:x + w]

    if crop.size == 0:
        raise RuntimeError(f"Slot {slot} is outside the image bounds.")

    return crop


def read_cards(img, templates, min_score=MIN_SCORE, debug_dir=DEBUG_DIR):
    if debug_dir:
        os.makedirs(debug_dir, exist_ok=True)

    cards = []

    for slot_number, slot in enumerate(CARD_SLOTS, start=1):
        slot_img = crop_slot(img, slot)

        if debug_dir:
            debug_path = os.path.join(debug_dir, f"slot_{slot_number}.png")
            cv2.imwrite(debug_path, slot_img)

        card_name, score, top5 = classify_card(slot_img, templates)
        result = format_card_name(card_name) if score >= min_score else "UNKNOWN"
        cards.append(result)

        print(f"Slot {slot_number}: {result} | score={score:.3f}")
        print("Top 5:")
        for name, top_score in top5:
            print(f"  {format_card_name(name):5s} {top_score:.3f}")

    return cards


def parse_args():
    parser = argparse.ArgumentParser(
        description="Reads configured poker-card slots from a screenshot or image."
    )
    parser.add_argument(
        "--image",
        help="Read this image instead of taking a live screenshot.",
    )
    parser.add_argument(
        "--template-dir",
        default=TEMPLATE_DIR,
        help=f"Directory with one template image per card. Default: {TEMPLATE_DIR}",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=MIN_SCORE,
        help=f"Minimum match score required for a known card. Default: {MIN_SCORE}",
    )
    parser.add_argument(
        "--debug-dir",
        default=DEBUG_DIR,
        help=f"Directory for cropped slot previews. Use an empty value to disable. Default: {DEBUG_DIR}",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    templates = load_templates(args.template_dir)

    if not templates:
        raise RuntimeError(f"No template images found in {args.template_dir}.")

    img = load_image(args.image)
    debug_dir = args.debug_dir or None
    cards = read_cards(img, templates, args.min_score, debug_dir)

    print()
    print("Detected:", cards)


if __name__ == "__main__":
    main()
