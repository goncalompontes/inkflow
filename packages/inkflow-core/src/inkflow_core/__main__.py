"""Command-line entry point: python -m inkflow_core."""
import argparse
import json
from pathlib import Path

from .pipeline import analyze, load_image
from .report import save_report


def main(argv=None):
    parser = argparse.ArgumentParser(prog="inkflow", description="Analyze ink geometry and generate an interactive visual debug report.")
    parser.add_argument("image", type=Path, help="PNG/JPEG/TIFF input scan")
    parser.add_argument("--out", type=Path, default=Path("runs/latest"), help="Output report directory")
    parser.add_argument("--threshold", type=int, default=None, help="Override global Otsu threshold (0..255)")
    parser.add_argument("--min-area", type=int, default=3, help="Minimum retained ink component pixel area")
    parser.add_argument("--max-side", type=int, default=1000, help="Downscale longest image side; 0 keeps resolution")
    parser.add_argument("--invert", action="store_true", help="Treat light-on-dark marks as ink")
    args = parser.parse_args(argv)
    if not args.image.is_file():
        parser.error(f"Input file does not exist: {args.image}")
    if args.min_area < 1 or args.max_side < 0:
        parser.error("--min-area must be >= 1 and --max-side must be >= 0")
    try:
        source, gray = load_image(args.image, args.max_side)
        result = analyze(source, gray, threshold=args.threshold, minimum_area=args.min_area, invert=args.invert)
        viewer = save_report(result, args.out, input_path=str(args.image),
                             options={"threshold": args.threshold, "min_area": args.min_area,
                                      "max_side": args.max_side, "invert": args.invert})
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps({"viewer": str(viewer.resolve()), "diagnostics": result.diagnostics}, indent=2))


if __name__ == "__main__":
    main()
