"""Feine Quell-Kategorien auf wenige Einkaufs-Gruppen abbilden.

Die Quellen liefern ~145 verschiedene Kategorien ("Hartkaese", "Weissweine",
"Tiefkuehlpizza & -flammkuchen", "Toepfe"). Als Filter im Dashboard ist das
unbrauchbar - hier werden sie auf 13 Gruppen zusammengefasst.

Zwei Mechanismen, in fester Reihenfolge (erster Treffer gewinnt):

  "kase"   Teiltreffer - noetig fuer deutsche Komposita ("Hartkaese",
           "Frischkaese & Huettenkaese" sollen alle auf Kaese passen).
  "=eis"   exakter Treffer - fuer kurze, mehrdeutige Woerter. "eis" als
           Teiltreffer wuerde sonst "Weisswein" fangen, "ol" (fuer Oel)
           steckt in "Folien", "Cola" und "Schokolade".

Die Reihenfolge korrigiert Mehrdeutigkeiten: "Dessertwein" muss zum Alkohol,
nicht zu den Desserts; "Alkoholfreies Bier" zu den Getraenken.
"""
from __future__ import annotations

import unicodedata

SONSTIGES = "Sonstiges"

_RULES: list[tuple[str, tuple[str, ...]]] = [
    # --- Vorab-Korrekturen: Faelle, die sonst falsch einsortiert wuerden ---
    # Tiefkuehl zuerst, sonst faengt "pizza" unten die Tiefkuehlpizza ab.
    ("Tiefkühl", ("tiefkuhl", "tiefkuehl", "gefrier", "pommes")),
    # "Zahnpasta" enthaelt "pasta", "Schokoaufstrich" faellt sonst unter
    # "aufstrich" zu den Molkereiprodukten.
    ("Drogerie & Haushalt", ("zahn",)),
    ("Süßes & Snacks", ("schokoaufstrich",)),
    ("Getränke", ("alkoholfrei", "eistee", "safte", "saefte")),
    ("Vorrat", ("teigwaren", "pizza", "tomatenprodukte", "kartoffelgericht",
                "gemusekonserven")),
    ("Baby & Kind", ("baby", "windel", "glaschen")),

    # --- Hauptgruppen ---
    ("Fisch", ("fisch", "lachs", "thunfisch", "meeresfruchte", "muschel",
               "garnelen", "sushi", "kaviar")),
    ("Fleisch & Wurst", (
        "fleisch", "wurst", "schinken", "salami", "speck", "faschiert",
        "rind", "schwein", "huhn", "gefluegel", "pute", "lamm", "wurstel",
        "aufschnitt", "mariniert", "grillspezialitaten")),
    ("Obst & Gemüse", (
        "obst", "gemuse", "salat", "tomaten", "gurken", "zwiebeln",
        "knoblauch", "kartoffel", "pilze", "champions", "banane", "apfel",
        "beeren", "zitrus", "melone", "trauben", "blattgemuse")),
    ("Alkohol", (
        "bier", "wein", "sekt", "schaumwein", "perlwein", "prosecco",
        "spirituos", "schnaps", "likor", "rum", "vodka", "wodka", "gin",
        "whisk", "cognac", "aperitif", "digestif", "alkopop", "cider",
        "radler", "champagner", "=rose")),
    ("Kaffee & Tee", ("kaffee", "tee", "kakao", "espresso", "ganze bohne",
                      "=gemahlen", "kapsel")),
    ("Milch, Käse & Eier", (
        "milch", "kase", "joghurt", "topfen", "obers", "rahm", "butter",
        "molkerei", "eier", "quark", "feta", "mozarella", "mozzarella",
        "dessert", "aufstrich", "margarine", "schmelzkase")),
    ("Brot & Gebäck", (
        "brot", "brotchen", "geback", "gebaeck", "semmel", "backwaren",
        "knackebrot", "zwieback", "kuchen", "toast", "weckerl", "striezel")),
    ("Süßes & Snacks", (
        "schokolad", "sussigkeit", "susse", "keks", "waffel", "schnitten",
        "riegel", "chips", "knabber", "snack", "eiscreme", "eis am stiel",
        "speiseeis", "bonbon", "gummi", "praline", "torte", "nusse",
        "stanizl", "=eis")),
    ("Getränke", (
        "getrank", "wasser", "saft", "limonad", "softdrink", "cola",
        "smoothie", "sirup", "energy", "nektar")),
    ("Vorrat", (
        "nudel", "pasta", "reis", "mehl", "zucker", "essig", "konserv",
        "sugo", "sauce", "sosse", "ketchup", "dressing", "gewurz", "wurz",
        "bohnen", "linsen", "erbsen", "mais", "oliven", "kapern", "pesto",
        "hafer", "musli", "cerealien", "marmelade", "honig", "suppe",
        "fertiggericht", "asia", "asien", "mediterran", "orientalisch",
        "beilagen", "raps", "veganes", "protein", "spezialitaten",
        "feinkost", "hulsenfr", "=ole und fette", "=ol", "speiseol")),
    ("Drogerie & Haushalt", (
        "waschmittel", "reiniger", "reinigung", "putz", "spul", "hygiene",
        "deo", "zahn", "shampoo", "seife", "dusch", "creme", "kosmetik",
        "papier", "servietten", "tucher", "beutel", "folie", "mullsack",
        "topf", "pfanne", "griller", "geschirr", "batterie", "textil",
        "rasier", "sonnenschutz", "=hand")),
]


def _norm(s: str) -> str:
    """Kleinschreibung ohne Umlaute/Akzente, damit die Regeln simpel bleiben."""
    s = (s or "").lower()
    s = s.replace("ä", "a").replace("ö", "o").replace("ü", "u").replace("ß", "ss")
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


def group_for(category: str | None) -> str:
    """Feine Quell-Kategorie -> Einkaufs-Gruppe. Unbekanntes -> "Sonstiges"."""
    if not category:
        return SONSTIGES
    n = _norm(category)
    for group, keywords in _RULES:
        for kw in keywords:
            if kw.startswith("="):
                if n == kw[1:]:
                    return group
            elif kw in n:
                return group
    return SONSTIGES


# Anzeigereihenfolge im Dashboard - grob der Weg durch den Supermarkt.
# Bewusst getrennt von der Regel-Reihenfolge oben, die nur der Trefferlogik dient.
DISPLAY_ORDER = [
    "Obst & Gemüse",
    "Fleisch & Wurst",
    "Fisch",
    "Milch, Käse & Eier",
    "Brot & Gebäck",
    "Tiefkühl",
    "Vorrat",
    "Süßes & Snacks",
    "Kaffee & Tee",
    "Getränke",
    "Alkohol",
    "Drogerie & Haushalt",
    "Baby & Kind",
    SONSTIGES,
]


def all_groups() -> list[str]:
    """Alle Gruppen in Ladenreihenfolge (stabile Sortierung im Dashboard)."""
    return list(DISPLAY_ORDER)


def sort_key(group: str) -> int:
    """Sortierindex einer Gruppe; Unbekanntes ans Ende."""
    try:
        return DISPLAY_ORDER.index(group)
    except ValueError:
        return len(DISPLAY_ORDER)
