import cv2

from main import TEMPLATE_DIR, load_templates, read_cards


def main():
    img = cv2.imread("image.png")

    if img is None:
        raise RuntimeError("Could not read image.png")

    templates = load_templates(TEMPLATE_DIR)

    if not templates:
        raise RuntimeError(f"No template images found in {TEMPLATE_DIR}.")

    print(f"Loaded templates: {len(templates)}")
    detected_cards = read_cards(img, templates)

    print()
    print("Detected:", detected_cards)


if __name__ == "__main__":
    main()
