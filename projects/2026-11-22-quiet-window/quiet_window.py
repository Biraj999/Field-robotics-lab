"""Group maintenance reminders into the fewest on-time dispatches."""

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape


@dataclass(frozen=True)
class Reminder:
    name: str
    ready: int
    due: int


def read_reminders(path):
    with path.open(newline="", encoding="utf-8") as stream:
        rows = csv.DictReader(stream)
        if rows.fieldnames != ["id", "ready", "due"]:
            raise ValueError("Expected id,ready,due CSV columns.")
        reminders = [Reminder(row["id"].strip(), int(row["ready"]), int(row["due"]))
                     for row in rows]
    names = {reminder.name for reminder in reminders}
    if not reminders or len(names) != len(reminders) or "" in names:
        raise ValueError("Supply at least one reminder and use unique, nonempty IDs.")
    if any(not 0 <= item.ready <= item.due for item in reminders):
        raise ValueError("Each window must satisfy 0 <= ready <= due.")
    return reminders


def plan(reminders):
    """Return pairs of dispatch minute and reminders, ordered by dispatch."""
    batches = []
    for item in sorted(reminders, key=lambda item: (item.due, item.name)):
        # The latest dispatch is all that matters because due times only increase.
        if not batches or batches[-1][0] < item.ready:
            batches.append((item.due, []))
        batches[-1][1].append(item)
    return batches


def draw(batches, output):
    assignments = [(item, minute) for minute, group in batches for item in group]
    last = max(1, max(item.due for item, _ in assignments))
    height = 116 + 32 * len(assignments)

    def x(minute):
        return 180 + 550 * minute / last

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 780 {height}">',
        '<title>Quiet Window dispatch timeline</title>',
        f'<rect width="780" height="{height}" rx="16" fill="#eaf3f4"/>',
        '<g font-family="sans-serif" fill="#0e3440">',
        '<text x="26" y="36" font-size="25" font-weight="bold">Quiet Window</text>',
        f'<text x="26" y="63" font-size="14">{len(batches)} dispatches for {len(assignments)} reminders</text>',
        '<text x="180" y="87" font-size="12">Bars show allowed windows. Dots show dispatches.</text>',
    ]
    for count, (item, minute) in enumerate(assignments):
        y = 110 + 32 * count
        svg.extend([
            f'<text x="26" y="{y+5}" font-size="14">{escape(item.name[:19])}</text>',
            f'<line x1="{x(item.ready):.2f}" x2="{x(item.due):.2f}" y1="{y}" y2="{y}" stroke="#5c8e9c" stroke-width="7" stroke-linecap="round"/>',
            f'<circle cx="{x(minute):.2f}" cy="{y}" r="6" fill="#9e4020"/>',
        ])
    svg.extend([
        f'<text x="180" y="{height-12}" font-size="12">0 min</text>',
        f'<text x="730" y="{height-12}" text-anchor="end" font-size="12">{last} min</text>',
        '</g></svg>',
    ])
    output.write_text("\n".join(svg) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--svg", type=Path)
    args = parser.parse_args()
    try:
        batches = plan(read_reminders(args.input))
        if args.svg:
            if args.svg.resolve() == args.input.resolve():
                raise ValueError("The SVG requires a separate output path.")
            draw(batches, args.svg)
    except (OSError, TypeError, ValueError, csv.Error) as error:
        parser.error(str(error))
    for minute, group in batches:
        print(f"{minute:>3} min  " + ", ".join(item.name for item in group))
    print(f"{sum(len(group) for _, group in batches)} reminders in {len(batches)} dispatches")


if __name__ == "__main__":
    main()
