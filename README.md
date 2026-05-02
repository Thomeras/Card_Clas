# Card_Clas

Jednoduchy Python nastroj na rozpoznani pokerovych karet ze screenshotu.

Program pri kazdem spusteni udela screenshot obrazovky, vyctte aktualni cast handy
a uklada stav do `hand_state.json`:

1. prvni spusteni: tvoje karty, pozice 1 a 2
2. druhe spusteni: flop, pozice 3 az 5
3. treti spusteni: turn, pozice 6
4. ctvrte spusteni: river, pozice 7

## Instalace

```bash
pip install -r requirements.txt
```

## Pouziti

Nejdriv zmer souradnice slotu karet:

```bash
python select_slot.py --screenshot
```

Vyber postupne vsech 7 pozic a vypsany `CARD_SLOTS` zkopiruj do `main.py`.

Potom pro kazdou cast handy spust:

```bash
python main.py
```

Nova handa:

```bash
python main.py --reset
```

Test na ulozenem screenshotu:

```bash
python main.py --image image.png
```
