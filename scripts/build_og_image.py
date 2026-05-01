"""One-shot Pillow renderer for assets/og-image.png and assets/apple-touch-icon.png.

Run manually whenever the wordmark / tagline changes:
    uv run python scripts/build_og_image.py

Outputs are committed to git; build_site.py just copies them.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parent.parent
ASSETS = REPO / "assets"

BG = (13, 17, 23)          # --bg-main
ACCENT = (0, 255, 157)     # --accent-green
TEXT = (230, 237, 243)     # --text-primary
MUTED = (139, 148, 158)    # --text-muted


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Try common system mono fonts, fall back to PIL default."""
    candidates = [
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/SFMono-Regular.otf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
            if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ]
    for c in candidates:
        if Path(c).exists():
            return ImageFont.truetype(c, size)
    return ImageFont.load_default()


def render_og() -> None:
    W, H = 1200, 630
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    # accent bar at top
    d.rectangle((0, 0, W, 8), fill=ACCENT)
    # wordmark
    d.text((80, 140), "CONDOR14", font=_font(64, bold=True), fill=ACCENT)
    # title
    d.text((80, 240), "Daily Iron Condor", font=_font(80, bold=True), fill=TEXT)
    d.text((80, 340), "Volatility Screener", font=_font(80, bold=True), fill=TEXT)
    # tagline
    d.text((80, 470), "Real OPRA quotes  ·  Held to expiration  ·  Open source",
           font=_font(28), fill=MUTED)
    # footer
    d.text((80, 540), "iron-condor-tracker.vercel.app",
           font=_font(24), fill=MUTED)
    out = ASSETS / "og-image.png"
    out.parent.mkdir(exist_ok=True)
    img.save(out, "PNG", optimize=True)
    print(f"wrote {out}")


def render_touch_icon() -> None:
    S = 180
    img = Image.new("RGB", (S, S), BG)
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, S, S), fill=BG)
    # rounded-square illusion via inner border
    d.rectangle((6, 6, S - 6, S - 6), outline=ACCENT, width=2)
    d.text((S // 2, S // 2), "C14", font=_font(64, bold=True),
           fill=ACCENT, anchor="mm")
    out = ASSETS / "apple-touch-icon.png"
    img.save(out, "PNG", optimize=True)
    print(f"wrote {out}")


if __name__ == "__main__":
    render_og()
    render_touch_icon()
