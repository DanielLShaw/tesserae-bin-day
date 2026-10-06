"""Screenshot scenarios. Each has its own Bin Day Core config (a manual
schedule of bins), a pinned clock, and the cell options to render.

``expect`` is what the cell should show, checked by
tests/test_preview_scenarios.py: ``[(days_until, [icon, ...]), ...]`` for
each collection day, or the start of the error tile's message.

``docs`` scenarios also illustrate docs/bin-colours.md: ``preview/shoot.py
--docs`` renders them at LG and SM into docs/images/.
"""

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

LONDON = ZoneInfo("Europe/London")


def _stream(label, first_date, every_weeks, icon="", body_colour="", lid_colour=""):
    return {
        "label": label,
        "first_date": first_date,
        "every_weeks": every_weeks,
        "icon": icon,
        "body_colour": body_colour,
        "lid_colour": lid_colour,
        "hide": False,
    }


def _at(day, hour, minute=0):
    return datetime(2026, 10, day, hour, minute, tzinfo=LONDON)


# Liverpool's WCS titles; the owner gives the bare "Green" the garden leaf.
LIVERPOOL = [
    _stream("Refuse", "2026-10-07", 2),
    _stream("Green", "2026-10-07", 2, icon="leaf"),
    _stream("Recycling", "2026-10-12", 2),
]


# Milton Keynes' bins: black bodies with black, blue and red lids.
LID_CODED = [
    _stream("Black lid rubbish", "2026-10-07", 2),
    _stream("Blue lid recycling", "2026-10-07", 2),
    _stream("Red lid paper", "2026-10-12", 2),
]


@dataclass(frozen=True)
class Scenario:
    name: str
    description: str
    streams: list
    now: datetime
    expect: object
    cutoff: str = "10:00"
    colours: str = "auto"
    source: str = "schedule"
    theme: str | None = None  # render in this theme whatever the run's
    docs: bool = False

    @property
    def config(self):
        return {"source": self.source, "calendar": "", "schedule": self.streams, "mappings": []}

    @property
    def options(self):
        return {"cutoff": self.cutoff, "colours": self.colours}


SCENARIOS = [
    Scenario(
        "next-week",
        "The mockup data: Refuse and Green tomorrow, Recycling in 6 days.",
        LIVERPOOL,
        _at(6, 8),
        [(1, ["trash", "leaf"]), (6, ["recycle"])],
    ),
    Scenario(
        "dark-mode",
        "The mockup data in the dark theme.",
        LIVERPOOL,
        _at(6, 8),
        [(1, ["trash", "leaf"]), (6, ["recycle"])],
        theme="dark",
    ),
    Scenario(
        "eink-colours",
        "The mockup data with Colours set to Colour for e-ink: exact panel inks.",
        LIVERPOOL,
        _at(6, 8),
        [(1, ["trash", "leaf"]), (6, ["recycle"])],
        colours="eink",
    ),
    Scenario(
        "today",
        "Collection day, before the 10:00 cutoff.",
        LIVERPOOL,
        _at(7, 8),
        [(0, ["trash", "leaf"]), (5, ["recycle"])],
    ),
    Scenario(
        "after-cutoff",
        "Collection day after the cutoff: today's bins are done.",
        LIVERPOOL,
        _at(7, 11),
        [(5, ["recycle"])],
    ),
    Scenario(
        "colour-names",
        "Stockport-style colour titles with no mappings, so no icons.",
        [
            _stream("Black bin", "2026-10-07", 2),
            _stream("Green bin", "2026-10-07", 2),
            _stream("Blue bin", "2026-10-13", 2),
            _stream("Brown bin", "2026-10-13", 2),
        ],
        _at(6, 8),
        [(1, [None, None]), (7, [None, None])],
    ),
    Scenario(
        "busy-day",
        "Five bins on one day: SM shows only that day, its label above the bins.",
        [
            _stream(label, "2026-10-07", 1)
            for label in ("Refuse", "Recycling", "Garden waste", "Food waste", "Glass")
        ],
        _at(6, 8),
        [(1, ["trash", "recycle", "leaf", "fork-knife", "wine"])],
    ),
    Scenario(
        "busy-second-day",
        "A light day then a busy one: two SM rows, the busy row ending with +N.",
        [_stream("Refuse", "2026-10-07", 2)]
        + [
            _stream(label, "2026-10-12", 2)
            for label in ("Recycling", "Garden waste", "Food waste", "Glass", "Paper")
        ],
        _at(6, 8),
        [(1, ["trash"]), (6, ["recycle", "leaf", "fork-knife", "wine", "newspaper"])],
    ),
    Scenario(
        "overflow",
        "Fourteen bins on one day: SM fills its 12 slots, ending with +N.",
        [
            _stream(label, "2026-10-07", 1)
            for label in (
                "Refuse",
                "Recycling",
                "Garden waste",
                "Food waste",
                "Glass",
                "Paper",
                "Cardboard",
                "Batteries",
                "Textiles",
                "Small electricals",
                "Nappies",
                "Bulky items",
                "Clinical waste",
                "Plastics",
            )
        ],
        _at(6, 8),
        [
            (
                1,
                ["trash", "recycle", "leaf", "fork-knife", "wine", "newspaper", "newspaper"]
                + [None] * 7,
            )
        ],
    ),
    Scenario(
        "overflow-second-day",
        "A light day, then fourteen bins: SM's second row, MD's second column and "
        "LG's strip end with +N.",
        [_stream("Refuse", "2026-10-07", 2)]
        + [
            _stream(label, "2026-10-12", 2)
            for label in (
                "Recycling",
                "Garden waste",
                "Food waste",
                "Glass",
                "Paper",
                "Cardboard",
                "Batteries",
                "Textiles",
                "Small electricals",
                "Nappies",
                "Bulky items",
                "Clinical waste",
                "Plastics",
                "Coffee pods",
            )
        ],
        _at(6, 8),
        [
            (1, ["trash"]),
            (6, ["recycle", "leaf", "fork-knife", "wine", "newspaper", "newspaper"] + [None] * 8),
        ],
    ),
    Scenario(
        "black-and-white",
        "Colours set to Black & white: solid, white, hatched, dotted and cross-hatched.",
        [_stream(label, "2026-10-07", 1) for label in ("Refuse", "Recycling", "Garden waste")]
        + [_stream(label, "2026-10-12", 1) for label in ("Glass", "Brown bin", "Purple bin")],
        _at(6, 8),
        [(1, ["trash", "recycle", "leaf"]), (6, ["wine", None, None])],
        colours="mono",
    ),
    Scenario(
        "palette-dark",
        "Seven bin colours side by side (no icons), for checking the palette.",
        [
            _stream(f"{colour} bin", "2026-10-07", 1)
            for colour in (
                "Black",
                "Dark grey",
                "Grey",
                "Blue",
                "Green",
                "Brown",
                "Purple",
                "Maroon",
            )
        ],
        _at(6, 8),
        [(1, [None] * 8)],
    ),
    Scenario(
        "palette-light",
        "The other seven bin colours side by side (no icons).",
        [
            _stream(f"{colour} bin", "2026-10-07", 1)
            for colour in (
                "Burgundy",
                "Pink",
                "Red",
                "Orange",
                "Yellow",
                "Light blue",
                "Light grey",
                "White",
            )
        ],
        _at(6, 8),
        [(1, [None] * 8)],
    ),
    Scenario(
        "solid-bins",
        "Liverpool: each bin one colour, lid included. The chips match the bins.",
        [
            _stream("Refuse", "2026-10-07", 2, body_colour="purple"),
            _stream("Green", "2026-10-07", 2, icon="leaf"),
            _stream("Recycling", "2026-10-12", 2),
        ],
        _at(6, 8),
        [(1, ["trash", "leaf"]), (6, ["recycle"])],
        docs=True,
    ),
    Scenario(
        "lid-colours",
        "Milton Keynes-style: every bin dark grey, told apart by lid. Lid colours "
        "read from the names; the chips take the lid colour.",
        LID_CODED,
        _at(6, 8),
        [(1, ["trash", "recycle"]), (6, ["newspaper"])],
        docs=True,
    ),
    Scenario(
        "lid-colours-mono",
        "The lid-coloured bins in Black & white: each takes its lid colour's fill.",
        LID_CODED,
        _at(6, 8),
        [(1, ["trash", "recycle"]), (6, ["newspaper"])],
        colours="mono",
        docs=True,
    ),
    Scenario(
        "mixed-bins",
        "Salford-style: one-colour bins plus a pink-lidded one, all read from the names.",
        [
            _stream("Black rubbish bin", "2026-10-07", 2),
            _stream("Pink lid garden bin", "2026-10-07", 2),
            _stream("Brown glass bin", "2026-10-12", 2),
            _stream("Blue paper bin", "2026-10-12", 2),
        ],
        _at(6, 8),
        [(1, ["trash", "leaf"]), (6, ["wine", "newspaper"])],
        docs=True,
    ),
    Scenario(
        "set-by-hand",
        "Perth & Kinross: every bin green, named by its lid, so lid colours (and "
        "icons) are set in Bin Day Core.",
        [
            _stream("Green bin", "2026-10-07", 2, "trash"),
            _stream("Grey bin", "2026-10-07", 2, "recycle", "green", "grey"),
            _stream("Blue bin", "2026-10-12", 4, "newspaper", "green", "blue"),
            _stream("Brown bin", "2026-10-12", 2, "leaf", "green", "brown"),
        ],
        _at(6, 8),
        [(1, ["trash", "recycle"]), (6, ["leaf", "newspaper"])],
        docs=True,
    ),
    Scenario(
        "empty",
        "Nothing in the next 7 days.",
        [_stream("Refuse", "2026-12-01", 1)],
        _at(6, 8),
        [],
    ),
    Scenario(
        "error",
        "Core set to a Home Assistant calendar but none chosen: error tile.",
        [],
        _at(6, 8),
        "Choose your bin calendar",
        source="calendar",
    ),
]
