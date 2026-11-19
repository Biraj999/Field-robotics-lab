# Canopy Confidence

An offline UAV survey prototype that helps a grower decide which plots to inspect. It filters blurry observations, gives equally weighted votes to camera passes, and flags plots where those passes disagree.

![Synthetic survey results showing estimated green cover, accepted passes, and review status for six plots](assets/preview.svg)

## Run the demo

Run these commands from the project folder with Python 3.10 or newer.

```bash
python3 canopy.py sample.csv --svg assets/preview.svg
python3 -m unittest -v
```

The first command prints JSON and regenerates the image above. Each sample row represents an existing measurement of canopy cover and sharpness for one frame. Both measurements use a 0–100 scale. Plot and pass IDs may contain up to 16 letters, digits, periods, underscores, or hyphens, starting with a letter or digit.

## How plots are flagged

1. Keep frames with a sharpness score of at least 60, then find the median cover within each pass.
2. Find the median across accepted passes. Flag plots with fewer than two accepted passes as **More passes needed**.
3. Flag a spread greater than 20 percentage points between accepted pass medians as **Conflicting passes**.
4. Flag the remaining plots as **Low cover** below 40% and **Stable cover** at 40% or above.

Plot A2 has 30.5% estimated cover and agreement across passes. Plot B1 has a 43.5-point spread, so its estimate goes to review. Plot B3's frames were all below the sharpness threshold. Use `--min-sharpness`, `--max-spread`, and `--low-cover` to see how the thresholds change those decisions.

The demo uses synthetic frame measurements. Real surveys would need a calibrated image-to-cover estimator and field observations to choose thresholds for the crop and growth stage.

![Illustrative aerial view of vegetable plots with different canopy densities](assets/crop-plots.jpg)

*Concept image. The demo uses the measurements in `sample.csv`.*
