"""Generate a reproducible synthetic pen trace fixture with known paths."""
from pathlib import Path
from PIL import Image, ImageDraw

STROKES = [
    [(30, 95), (60, 35), (90, 95)],  # A-shaped trace, crossing later
    [(45, 69), (75, 69)],
    [(132, 95), (132, 35), (165, 35), (173, 43), (165, 62), (132, 62)],
    [(198, 90), (215, 43), (237, 90), (224, 63), (208, 63)]
]


def main():
    base = Image.new("RGB", (280, 130), "#fffdf7")
    draw = ImageDraw.Draw(base)
    for stroke in STROKES:
        draw.line(stroke, fill="#17253c", width=7, joint="curve")
    output = Path(__file__).with_name("synthetic-sample.png")
    base.save(output)
    print(output)


if __name__ == "__main__":
    main()
