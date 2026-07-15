"""
Banner 1380x320px para apps.odoo.com — sale_price_update
Zona segura: x=200 a x=1180
"""
from PIL import Image, ImageDraw, ImageFont
import os

FONTS_DIR = (
    r"C:\Users\ignac\AppData\Roaming\Claude\local-agent-mode-sessions"
    r"\skills-plugin\60a6aebb-6628-4a15-84c5-26075654cd97"
    r"\ad541d52-46df-4e10-9062-c5ce49c0aacd\skills\canvas-design\canvas-fonts"
)
OUT_DIR = (
    r"C:\Users\ignac\dev\facundo\sale_price_update"
    r"\sale_price_update\static\description"
)
ICON_PATH = os.path.join(OUT_DIR, "icon_512.png")

W, H = 1380, 320

BG_DARK    = (13,  55, 110)
BG_MID     = (18,  72, 138)
BG_LIGHT   = (28,  95, 165)
GOLD       = (245, 170,  30)
WHITE      = (255, 255, 255)


def f(name, size):
    try:
        return ImageFont.truetype(os.path.join(FONTS_DIR, name), size)
    except Exception:
        return ImageFont.load_default()


def make_banner() -> Image.Image:
    img  = Image.new("RGB", (W, H), BG_DARK)
    draw = ImageDraw.Draw(img)

    # Gradiente horizontal
    for x in range(W):
        t = x / W
        r = int(BG_DARK[0] + (BG_MID[0]   - BG_DARK[0]) * t)
        g = int(BG_DARK[1] + (BG_MID[1]   - BG_DARK[1]) * t * 0.8)
        b = int(BG_DARK[2] + (BG_LIGHT[2] - BG_DARK[2]) * t * 0.4)
        draw.line([(x, 0), (x, H-1)], fill=(r, g, b))

    # Overlay decorativo
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for i in range(-H, W + H, 48):
        od.line([(i, 0), (i + H, H)], fill=(255, 255, 255, 7), width=1)
    for rad, alpha in [(280, 15), (210, 20), (140, 26)]:
        od.ellipse([(W//2 + 320 - rad, H//2 - rad),
                    (W//2 + 320 + rad, H//2 + rad)],
                   outline=(255, 255, 255, alpha), width=2)

    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Franjas doradas
    draw.rectangle([(0, 0), (W, 5)],   fill=GOLD)
    draw.rectangle([(0, H-5), (W, H)], fill=GOLD)

    SAFE_X = 220
    SAFE_W = 940

    # Ícono
    icon_size = 190
    icon_x    = SAFE_X
    icon_y    = (H - icon_size) // 2

    if os.path.exists(ICON_PATH):
        icon = Image.open(ICON_PATH).convert("RGBA").resize(
            (icon_size, icon_size), Image.LANCZOS
        )
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle(
            [(icon_x+8, icon_y+8), (icon_x+icon_size+8, icon_y+icon_size+8)],
            radius=int(icon_size*0.18), fill=(0, 0, 0, 55)
        )
        img.paste(sh, (0, 0), sh)
        img.paste(icon, (icon_x, icon_y), icon)
        draw = ImageDraw.Draw(img)

    # Separador dorado
    sep_x = SAFE_X + icon_size + 34
    draw.rectangle([(sep_x, 32), (sep_x + 3, H - 32)], fill=(*GOLD, 200))

    tx = sep_x + 26

    # Tagline
    draw.text((tx, 38), "ODOO 17 · 18 · 19  ·  ACELERADORA LA",
              font=f("BricolageGrotesque-Regular.ttf", 15), fill=GOLD)

    # Título
    draw.text((tx, 60), "Sale Price",
              font=f("BricolageGrotesque-Bold.ttf", 50), fill=WHITE)
    draw.text((tx, 114), "Update",
              font=f("BricolageGrotesque-Bold.ttf", 50), fill=WHITE)

    # Subtítulo
    draw.text((tx, 174), "Bulk Price Update Assistant",
              font=f("BricolageGrotesque-Regular.ttf", 22),
              fill=(185, 215, 250))

    # Línea dorada
    draw.rectangle([(tx, 202), (tx + 280, 205)], fill=GOLD)

    # Features
    feat_f = f("BricolageGrotesque-Regular.ttf", 16)
    bold_f = f("BricolageGrotesque-Bold.ttf",    16)
    features = [
        ("%", "Actualización por % de aumento"),
        ("≡", "Filtro por categoría con árbol"),
        ("⟳", "Historial completo de cambios"),
    ]
    fy = 215
    for sym, txt in features:
        draw.text((tx,      fy), sym, font=bold_f, fill=GOLD)
        draw.text((tx + 22, fy), txt, font=feat_f, fill=(205, 225, 255))
        fy += 26

    draw.text((tx, H - 28), "aceleradora.la",
              font=f("BricolageGrotesque-Regular.ttf", 13),
              fill=(110, 155, 210))

    # Panel preview (derecha)
    px = SAFE_X + SAFE_W - 225
    py = 28
    pw = 230
    ph = H - 56

    gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(gl).rounded_rectangle(
        [(px, py), (px+pw, py+ph)], radius=16,
        fill=(255, 255, 255, 20), outline=(255, 255, 255, 45)
    )
    img = Image.alpha_composite(img.convert("RGBA"), gl).convert("RGB")
    draw = ImageDraw.Draw(img)

    lbl  = f("BricolageGrotesque-Regular.ttf", 12)
    num  = f("BricolageGrotesque-Bold.ttf",    22)
    mx   = px + 18

    # Fila 1: precio actual
    draw.text((mx, py+16), "Precio actual", font=lbl, fill=(160, 200, 245))
    draw.text((mx, py+30), "$ 4.200,00",   font=num, fill=(180, 200, 220))

    # Fila 2: % aumento
    draw.text((mx, py+66), "% Aumento", font=lbl, fill=(160, 200, 245))
    draw.text((mx, py+80), "+ 15,00 %",  font=num, fill=GOLD)

    draw.rectangle([(mx, py+114), (mx+pw-36, py+116)], fill=(255, 255, 255, 40))

    # Fila 3: precio nuevo
    draw.text((mx, py+122), "Precio nuevo",  font=lbl, fill=(160, 200, 245))
    draw.text((mx, py+136), "$ 4.830,00", font=num, fill=WHITE)

    # Badge "Vigente desde"
    bx, by2, bw2, bh2 = mx, py+176, pw-36, 32
    bd = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(bd).rounded_rectangle(
        [(bx, by2), (bx+bw2, by2+bh2)], radius=7, fill=(*GOLD, 255)
    )
    img = Image.alpha_composite(img.convert("RGBA"), bd).convert("RGB")
    draw = ImageDraw.Draw(img)

    badge_txt = "Vigente desde hoy"
    bf   = f("BricolageGrotesque-Bold.ttf", 15)
    bb   = draw.textbbox((0,0), badge_txt, font=bf)
    bltw = bb[2]-bb[0]
    draw.text((bx + bw2//2 - bltw//2, by2 + 8), badge_txt,
              font=bf, fill=BG_DARK)

    return img.convert("RGB")


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, "banner.png")
    make_banner().save(path, "PNG")
    print(f"Saved: {path}  ({W}x{H}px)  —  zona segura: x=220 a x=1160")
