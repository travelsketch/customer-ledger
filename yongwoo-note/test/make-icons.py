"""용우노트 앱 아이콘 생성 (icon.svg 와 같은 도안으로 icon-192/512/512-maskable PNG).

도안: 파란 바탕 + 흰 노트 + 노란 형광펜/펜 — 갤럭시 홈 화면에서 한눈에 띄도록 고대비.
실행: python3 apps/yongwoo-note/test/make-icons.py
"""
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SS = 4                      # 512 좌표를 4배로 그린 뒤 줄입니다(안티에일리어싱)
S = 512 * SS

BLUE_TOP = (43, 107, 255)
BLUE_BOT = (18, 48, 155)
PAGE = (255, 255, 255)
LINE = (195, 211, 242)
YELLOW = (255, 210, 31)
YELLOW_D = (242, 169, 0)
YELLOW_L = (255, 236, 150)
INK = (26, 31, 43)


def T(v):
    return int(round(v * SS))


def gradient(size):
    g = Image.new("RGB", (96, 96))
    px = g.load()
    for y in range(96):
        for x in range(96):
            t = (x * 0.62 + y * 0.38) / 95.0
            px[x, y] = (
                int(BLUE_TOP[0] + (BLUE_BOT[0] - BLUE_TOP[0]) * t),
                int(BLUE_TOP[1] + (BLUE_BOT[1] - BLUE_TOP[1]) * t),
                int(BLUE_TOP[2] + (BLUE_BOT[2] - BLUE_TOP[2]) * t),
            )
    return g.resize(size, Image.BICUBIC)


def content_layer():
    """512 좌표 기준의 노트 + 펜 그림(투명 바탕)."""
    c = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)

    # 노트 그림자
    sh = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle(
        [T(96), T(94), T(352), T(444)], radius=T(30), fill=(8, 18, 48, 90)
    )
    sh = sh.filter(__import__("PIL.ImageFilter", fromlist=["ImageFilter"]).GaussianBlur(T(9)))
    c.alpha_composite(sh)

    # 흰 노트
    d.rounded_rectangle([T(96), T(80), T(344), T(432)], radius=T(28), fill=PAGE)

    # 제목 형광펜
    d.rounded_rectangle([T(126), T(116), T(292), T(150)], radius=T(17), fill=YELLOW)

    # 본문 줄
    for (x1, y1, x2) in [(126, 184, 314), (126, 222, 314), (126, 260, 258)]:
        d.rounded_rectangle([T(x1), T(y1), T(x2), T(y1 + 18)], radius=T(9), fill=LINE)

    # 체크리스트
    d.rounded_rectangle([T(124), T(306), T(162), T(344)], radius=T(10), fill=(29, 78, 216))
    d.line([T(133), T(325), T(141), T(334), T(153), T(315)], fill=(255, 255, 255), width=T(7), joint="curve")
    d.rounded_rectangle([T(174), T(316), T(292), T(334)], radius=T(9), fill=LINE)

    # 노란 펜 (따로 그려 회전)
    pen = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    pd = ImageDraw.Draw(pen)
    pd.rounded_rectangle([T(330), T(150), T(382), T(392)], radius=T(15), fill=YELLOW)
    pd.rounded_rectangle([T(330), T(150), T(382), T(198)], radius=T(15), fill=YELLOW_D)
    pd.polygon([(T(330), T(392)), (T(382), T(392)), (T(356), T(454))], fill=YELLOW_L)
    pd.polygon([(T(346), T(428)), (T(366), T(428)), (T(356), T(456))], fill=INK)
    pen = pen.rotate(-38, resample=Image.BICUBIC, center=(T(356), T(300)))
    c.alpha_composite(pen)
    return c


def build(maskable=False):
    base = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    bg = gradient((S, S)).convert("RGBA")
    mask = Image.new("L", (S, S), 0)
    md = ImageDraw.Draw(mask)
    if maskable:
        md.rectangle([0, 0, S, S], fill=255)
    else:
        md.rounded_rectangle([0, 0, S - 1, S - 1], radius=T(116), fill=255)
    base.paste(bg, (0, 0), mask)

    content = content_layer()
    if maskable:
        # 안전 영역(가운데 74%) 안에 들어오도록 줄입니다.
        small = content.resize((int(S * 0.74), int(S * 0.74)), Image.LANCZOS)
        off = (S - small.width) // 2
        base.alpha_composite(small, (off, off))
    else:
        base.alpha_composite(content)
    return base


def save(img, name, size):
    img.resize((size, size), Image.LANCZOS).save(ROOT / name, optimize=True)


icon = build(False)
save(icon, "icon-192.png", 192)
save(icon, "icon-512.png", 512)
maskable = build(True)
maskable.resize((512, 512), Image.LANCZOS).save(ROOT / "icon-512-maskable.png", optimize=True)

# 미리보기(홈 화면 느낌) — 검증용으로만 씁니다.
prev = Image.new("RGBA", (1080, 520), (238, 241, 247, 255))
prev.alpha_composite(icon.resize((256, 256), Image.LANCZOS), (80, 120))
prev.alpha_composite(maskable.resize((256, 256), Image.LANCZOS), (420, 120))
prev.save(ROOT / ".test-artifacts" if False else ROOT / "icon-preview.png", optimize=True)
print("icons written:", [p.name for p in ROOT.glob("icon*.png")])
