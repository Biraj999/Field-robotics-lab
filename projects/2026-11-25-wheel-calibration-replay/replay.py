"""Fit differential-drive odometry and replay a held-out encoder log."""

import argparse
from dataclasses import dataclass
import json
import math
from pathlib import Path
from statistics import median


@dataclass(frozen=True)
class Drive:
    left_m_per_tick: float
    right_m_per_tick: float
    track_m: float

    def __post_init__(self):
        if any(not math.isfinite(value) or value <= 0 for value in
               (self.left_m_per_tick, self.right_m_per_tick, self.track_m)):
            raise ValueError("Drive parameters must be finite and positive.")


def calibrate(straight, turns):
    left = median(distance / lt for distance, lt, _ in straight)
    right = median(distance / rt for distance, _, rt in straight)
    track = median((rt * right - lt * left) / math.radians(degrees)
                   for degrees, lt, rt in turns)
    return Drive(left, right, track)


def replay(log, drive):
    x = y = heading = 0.0
    points = [(x, y)]
    for left_ticks, right_ticks in log:
        left = left_ticks * drive.left_m_per_tick
        right = right_ticks * drive.right_m_per_tick
        delta = (right - left) / drive.track_m
        half = delta / 2
        chord = (right + left) / 2
        if half:
            chord *= math.sin(half) / half
        x += chord * math.cos(heading + half)
        y += chord * math.sin(heading + half)
        heading += delta
        points.append((x, y))
    return points


def rms_error(points, reference):
    return math.sqrt(sum(math.dist(p, q) ** 2
                         for p, q in zip(points, reference, strict=True)) / len(points))


def draw(paths, output):
    points = [point for _, _, route in paths for point in route]
    x_min = min(x for x, _ in points)
    y_min = min(y for _, y in points)
    span_x = max(x for x, _ in points) - x_min
    span_y = max(y for _, y in points) - y_min
    scale = min(590 / max(span_x, 0.01), 325 / max(span_y, 0.01))
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 510">',
        '<title>Held-out differential-drive trajectories</title>',
        '<rect width="760" height="510" rx="20" fill="#102629"/>',
        '<g font-family="sans-serif" fill="#eef5ed">',
        '<text x="32" y="42" font-size="26" font-weight="bold">Wheel Calibration Replay</text>',
        '<text x="32" y="67" font-size="14">Held-out rectangular route · equal scale on both axes</text>',
        '<rect x="32" y="82" width="696" height="380" rx="10" fill="#193438"/>',
    ]
    for index, (label, color, route) in enumerate(paths):
        coords = " ".join(f"{71+(x-x_min)*scale:.2f},{438-(y-y_min)*scale:.2f}"
                          for x, y in route)
        dash = ' stroke-dasharray="9 5"' if label == "Reference" else ""
        svg.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="3"{dash}/>')
        line_x = 40 + 230 * index
        svg.append(f'<circle cx="{line_x}" cy="485" r="4" fill="{color}"/>')
        svg.append(f'<text x="{line_x+12}" y="490" font-size="14">{label}</text>')
    svg.append('</g></svg>')
    output.write_text("\n".join(svg) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--svg", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.fixture.read_text(encoding="utf-8"))
        reference = data["reference_xy"]
        nominal = replay(data["replay"], Drive(*data["nominal"]))
        drive = calibrate(data["straight"], data["turn"])
        calibrated = replay(data["replay"], drive)
        print(f"Calibrated scales: {drive.left_m_per_tick:.8f}, "
              f"{drive.right_m_per_tick:.8f} m/tick")
        print(f"Calibrated track: {drive.track_m:.4f} m")
        print(f"Nominal pose-position RMS: {rms_error(nominal, reference):.4f} m")
        print(f"Calibrated pose-position RMS: {rms_error(calibrated, reference):.4f} m")
        if args.svg:
            if args.svg.resolve() == args.fixture.resolve():
                raise ValueError("Choose an SVG path separate from the input fixture.")
            draw([("Nominal", "#ffa071", nominal), ("Calibrated", "#62dcaf", calibrated),
                  ("Reference", "#e3edf0", reference)], args.svg)
    except (OSError, ValueError, TypeError, KeyError, ZeroDivisionError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
