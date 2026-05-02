import argparse
import json
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
STATE_PATH = "hand_state.json"
DEBUG_DIR = "debug"

# Pozice jsou cislovane tak, jak pokerova handa prichazi:
# 1-2 tvoje karty, 3-5 flop, 6 turn, 7 river.
#
# Dulezite: sloty 3-7 je potreba jednou zmerit pro tvoje pokerove okno.
# Spust `python select_slot.py --screenshot`, vyber postupne vsech 7 pozic
# a vypsany CARD_SLOTS sem zkopiruj.
CARD_SLOTS = [
    (573, 764, 92, 127),
    (951, 773, 90, 125),
    None,
    None,
    None,
    None,
    None,
]

STREETS = [
    ("preflop", [0, 1], "hole_cards"),
    ("flop", [2, 3, 4], "board"),
    ("turn", [5], "board"),
    ("river", [6], "board"),
]


def load_templates(template_dir=TEMPLATE_DIR):
    templates = {}

    for filename in os.listdir(template_dir):
        if not filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            continue

        card_name = os.path.splitext(filename)[0].upper()
        path = os.path.join(template_dir, filename)
        img = cv2.imread(path)

        if img is None:
            print(f"Varovani: nepodarilo se nacist {path}")
            continue

        templates[card_name] = img

    return templates


def normalize_card(img, size=(90, 125)):
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
        "Neni dostupny zadny screenshot backend. Nainstaluj `mss`: pip install mss"
    )


def load_image(path):
    if path:
        img = cv2.imread(path)
        if img is None:
            raise RuntimeError(f"Nepodarilo se nacist obrazek: {path}")
        return img

    return take_screenshot()


def load_state(path=STATE_PATH):
    if not os.path.exists(path):
        return {"street_index": 0, "hole_cards": [], "board": []}

    with open(path, "r", encoding="utf-8") as state_file:
        return json.load(state_file)


def save_state(state, path=STATE_PATH):
    with open(path, "w", encoding="utf-8") as state_file:
        json.dump(state, state_file, indent=2)


def reset_state(path=STATE_PATH):
    if os.path.exists(path):
        os.remove(path)


def crop_slot(img, slot):
    x, y, w, h = slot
    return img[y:y + h, x:x + w]


def validate_slots(slot_indexes):
    missing = [index + 1 for index in slot_indexes if CARD_SLOTS[index] is None]

    if missing:
        raise RuntimeError(
            "Chybi souradnice pro pozice: "
            + ", ".join(str(index) for index in missing)
            + ". Spust `python select_slot.py --screenshot`, vyber vsech 7 pozic "
            + "a dopln CARD_SLOTS v main.py."
        )


def read_cards_from_slots(img, slot_indexes, templates, street_name):
    os.makedirs(DEBUG_DIR, exist_ok=True)
    cards = []

    for slot_index in slot_indexes:
        slot = CARD_SLOTS[slot_index]
        slot_img = crop_slot(img, slot)

        debug_path = os.path.join(DEBUG_DIR, f"{street_name}_pos_{slot_index + 1}.png")
        cv2.imwrite(debug_path, slot_img)

        card_name, score, top5 = classify_card(slot_img, templates)
        cards.append(card_name)

        print(f"Pozice {slot_index + 1}: {format_card_name(card_name)} | score={score:.3f}")
        print("Top 5:")
        for name, top_score in top5:
            print(f"  {format_card_name(name):5s} {top_score:.3f}")

    return cards


def apply_street(state, img, templates):
    street_index = state.get("street_index", 0)

    if street_index >= len(STREETS):
        raise RuntimeError(
            "Handa uz ma ulozene vsechny streety. "
            "Pro novou handu spust `python main.py --reset`."
        )

    street_name, slot_indexes, target = STREETS[street_index]
    validate_slots(slot_indexes)

    print(f"Street: {street_name}")
    cards = read_cards_from_slots(img, slot_indexes, templates, street_name)

    if target == "hole_cards":
        state["hole_cards"] = cards
    else:
        state["board"].extend(cards)

    state["street_index"] = street_index + 1
    return state


def print_state(state):
    hole_cards = [format_card_name(card) for card in state.get("hole_cards", [])]
    board = [format_card_name(card) for card in state.get("board", [])]

    print()
    print("Aktualni seznam:")
    print(f"  Tvoje karty: {hole_cards}")
    print(f"  Board:       {board}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Nacte karty z aktualniho screenshotu podle faze handy."
    )
    parser.add_argument(
        "--image",
        help="Volitelny testovaci obrazek misto aktualniho screenshotu.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Smaze ulozeny stav handy a zacne znovu od pozic 1-2.",
    )
    parser.add_argument(
        "--state",
        default=STATE_PATH,
        help=f"Cesta ke stavovemu souboru. Vychozi: {STATE_PATH}",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.reset:
        reset_state(args.state)
        print("Stav handy smazan. Dalsi volani zacne od pozic 1-2.")
        return

    templates = load_templates()

    if not templates:
        raise RuntimeError(f"Ve slozce {TEMPLATE_DIR} nejsou zadne obrazky.")

    img = load_image(args.image)
    state = load_state(args.state)
    state = apply_street(state, img, templates)
    save_state(state, args.state)
    print_state(state)


if __name__ == "__main__":
    main()
