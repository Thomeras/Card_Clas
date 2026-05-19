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


points = []
rectangles = []


def draw_preview(img):
    preview = img.copy()

    for i, (x, y, w, h) in enumerate(rectangles, start=1):
        cv2.rectangle(preview, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(
            preview,
            str(i),
            (x, y - 8),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
        )

    if len(points) == 1:
        x, y = points[0]
        cv2.circle(preview, (x, y), 5, (0, 255, 255), -1)

    return preview


def mouse_callback(event, x, y, flags, param):
    global points, rectangles

    img = param

    if event == cv2.EVENT_LBUTTONDOWN:
        points.append((x, y))
        print(f"Click: x={x}, y={y}")

        if len(points) == 2:
            x1, y1 = points[0]
            x2, y2 = points[1]

            left = min(x1, x2)
            top = min(y1, y2)
            right = max(x1, x2)
            bottom = max(y1, y2)

            w = right - left
            h = bottom - top

            rectangles.append((left, top, w, h))
            print(f"Added slot: (x={left}, y={top}, w={w}, h={h})")
            print(f"Corners: (x1={left}, y1={top}, x2={right}, y2={bottom})")
            points = []

        cv2.imshow("Select slots", draw_preview(img))


def save_crops(img):
    os.makedirs("debug", exist_ok=True)

    preview = img.copy()

    for i, (x, y, w, h) in enumerate(rectangles, start=1):
        crop = img[y:y+h, x:x+w]

        crop_path = f"debug/slot_{i}.png"
        cv2.imwrite(crop_path, crop)

        cv2.rectangle(preview, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(
            preview,
            str(i),
            (x, y - 8),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
        )

        print(f"Saved crop: {crop_path}")

    cv2.imwrite("debug/slots_preview.png", preview)
    print("Saved preview: debug/slots_preview.png")


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


def parse_args():
    parser = argparse.ArgumentParser(description="Measure card slot coordinates.")
    parser.add_argument(
        "--screenshot",
        action="store_true",
        help="Use a live screenshot instead of image.png.",
    )
    parser.add_argument(
        "--image",
        default="image.png",
        help="Image used for measuring slots when --screenshot is not set.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    img = take_screenshot() if args.screenshot else cv2.imread(args.image)

    if img is None:
        raise RuntimeError(f"Could not read {args.image}")

    print("Controls:")
    print("- left mouse button: click the top-left and bottom-right slot corners")
    print("- u: undo the last slot")
    print("- s: save slot crops")
    print("- q: quit and print CARD_SLOTS")
    print()

    cv2.imshow("Select slots", draw_preview(img))
    cv2.setMouseCallback("Select slots", mouse_callback, img)

    while True:
        key = cv2.waitKey(1) & 0xFF

        if key == ord("u"):
            if rectangles:
                removed = rectangles.pop()
                print(f"Removed last slot: {removed}")
                cv2.imshow("Select slots", draw_preview(img))

        elif key == ord("s"):
            save_crops(img)

        elif key == ord("q"):
            break

    cv2.destroyAllWindows()

    print("\nFORMAT FOR main.py:")
    print("CARD_SLOTS = [")
    for x, y, w, h in rectangles:
        print(f"    ({x}, {y}, {w}, {h}),")
    print("]")

    print("\nCorner format for reference:")
    print("RECT_CORNERS = [")
    for x, y, w, h in rectangles:
        print(f"    ({x}, {y}, {x + w}, {y + h}),")
    print("]")


if __name__ == "__main__":
    main()
