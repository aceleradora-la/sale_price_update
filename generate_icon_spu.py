"""
Ícono para sale_price_update — 512×512 y 128×128
Concepto: etiqueta de precio con % dorado + flecha ascendente.
"""
from PIL import Image, ImageDraw, ImageFont
import os, math

FONTS_DIR = (
    r"C:\Users\ignac\AppData\Roaming\Claude\local-agent-mode-sessions"
    r"\skills-plugin\60a6aebb-6628-4a15-84c5-26075654cd97"
    r"\ad541d52-46df-4e10-9062-c5ce49c0aacd\skills\canvas-design\canvas-fonts"
)
OUT_DIR = (
    r"C:\Users\ignac\dev\facundo\sale_price_update"
    r"\sale_price_update\static\description"
)

BLUE_BG    = (18,  72, 138)
BLUE_LIGHT = (30,  95, 165)
GOLD       = (245, 170,  30)
WHITE      = (255, 255, 255)
TAG_WHITE  = (240, 246, 255)
TAG_FOLD   = (190, 215, 240)


def font(name, size):
    try:
        return ImageFont.truetype(os.path.join(FONTS_DIR, name), size)
    except Exception:
        return ImageFont.load_default()


def make_icon(size: int) -> Image.Image:
    s = size
    img  = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Fondo redondeado con gradiente
    r = int(s * 0.175)
    for y in range(s):
        t = y / s
        col = tuple(int(BLUE_BG[i] + (BLUE_LIGHT[i] - BLUE_BG[i]) * t * 0.5)
                    for i in range(3)) + (255,)
        draw.line([(0, y), (s-1, y)], fill=col)

    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle([(0,0),(s-1,s-1)], radius=r, fill=255)
    img.putalpha(mask)
    draw = ImageDraw.Draw(img)

    # ── Etiqueta de precio (tag shape) ──────────────────────────────────────
    tw = int(s * 0.62)
    th = int(s * 0.44)
    tx0 = int(s * 0.12)
    ty0 = int(s * 0.16)
    notch = int(s * 0.09)   # muesca izquierda de la etiqueta

    # Sombra
    sh_offset = int(s * 0.025)
    shadow = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle(
        [(tx0 + notch + sh_offset, ty0 + sh_offset),
         (tx0 + tw + sh_offset, ty0 + th + sh_offset)],
        radius=int(s * 0.045), fill=(0, 0, 0, 40)
    )
    img = Image.alpha_composite(img, shadow)
    draw = ImageDraw.Draw(img)

    # Cuerpo de la etiqueta (rectángulo con esquina izquierda en punta)
    pts = [
        (tx0,               ty0 + th // 2),          # punta izquierda
        (tx0 + notch,       ty0),                     # esquina sup-izq
        (tx0 + tw,          ty0),                     # esquina sup-der
        (tx0 + tw,          ty0 + th),                # esquina inf-der
        (tx0 + notch,       ty0 + th),                # esquina inf-izq
    ]
    draw.polygon(pts, fill=TAG_WHITE)

    # Ojete de la etiqueta
    hole_r = int(s * 0.032)
    hole_x = tx0 + notch + int(s * 0.06)
    hole_y = ty0 + th // 2
    draw.ellipse(
        [(hole_x - hole_r, hole_y - hole_r),
         (hole_x + hole_r, hole_y + hole_r)],
        fill=BLUE_BG
    )

    # Líneas de contenido en la etiqueta
    lc = (100, 145, 195, 150)
    lx1 = hole_x + hole_r + int(s * 0.04)
    lx2 = tx0 + tw - int(s * 0.06)
    lh  = max(2, int(s * 0.02))
    for frac_y, wp in [(0.30, 0.75), (0.50, 0.55)]:
        ly = int(ty0 + th * frac_y)
        draw.rounded_rectangle(
            [(lx1, ly), (lx1 + int((lx2 - lx1) * wp), ly + lh)],
            radius=lh // 2, fill=lc
        )

    # ── % DORADO sobre la etiqueta ───────────────────────────────────────────
    pct_size = int(s * 0.28)
    ef = font("BricolageGrotesque-Bold.ttf", pct_size)
    ebox = draw.textbbox((0, 0), "%", font=ef)
    ew = ebox[2] - ebox[0]
    eh = ebox[3] - ebox[1]
    # Centrado en el área derecha de la etiqueta
    ex = tx0 + notch + (tw - notch) // 2 - ew // 2 + int(s * 0.02)
    ey = ty0 + th // 2 - eh // 2 - int(s * 0.01)

    # sombra del símbolo
    draw.text((ex + int(s*0.008), ey + int(s*0.008)), "%",
              font=ef, fill=(180, 120, 0, 100))
    draw.text((ex, ey), "%", font=ef, fill=GOLD)

    # ── Flecha ascendente (abajo del tag) ────────────────────────────────────
    arrow_cx = int(s * 0.68)
    arrow_by = int(s * 0.87)   # base
    arrow_ty = int(s * 0.63)   # tope
    aw  = int(s * 0.13)        # ancho cabeza
    asw = max(2, int(s * 0.05))  # grosor shaft

    # shaft
    draw.rounded_rectangle(
        [(arrow_cx - asw//2, arrow_ty + aw//2),
         (arrow_cx + asw//2, arrow_by)],
        radius=asw//2, fill=GOLD
    )
    # cabeza triangular (arriba)
    draw.polygon([
        (arrow_cx - aw//2, arrow_ty + aw//2),
        (arrow_cx,         arrow_ty),
        (arrow_cx + aw//2, arrow_ty + aw//2),
    ], fill=GOLD)

    # ── Badge "+" en esquina inferior izquierda de la flecha ─────────────────
    badge_r = int(s * 0.10)
    bx = int(s * 0.28)
    by_b = int(s * 0.81)

    bd = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(bd).ellipse(
        [(bx - badge_r, by_b - badge_r),
         (bx + badge_r, by_b + badge_r)],
        fill=(*GOLD, 255)
    )
    img = Image.alpha_composite(img, bd)
    draw = ImageDraw.Draw(img)

    pf   = font("BricolageGrotesque-Bold.ttf", int(s * 0.13))
    pbox = draw.textbbox((0, 0), "+", font=pf)
    pw   = pbox[2] - pbox[0]
    ph   = pbox[3] - pbox[1]
    draw.text((bx - pw//2, by_b - ph//2 - int(s*0.005)), "+",
              font=pf, fill=BLUE_BG)

    return img


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    for sz, name in [(512, "icon_512.png"), (128, "icon.png")]:
        path = os.path.join(OUT_DIR, name)
        make_icon(sz).save(path, "PNG")
        print(f"✓ {path}")
