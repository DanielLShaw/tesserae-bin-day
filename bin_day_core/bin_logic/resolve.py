"""Stream resolution: an event title -> {id, label, icon, body, lid colours}.

UK councils use no standard bin colours, so a title is read for colour words
and material keywords, after any user mapping. Colours are palette names
("light_blue") or user hex values; converting names to hex happens later.

Many councils give every bin the same body (usually black or dark grey) and
tell them apart by lid, naming them by it: "blue-lidded bin", "pink lid". A
colour word followed by "lid" colours only the lid.
"""

import re

# Material stream -> (Phosphor icon, default colour name).
MATERIAL_STYLES = {
    "refuse": ("trash", "black"),
    "recycling": ("recycle", "blue"),
    "garden": ("leaf", "green"),
    "food": ("fork-knife", "light_grey"),
    "glass": ("wine", "light_blue"),
    "paper": ("newspaper", "white"),
}

# Keyword or phrase -> material stream.
MATERIAL_KEYWORDS = (
    ("refuse", "refuse"),
    ("general", "refuse"),
    ("residual", "refuse"),
    ("rubbish", "refuse"),
    ("household waste", "refuse"),
    ("non-recyclable", "refuse"),
    ("landfill", "refuse"),
    ("recycling", "recycling"),
    ("recyclable", "recycling"),
    ("mixed", "recycling"),
    ("dry mixed", "recycling"),
    ("garden", "garden"),
    ("green waste", "garden"),
    ("organic", "garden"),
    ("food", "food"),
    ("caddy", "food"),
    ("glass", "glass"),
    ("bottles", "glass"),
    ("jars", "glass"),
    ("paper", "paper"),
    ("card", "paper"),
    ("cardboard", "paper"),
)

# Colour word -> palette name.
COLOUR_WORDS = (
    ("dark grey", "dark_grey"),
    ("dark gray", "dark_grey"),
    ("light blue", "light_blue"),
    ("light grey", "light_grey"),
    ("light gray", "light_grey"),
    ("black", "black"),
    ("grey", "grey"),
    ("gray", "grey"),
    ("blue", "blue"),
    ("green", "green"),
    ("brown", "brown"),
    ("purple", "purple"),
    ("pink", "pink"),
    ("maroon", "maroon"),
    ("burgundy", "burgundy"),
    ("red", "red"),
    ("yellow", "yellow"),
    ("orange", "orange"),
    ("white", "white"),
)

FALLBACK_COLOUR = "grey"
LID_CODED_BODY = "dark_grey"  # the body of a bin named by its lid colour

# "blue lid", "red-lidded", "grey lids": colour word -> lid colour.
_LID_PHRASES = [
    (re.compile(rf"\b{re.escape(word)}[\s-]*lid(?:s|ded)?\b", re.IGNORECASE), name)
    for word, name in COLOUR_WORDS
]

# Stream ids in display order: the materials, then anything unrecognised.
STREAM_ORDER = (*MATERIAL_STYLES, "other")

ICON_MATERIALS = {icon: material for material, (icon, _) in MATERIAL_STYLES.items()}

# Fields a fixed-rule stream may set on itself, over any title mapping.
OVERRIDE_FIELDS = ("icon", "body_colour", "lid_colour")

# Accepted spellings of a palette colour in a user mapping: the colour words
# ("Light blue", "gray") and the palette names themselves ("light_blue").
_COLOUR_LOOKUP = dict(COLOUR_WORDS) | {name: name for _, name in COLOUR_WORDS}
_HEX_COLOUR = re.compile(r"#(?:[0-9a-f]{3}|[0-9a-f]{6})", re.IGNORECASE)


def clean_text(value):
    """``value`` stripped, or "" for anything that is not a string."""
    return value.strip() if isinstance(value, str) else ""


def _colour(value):
    """A palette name or lower-case hex for a mapping colour, else None."""
    text = clean_text(value)
    if _HEX_COLOUR.fullmatch(text):
        return text.lower()
    return _COLOUR_LOOKUP.get(text.lower())


def _icon(value):
    text = clean_text(value).lower()
    return text.removeprefix("ph-") or None


def _matches(text, phrases):
    """(start, end, value) for every whole-word, case-insensitive phrase hit."""
    for phrase, value in phrases:
        for m in re.finditer(rf"\b{re.escape(phrase)}\b", text, re.IGNORECASE):
            yield m.start(), m.end(), value


def _first_match(text, phrases):
    """The earliest hit in ``text``, or None."""
    return min(_matches(text, phrases), key=lambda hit: hit[0], default=None)


def _find_mapping(title, mappings):
    """The user mapping for ``title``: an exact match, else the first whole-word
    "contains" match in list order. Matching ignores case."""
    usable = [m for m in mappings if clean_text(m.get("match"))]
    for mapping in usable:
        if clean_text(mapping["match"]).lower() == title.lower():
            return mapping
    for mapping in usable:
        if _first_match(title, [(clean_text(mapping["match"]), mapping)]):
            return mapping
    return {}


def _blank(text, start, end):
    return text[:start] + " " * (end - start) + text[end:]


def _mask_materials(title):
    """Blank out material phrases so "green waste" is not read as a colour."""
    for start, end, _ in _matches(title, MATERIAL_KEYWORDS):
        title = _blank(title, start, end)
    return title


def _lid_match(text):
    """The earliest "<colour> lid" phrase in ``text`` as (start, end, colour)."""
    hits = [
        (m.start(), m.end(), name) for regex, name in _LID_PHRASES for m in regex.finditer(text)
    ]
    return min(hits, key=lambda hit: hit[0], default=None)


def resolve_stream(title, mappings=(), overrides=None):
    """Resolve an event title to a stream. Icon and colour are resolved
    separately; for each, the first rule that applies wins:

    1. ``overrides`` (a fixed-rule stream's own fields), then the user's
       mapping for this title
    2. a colour word in the title (colour only; material phrases masked):
       "<colour> lid" for the lid, any other colour word for the body
    3. a material keyword in the title (its icon and default colour); a bin
       named by its lid colour gets a dark grey body instead
    4. no icon, grey
    """
    title = title.strip()
    mapping = _find_mapping(title, mappings) | {
        field: value
        for field, value in (overrides or {}).items()
        if field in OVERRIDE_FIELDS and clean_text(value)
    }

    material_hit = _first_match(title, MATERIAL_KEYWORDS)
    material = material_hit[2] if material_hit else "other"
    icon = MATERIAL_STYLES[material][0] if material in MATERIAL_STYLES else None
    mapped_icon = _icon(mapping.get("icon"))
    if mapped_icon:
        icon = mapped_icon
        material = ICON_MATERIALS.get(mapped_icon, material)

    colour_text = _mask_materials(title)
    lid_hit = _lid_match(colour_text)
    if lid_hit:
        colour_text = _blank(colour_text, lid_hit[0], lid_hit[1])
        default_colour = LID_CODED_BODY
    else:
        default_colour = MATERIAL_STYLES.get(material, (None, FALLBACK_COLOUR))[1]
    colour_hit = _first_match(colour_text, COLOUR_WORDS)
    body = _colour(mapping.get("body_colour")) or (colour_hit[2] if colour_hit else default_colour)
    return {
        "id": material,
        "label": clean_text(mapping.get("label")) or title,
        "icon": icon,
        "body_colour": body,
        "lid_colour": _colour(mapping.get("lid_colour")) or (lid_hit[2] if lid_hit else body),
    }


def is_hidden(title, mappings):
    """True when the user mapping for ``title``, the one that would style it,
    has Hide ticked: that collection is left off the widget entirely."""
    return _find_mapping(title.strip(), mappings).get("hide") is True
