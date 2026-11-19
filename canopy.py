"""Triage crop plots from quality-scored UAV survey observations."""

import argparse
import csv
from collections import defaultdict
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
from statistics import median
from xml.sax.saxutils import escape


@dataclass(frozen=True)
class Observation:
    plot: str
    pass_id: str
    green_cover: int
    sharpness: int


@dataclass(frozen=True)
class PlotResult:
    plot: str
    status: str
    cover: float | None
    spread: float | None
    accepted_passes: int
    accepted_frames: int


def percentage(value: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("expected a whole number from 0 to 100") from exc
    if not 0 <= number <= 100:
        raise ValueError("expected a whole number from 0 to 100")
    return number


def read_observations(path: Path) -> list[Observation]:
    columns = {"plot", "pass_id", "green_cover", "sharpness"}
    identifier = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,15}")
    observations = []
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, strict=True)
        if reader.fieldnames is None or not columns.issubset(reader.fieldnames):
            raise ValueError(f"CSV requires these columns: {', '.join(sorted(columns))}")
        if len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError("CSV column names must be unique")
        for row in reader:
            plot = (row["plot"] or "").strip()
            pass_id = (row["pass_id"] or "").strip()
            if not identifier.fullmatch(plot) or not identifier.fullmatch(pass_id):
                raise ValueError(f"CSV line {reader.line_num}: invalid plot or pass ID")
            try:
                cover = percentage(row["green_cover"])
                sharpness = percentage(row["sharpness"])
            except ValueError as exc:
                raise ValueError(f"CSV line {reader.line_num}: {exc}") from exc
            observations.append(Observation(plot, pass_id, cover, sharpness))
    if not observations:
        raise ValueError("CSV must contain at least one observation")
    return observations


STATUS_STYLES = {
    "Low cover": "#AD451F",
    "Conflicting passes": "#8B4B83",
    "More passes needed": "#526681",
    "Stable cover": "#14725C",
}


def triage(
    observations: list[Observation],
    min_sharpness: int = 60,
    low_cover: int = 40,
    max_spread: int = 20,
) -> list[PlotResult]:
    by_plot: dict[str, dict[str, list[int]]] = {}
    for observation in observations:
        passes = by_plot.setdefault(observation.plot, defaultdict(list))
        if observation.sharpness >= min_sharpness:
            passes[observation.pass_id].append(observation.green_cover)

    results = []
    for plot, passes in by_plot.items():
        pass_medians = [median(frames) for frames in passes.values()]
        cover = median(pass_medians) if pass_medians else None
        spread = max(pass_medians) - min(pass_medians) if len(pass_medians) >= 2 else None

        if spread is None:
            status = "More passes needed"
        elif spread > max_spread:
            status = "Conflicting passes"
        elif cover < low_cover:
            status = "Low cover"
        else:
            status = "Stable cover"

        results.append(PlotResult(plot, status, cover, spread, len(passes),
                                  sum(map(len, passes.values()))))

    priority = {status: index for index, status in enumerate(STATUS_STYLES)}
    return sorted(results, key=lambda result: (priority[result.status], result.plot))


def render_svg(results: list[PlotResult], low_cover: int) -> str:
    width = 880
    chart_x = 195
    chart_width = 330
    height = 162 + 42 * len(results)
    threshold_x = chart_x + chart_width * low_cover / 100
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img">',
        '<title>Canopy Confidence plot review</title>',
        '<desc>Estimated crop canopy cover by plot with accepted pass count and review status.</desc>',
        f'<rect width="{width}" height="{height}" rx="20" fill="#F1F6F1"/>',
        '<rect width="880" height="80" rx="20" fill="#12392F"/>',
        '<path d="M0 55h880v25H0z" fill="#12392F"/>',
        '<g font-family="system-ui, sans-serif" fill="#12392F">',
        '<text x="26" y="35" fill="#FFFFFF" font-size="25" font-weight="700">Canopy Confidence</text>',
        f'<text x="26" y="60" fill="#C0E3CF" font-size="14">UAV survey review · Low-cover threshold {low_cover}%</text>',
        '<g fill="#36534B" font-size="13" font-weight="700">',
        '<text x="26" y="109">Plot</text><text x="195" y="109">Estimated green cover</text>',
        '<text x="585" y="109">Passes</text><text x="668" y="109">Review status</text>',
        '</g>',
    ]
    for index, result in enumerate(results):
        y = 119 + 42 * index
        mid = y + 21
        color = STATUS_STYLES[result.status]
        fill = "#FFFFFF" if index % 2 == 0 else "#E7EFE8"
        elements.extend([
            f'<rect x="14" y="{y}" width="852" height="38" rx="7" fill="{fill}"/>',
            f'<text x="26" y="{mid + 5}" font-size="14">{escape(result.plot)}</text>',
            f'<rect x="{chart_x}" y="{mid - 6}" width="{chart_width}" height="12" rx="6" fill="#DCE6DF"/>',
        ])
        if result.cover is None:
            label = "—"
        else:
            bar_width = chart_width * result.cover / 100
            label = f"{result.cover:g}%"
            elements.append(f'<rect x="{chart_x}" y="{mid - 6}" width="{bar_width:g}" height="12" rx="6" fill="{color}"/>')
        elements.extend([
            f'<path d="M{threshold_x:g} {mid - 8}v16" stroke="#12392F" stroke-width="1.5"/>',
            f'<text x="535" y="{mid + 5}" font-size="13">{label}</text>',
            f'<text x="603" y="{mid + 5}" text-anchor="middle" font-size="14">{result.accepted_passes}</text>',
            f'<text x="668" y="{mid + 5}" fill="{color}" font-size="14" font-weight="600">{result.status}</text>',
        ])
    elements.extend([
        f'<text x="26" y="{height - 16}" fill="#36534B" font-size="12">The tick mark shows the low-cover threshold. Single-pass estimates are provisional.</text>',
        '</g></svg>',
    ])
    return "\n".join(elements) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("observations", type=Path, help="input CSV file")
    parser.add_argument("--min-sharpness", type=percentage, default=60)
    parser.add_argument("--low-cover", type=percentage, default=40)
    parser.add_argument("--max-spread", type=percentage, default=20)
    parser.add_argument("--svg", type=Path, help="write a plot review image to this path")
    args = parser.parse_args()

    try:
        observations = read_observations(args.observations)
        results = triage(observations, args.min_sharpness, args.low_cover, args.max_spread)
        if args.svg is not None:
            if args.svg.resolve() == args.observations.resolve():
                raise ValueError("choose an output path separate from the input CSV")
            args.svg.write_text(render_svg(results, args.low_cover), encoding="utf-8")
    except (ValueError, OSError, csv.Error) as exc:
        parser.error(str(exc))
    print(json.dumps([asdict(result) for result in results], indent=2))


if __name__ == "__main__":
    main()
