"""Screenshot scenarios. Each has its own Bin Day Core config (one schedule
plus any title mappings), a pinned clock, and the cell options to render.

``expect`` is what the cell should show, checked by
tests/test_preview_scenarios.py: ``[(days_until, [icon, ...]), ...]`` for
each collection day, or ``"error"``.
"""

from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo

LONDON = ZoneInfo("Europe/London")
SCHEDULE_ID = "home"


def _stream(label, first_date, every_weeks):
    return {
        "label": label,
        "first_date": first_date,
        "every_weeks": every_weeks,
        "icon": "",
        "body_colour": "",
        "lid_colour": "",
    }


def _at(day, hour, minute=0):
    return datetime(2026, 10, day, hour, minute, tzinfo=LONDON)


# Liverpool's WCS titles; the owner maps the bare "Green" to the garden leaf.
LIVERPOOL = [
    _stream("Refuse", "2026-10-07", 2),
    _stream("Green", "2026-10-07", 2),
    _stream("Recycling", "2026-10-12", 2),
]
LIVERPOOL_MAPPINGS = [
    {"match": "Green", "label": "", "icon": "leaf", "body_colour": "", "lid_colour": ""}
]


@dataclass(frozen=True)
class Scenario:
    name: str
    description: str
    streams: list
    now: datetime
    expect: object
    mappings: list = field(default_factory=list)
    cutoff: str = "10:00"
    colours: str = "auto"
    schedule_deleted: bool = False

    @property
    def config(self):
        schedule = {"id": SCHEDULE_ID, "name": self.name, "streams": self.streams}
        return {"mappings": self.mappings, "schedules": [schedule]}

    @property
    def options(self):
        schedule_id = "deleted" if self.schedule_deleted else SCHEDULE_ID
        return {"source": f"schedule:{schedule_id}", "cutoff": self.cutoff, "colours": self.colours}


SCENARIOS = [
    Scenario(
        "next-week",
        "The mockup data: Refuse and Green tomorrow, Recycling in 6 days.",
        LIVERPOOL,
        _at(6, 8),
        [(1, ["trash", "leaf"]), (6, ["recycle"])],
        mappings=LIVERPOOL_MAPPINGS,
    ),
    Scenario(
        "today",
        "Collection day, before the 10:00 cutoff.",
        LIVERPOOL,
        _at(7, 8),
        [(0, ["trash", "leaf"]), (5, ["recycle"])],
        mappings=LIVERPOOL_MAPPINGS,
    ),
    Scenario(
        "after-cutoff",
        "Collection day after the cutoff: today's bins are done.",
        LIVERPOOL,
        _at(7, 11),
        [(5, ["recycle"])],
        mappings=LIVERPOOL_MAPPINGS,
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
        "empty",
        "Nothing in the next 7 days.",
        [_stream("Refuse", "2026-12-01", 1)],
        _at(6, 8),
        [],
    ),
    Scenario(
        "error",
        "The cell's schedule was deleted: error tile.",
        LIVERPOOL,
        _at(6, 8),
        "error",
        schedule_deleted=True,
    ),
]
