"""从几何图形生成应用图标，无外部图片、字体或网络依赖。"""
from pathlib import Path
from PIL import Image, ImageDraw


def make_icon(kind, color):
    image = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    d = ImageDraw.Draw(image)
    d.rounded_rectangle((4, 4, 252, 252), radius=62, fill=color)
    ink = "white"
    if kind == "farmland_context":
        d.polygon([(49, 133), (127, 91), (208, 133), (128, 175)], fill=ink)
        d.line([(50, 163), (128, 205), (207, 163)], fill=ink, width=12, joint="curve")
        d.line([(128, 116), (128, 66)], fill=ink, width=11)
        d.ellipse((82, 46, 128, 83), fill=ink)
        d.ellipse((128, 32, 174, 70), fill=ink)
    elif kind == "split_by_size":
        for a, b in [((49, 57, 113, 119), (143, 57, 207, 119)), ((49, 145, 113, 207), (143, 145, 207, 207))]:
            for box in (a, b):
                d.rounded_rectangle(box, radius=10, outline=ink, width=9)
    elif kind == "shp_to_kml":
        d.rounded_rectangle((48, 46, 127, 165), radius=9, outline=ink, width=10)
        d.line([(75, 80), (104, 80)], fill=ink, width=8)
        d.line([(75, 104), (104, 104)], fill=ink, width=8)
        d.line([(143, 150), (209, 150)], fill=ink, width=12)
        d.line([(182, 123), (209, 150), (182, 177)], fill=ink, width=12, joint="curve")
        d.line([(67, 195), (164, 195)], fill=ink, width=10)
    elif kind == "coordinate_converter":
        d.ellipse((45, 45, 211, 211), outline=ink, width=10)
        d.ellipse((89, 45, 167, 211), outline=ink, width=8)
        d.line([(48, 128), (208, 128)], fill=ink, width=8)
        d.arc((49, 80, 207, 135), 0, 180, fill=ink, width=7)
        d.arc((49, 122, 207, 177), 180, 360, fill=ink, width=7)
    else:
        d.polygon([(128, 47), (210, 92), (128, 139), (46, 92)], fill=ink)
        d.line([(48, 131), (128, 177), (208, 131)], fill=ink, width=12, joint="curve")
        d.line([(48, 169), (128, 215), (208, 169)], fill=ink, width=12, joint="curve")
    return image


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    for kind, color in [("farmland_context", "#16856F"), ("split_by_size", "#377DC6"), ("shp_to_kml", "#9B71C6"), ("coordinate_converter", "#D58A32")]:
        assets = root / "tools" / kind / "assets"
        assets.mkdir(parents=True, exist_ok=True)
        make_icon(kind, color).save(assets / "icon.png")
    make_icon("app", "#127B80").save(root / "icon.ico", sizes=[(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)])
