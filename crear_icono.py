"""
Genera Assets/icono.ico desde Assets/icono.png.

El PNG de origen es rectangular. Para evitar que Windows o PyInstaller lo
aplasten dentro de un icono cuadrado, se recorta primero a un cuadrado
manteniendo proporcion y luego se generan las resoluciones internas del ICO.
"""
from pathlib import Path

from PIL import Image


ICON_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
SMALL_ICON_ZOOM = {
    16: 1.35,
    24: 1.30,
    32: 1.25,
    48: 1.18,
    64: 1.10,
}


def get_resample_filter():
    try:
        return Image.Resampling.LANCZOS
    except AttributeError:
        return Image.LANCZOS


def crop_to_square_cover(img, centering=(0.5, 0.5)):
    """Recorta al mayor cuadrado posible sin deformar la imagen."""
    bbox = img.getbbox()
    if bbox:
        print(f"  Recortando margenes transparentes: {bbox}")
        img = img.crop(bbox)

    width, height = img.size
    side = min(width, height)

    left = round((width - side) * centering[0])
    top = round((height - side) * centering[1])
    right = left + side
    bottom = top + side

    print(f"  Dimensiones base: {width}x{height}")
    print(f"  Recorte cuadrado: {side}x{side} desde ({left}, {top})")
    return img.crop((left, top, right, bottom))


def zoom_square(img, zoom, centering=(0.5, 0.5)):
    if zoom <= 1:
        return img

    width, height = img.size
    side = min(width, height)
    crop_side = round(side / zoom)
    left = round((width - crop_side) * centering[0])
    top = round((height - crop_side) * centering[1])
    return img.crop((left, top, left + crop_side, top + crop_side))


def crear_ico():
    base_dir = Path(__file__).resolve().parent
    png_path = base_dir / "Assets" / "icono.png"
    ico_path = base_dir / "Assets" / "icono.ico"

    if not png_path.exists():
        print(f"ERROR: No se encontro {png_path}")
        return False

    print(f"Cargando: {png_path}")
    img = Image.open(png_path).convert("RGBA")
    square_img = crop_to_square_cover(img)

    resample_filter = get_resample_filter()
    icon_images = []

    print("  Generando resoluciones internas del ICO...")
    for size in ICON_SIZES:
        width, height = size
        zoom = SMALL_ICON_ZOOM.get(width, 1)
        source = zoom_square(square_img, zoom)
        icon_images.append(source.resize((width, height), resample_filter))
        if zoom > 1:
            print(f"   - {width}x{height}: zoom {zoom:.2f} para escritorio/atajos")

    icon_images[-1].save(ico_path, format="ICO", append_images=icon_images[:-1])

    file_size = ico_path.stat().st_size
    print(f"\n[OK] Icono creado: {ico_path}")
    print(f"   Tamano: {file_size / 1024:.1f} KB")
    print(f"   Resoluciones: {', '.join(f'{w}x{h}' for w, h in ICON_SIZES)}")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if crear_ico() else 1)
