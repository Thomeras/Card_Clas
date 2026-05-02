import cv2
import os


CARD_SLOTS = [
    (573, 764, 92, 127),
    (951, 773, 90, 125),
]

TEMPLATE_DIR = "Karty_new"
MIN_SCORE = 0.80


def load_templates(template_dir=TEMPLATE_DIR):
    templates = {}

    for filename in os.listdir(template_dir):
        if not filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            continue

        card_name = os.path.splitext(filename)[0].upper()
        path = os.path.join(template_dir, filename)

        img = cv2.imread(path)

        if img is None:
            print(f"Varování: nepodařilo se načíst {path}")
            continue

        templates[card_name] = img

    return templates


def normalize_card(img, size=(90, 125)):
    img = cv2.resize(img, size)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return gray


def compare_card(slot_img, template_img):
    slot_norm = normalize_card(slot_img)
    template_norm = normalize_card(template_img)

    result = cv2.matchTemplate(
        slot_norm,
        template_norm,
        cv2.TM_CCOEFF_NORMED
    )

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
    rank = name[:-1]
    suit = name[-1]
    return f"{rank}-{suit}"


def recognize_slots(img, templates):
    detected_cards = []

    for i, (x, y, w, h) in enumerate(CARD_SLOTS):
        slot_img = img[y:y+h, x:x+w]

        card_name, score, top5 = classify_card(slot_img, templates)

        if score < MIN_SCORE:
            result = "UNKNOWN"
        else:
            result = format_card_name(card_name)

        detected_cards.append(result)

        print()
        print(f"Slot {i}: {result} | score={score:.3f}")

        print("Top 5:")
        for name, s in top5:
            print(f"  {format_card_name(name):5s} {s:.3f}")

    return detected_cards


def main():
    img = cv2.imread("image.png")

    if img is None:
        raise RuntimeError("Nepodařilo se načíst debug_screenshot.png")

    templates = load_templates()

    if not templates:
        raise RuntimeError(f"Ve složce {TEMPLATE_DIR} nejsou žádné obrázky.")

    print(f"Načteno templates: {len(templates)}")

    detected_cards = recognize_slots(img, templates)

    print()
    print("Detected:", detected_cards)


if __name__ == "__main__":
    main()