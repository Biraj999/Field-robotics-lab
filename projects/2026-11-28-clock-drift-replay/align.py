"""Align an aerial survey camera clock to a logger using shared trigger marks."""

import argparse
from itertools import combinations
import json
from math import isfinite, sqrt
from pathlib import Path
from statistics import median


def read_pairs(values, minimum):
    pairs = [(float(x), float(y)) for x, y in values]
    if len(pairs) < minimum or any(not isfinite(v) for pair in pairs for v in pair):
        raise ValueError(f"Expected at least {minimum} finite timestamp pairs.")
    return pairs


def fit(sync):
    """Return the robust slope and offset for logger = slope * camera + offset."""
    if len({camera for camera, _ in sync}) != len(sync):
        raise ValueError("Camera times must be unique in the sync marks.")
    slope = median((y2 - y1) / (x2 - x1)
                   for (x1, y1), (x2, y2) in combinations(sync, 2))
    if not isfinite(slope) or slope <= 0:
        raise ValueError("Estimated clock rate must be finite and positive.")
    offset = median(logger - slope * camera for camera, logger in sync)
    if not isfinite(offset):
        raise ValueError("Estimated clock offset must be finite.")
    return slope, offset


def rms(values):
    return sqrt(sum(value ** 2 for value in values) / len(values))


def draw_svg(pairs, offset_only, corrected, output):
    """Draw held-out residuals in milliseconds on the same vertical scale."""
    colors = ("#ec9b62", "#60d9b5")
    limit = max(1, *(abs(value) * 1000 for values in (offset_only, corrected) for value in values))
    start = min(x for x, _ in pairs)
    span = max(1, max(x for x, _ in pairs) - start)
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 690 350">',
        '<title>Held-out timestamp alignment errors</title>',
        '<rect width="690" height="350" rx="12" fill="#13272f"/>',
        '<g fill="#f3f5ed" font-family="sans-serif">',
        '<text x="30" y="39" font-size="24" font-weight="bold">Clock Drift Replay</text>',
        '<text x="30" y="65" font-size="13">Signed timestamp error on held-out triggers (ms)</text>',
    ]
    for level in (-limit, 0, limit):
        y = 180 - 82 * level / limit
        svg.append(f'<path d="M79 {y:.2f}H652" stroke="#43616c"/>')
        svg.append(f'<text x="70" y="{y+4:.2f}" text-anchor="end" font-size="12">{level:.1f}</text>')
    for index, (label, color, values) in enumerate(zip(
            ("Offset only", "Offset + drift"), colors, (offset_only, corrected))):
        points = [(95 + 540 * (time - start) / span, 180 - 82000 * error / limit)
                  for (time, _), error in zip(pairs, values)]
        coords = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
        svg.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="2"/>')
        for x, y in points:
            svg.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4" fill="{color}"/>')
        svg.append(f'<text x="{269 + 150 * index}" y="329" fill="{color}" font-size="13">{label}</text>')
    svg.append(f'<text x="95" y="284" text-anchor="middle" font-size="12">{start:g} s</text>')
    svg.append(f'<text x="{95+540*(max(x for x, _ in pairs)-start)/span:.2f}" y="284" text-anchor="middle" font-size="12">{max(x for x, _ in pairs):g} s</text>')
    svg.append('<text x="365" y="306" text-anchor="middle" font-size="12">Camera time</text>')
    svg.append('</g></svg>')
    output.write_text("\n".join(svg) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--svg", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.fixture.read_text(encoding="utf-8"))
        sync = read_pairs(data["camera_and_logger_sync_s"], minimum=3)
        pairs = sorted(read_pairs(data["held_out_pairs_s"], minimum=1))
        slope, offset = fit(sync)
        baseline = median(logger - camera for camera, logger in sync)
        offset_only = [camera + baseline - logger for camera, logger in pairs]
        corrected = [slope * camera + offset - logger for camera, logger in pairs]
        if args.svg:
            if args.svg.resolve() == args.fixture.resolve():
                raise ValueError("Choose a different path for the SVG output.")
            draw_svg(pairs, offset_only, corrected, args.svg)
        print(f"Estimated camera-to-logger drift: {(slope - 1) * 1e6:+.1f} ppm")
        print(f"Estimated offset: {offset:.4f} s")
        print(f"Offset-only held-out RMS: {rms(offset_only) * 1000:.3f} ms")
        print(f"Offset + drift held-out RMS: {rms(corrected) * 1000:.3f} ms")
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
