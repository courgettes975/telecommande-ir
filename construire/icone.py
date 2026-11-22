# Dessine l'icone de l'application (128x128, PNG) sans bibliotheque externe.
import struct
import sys
import zlib

T = 128
ORANGE, BLANC, FONCE, ROUGE = (243, 156, 18), (255, 255, 255), (11, 29, 46), (231, 76, 60)


def dans_rectangle_arrondi(x, y, x1, y1, x2, y2, r):
    if not (x1 <= x <= x2 and y1 <= y <= y2):
        return False
    cx = min(max(x, x1 + r), x2 - r)
    cy = min(max(y, y1 + r), y2 - r)
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def pixel(x, y):
    if not dans_rectangle_arrondi(x, y, 4, 4, 123, 123, 26):
        return (0, 0, 0, 0)
    # ondes infrarouges en haut a droite
    for rayon in (18, 28):
        d = ((x - 92) ** 2 + (y - 30) ** 2) ** 0.5
        if abs(d - rayon) < 3 and x > 92 and y < 30:
            return BLANC + (255,)
    # telecommande
    if dans_rectangle_arrondi(x, y, 38, 40, 82, 116, 10):
        if (x - 60) ** 2 + (y - 54) ** 2 <= 49:
            return ROUGE + (255,)
        for bx in (49, 60, 71):
            for by in (72, 86, 100):
                if (x - bx) ** 2 + (y - by) ** 2 <= 16:
                    return ORANGE + (255,)
        return FONCE + (255,)
    return ORANGE + (255,)


def png(chemin):
    lignes = b"".join(b"\x00" + bytes(c for x in range(T) for c in pixel(x, y)) for y in range(T))

    def bloc(type_, donnees):
        return struct.pack(">I", len(donnees)) + type_ + donnees + struct.pack(">I", zlib.crc32(type_ + donnees) & 0xFFFFFFFF)

    with open(chemin, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(bloc(b"IHDR", struct.pack(">IIBBBBB", T, T, 8, 6, 0, 0, 0)))
        f.write(bloc(b"IDAT", zlib.compress(lignes, 9)))
        f.write(bloc(b"IEND", b""))


png(sys.argv[1] if len(sys.argv) > 1 else "telecommande.png")
