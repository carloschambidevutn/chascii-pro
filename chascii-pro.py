import argparse
import shutil
from pathlib import Path
from typing import cast

from PIL import (
    Image,
    ImageOps,
    ImageEnhance,
    ImageFilter
)

# =========================================================
# CONFIG
# =========================================================

ASCII_CHARS = "@%#*+=-:. "

# Compatibilidad universal Pillow
try:
    RESAMPLE = Image.Resampling.LANCZOS
except Exception:
    RESAMPLE = 1

# =========================================================
# UTILIDADES
# =========================================================

def clamp(value: float) -> int:

    return max(
        0,
        min(255, int(value))
    )


# =========================================================
# GAMMA
# =========================================================

def ajustar_gamma(
    img: Image.Image,
    gamma: float = 1.15
) -> Image.Image:

    tabla = []

    for i in range(256):

        corregido = (
            (i / 255.0) ** gamma
        ) * 255

        tabla.append(
            clamp(corregido)
        )

    return img.point(tabla)


# =========================================================
# DITHERING
# =========================================================

def dithering(
    img: Image.Image
) -> Image.Image:

    img = img.convert("L")

    w, h = img.size

    pixels = img.load()

    if pixels is None:
        return img

    for y in range(h - 1):

        for x in range(1, w - 1):

            old_pixel = int(
                cast(int, pixels[x, y])
            )

            new_pixel = (
                255 if old_pixel > 127
                else 0
            )

            pixels[x, y] = new_pixel

            error = old_pixel - new_pixel

            # derecha
            right = int(
                cast(int, pixels[x + 1, y])
            )

            pixels[x + 1, y] = clamp(
                right + error * 7 / 16
            )

            # abajo izquierda
            bottom_left = int(
                cast(int, pixels[x - 1, y + 1])
            )

            pixels[x - 1, y + 1] = clamp(
                bottom_left + error * 3 / 16
            )

            # abajo
            bottom = int(
                cast(int, pixels[x, y + 1])
            )

            pixels[x, y + 1] = clamp(
                bottom + error * 5 / 16
            )

            # abajo derecha
            bottom_right = int(
                cast(
                    int,
                    pixels[x + 1, y + 1]
                )
            )

            pixels[x + 1, y + 1] = clamp(
                bottom_right + error * 1 / 16
            )

    return img


# =========================================================
# PROCESAMIENTO
# =========================================================

def optimizar_imagen(
    img: Image.Image
) -> Image.Image:

    img = img.convert("RGB")

    # -------------------------------------------------
    # UPSCALE
    # -------------------------------------------------

    w, h = img.size

    upscale = 2

    img = img.resize(
        (
            w * upscale,
            h * upscale
        ),
        RESAMPLE
    )

    # -------------------------------------------------
    # CONTRASTE
    # -------------------------------------------------

    img = ImageOps.autocontrast(
        img,
        cutoff=1
    )

    img = ImageEnhance.Contrast(
        img
    ).enhance(1.2)

    # -------------------------------------------------
    # SHARPEN
    # -------------------------------------------------

    img = ImageEnhance.Sharpness(
        img
    ).enhance(2.2)

    # -------------------------------------------------
    # UNSHARP MASK
    # -------------------------------------------------

    img = img.filter(
        ImageFilter.UnsharpMask(
            radius=2,
            percent=220,
            threshold=2
        )
    )

    # -------------------------------------------------
    # EDGES
    # -------------------------------------------------

    edges = img.filter(
        ImageFilter.FIND_EDGES
    )

    img = Image.blend(
        img,
        edges,
        0.10
    )

    # -------------------------------------------------
    # GRAYSCALE
    # -------------------------------------------------

    img = img.convert("L")

    # -------------------------------------------------
    # GAMMA
    # -------------------------------------------------

    img = ajustar_gamma(
        img,
        0.9
    )

    # -------------------------------------------------
    # CONTRASTE FINAL
    # -------------------------------------------------

    img = ImageOps.autocontrast(img)

    return img


# =========================================================
# REDIMENSIONAR
# =========================================================

def redimensionar(
    img: Image.Image,
    ancho: int
) -> Image.Image:

    w, h = img.size

    ratio = h / w

    alto = max(
        1,
        int(ancho * ratio * 0.50)
    )

    return img.resize(
        (ancho, alto),
        RESAMPLE
    )


# =========================================================
# BUSCAR ARCHIVO
# =========================================================

def encontrar_archivo(
    nombre: str
) -> str:

    ruta = Path(nombre)

    if ruta.is_file():
        return str(ruta)

    carpetas = [
        Path.home() / "Pictures",
        Path.home() / "Downloads",
        Path.home() / "Imágenes",
        Path.home() / "Descargas"
    ]

    for carpeta in carpetas:

        if carpeta.exists():

            resultados = list(
                carpeta.rglob(nombre)
            )

            if resultados:
                return str(
                    resultados[0]
                )

    return nombre


# =========================================================
# PIXEL -> ASCII
# =========================================================

def pixel_a_ascii(pixel: int) -> str:

    # Invertir brillo correctamente
    norm = 1.0 - (pixel / 255.0)

    # Curva perceptual más suave
    norm = norm ** 1.1

    idx = int(
        norm * (len(ASCII_CHARS) - 1)
    )

    idx = max(
        0,
        min(idx, len(ASCII_CHARS) - 1)
    )

    return ASCII_CHARS[idx]


# =========================================================
# IMAGEN -> ASCII
# =========================================================

def imagen_a_ascii(
    ruta: str,
    ancho: int,
    usar_dither: bool = True
) -> str:

    try:

        with Image.open(ruta) as img:

            img = optimizar_imagen(img)

            img = redimensionar(
                img,
                ancho
            )

            if usar_dither:
                img = dithering(img)

            pixels = list(
                cast(list[int], img.getdata())
            )

            ascii_chars = []

            for pixel in pixels:

                ascii_chars.append(
                    pixel_a_ascii(
                        int(pixel)
                    )
                )

            w = img.width

            lineas = []

            for i in range(
                0,
                len(ascii_chars),
                w
            ):

                linea = "".join(
                    ascii_chars[i:i + w]
                )

                lineas.append(linea)

            return "\n".join(lineas)

    except Exception as e:

        return (
            "Error procesando imagen:\n"
            f"{e}"
        )


# =========================================================
# MAIN
# =========================================================

def main():

    term_width, _ = shutil.get_terminal_size(
        fallback=(100, 30)
    )

    default_width = min(
        120,
        term_width - 2
    )

    parser = argparse.ArgumentParser(
        description="ASCII Art Ultra"
    )

    parser.add_argument(
        "ruta",
        help="Ruta imagen"
    )

    parser.add_argument(
        "-w",
        "--width",
        type=int,
        default=default_width,
        help="Ancho ASCII"
    )

    parser.add_argument(
        "-o",
        "--output",
        help="Guardar resultado"
    )

    parser.add_argument(
        "--no-dither",
        action="store_true",
        help="Desactivar dithering"
    )

    args = parser.parse_args()

    ruta = encontrar_archivo(
        args.ruta
    )

    ancho = max(
        20,
        min(
            args.width,
            term_width - 1
        )
    )

    resultado = imagen_a_ascii(
        ruta,
        ancho,
        not args.no_dither
    )

    print()

    print(f"Procesando: {ruta}")
    print(f"Ancho: {ancho}")

    print()

    if args.output:

        Path(args.output).write_text(
            resultado,
            encoding="utf-8"
        )

        print(
            f"Guardado en: {args.output}"
        )

    else:

        print(resultado)


if __name__ == "__main__":
    main()