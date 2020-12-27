from math import sqrt

from .settings import COLORS, LO_P

def find_pollution_coords(user_coords: list, edges: list, image: bytes) -> list:
    width, height = image.size
    wpx = int(height * (user_coords[1] - edges[3]) / (edges[2] - edges[3]))
    hpx = width - int(width * (user_coords[0] - edges[1]) / (edges[0] - edges[1]))

    pixelmap = image.load()

    ilev = 0
    cus = [] # closest_unique_spots
    indexed_colors = []
    stopper = True
    while not len(cus) == len(LO_P) and stopper:
        ilev += 1
        layer = []
        # top row
        wpos = wpx - ilev
        for i in range(hpx - ilev, hpx + ilev):
            layer.append([wpos, i])
        # right column
        hpos = hpx + ilev
        for i in range(wpx - ilev, wpx + ilev):
            layer.append([i, hpos])
        # bottom row
        wpos = wpx + ilev
        for i in range(hpx - ilev + 1, hpx + ilev + 1):
            layer.append([wpos, i])
        # left column
        hpos = hpx - ilev
        for i in range(wpx - ilev + 1, wpx + ilev + 1):
            layer.append([i, hpos])

        for px in layer:
            try:
                color = closest_color(pixelmap[px[0], px[1]])
            except IndexError:
                stopper = False
                break
            if not color in indexed_colors and color in LO_P:
                cus.append(matrix_geo_coords(width, height, edges, px))
                indexed_colors.append(color)

    return cus

def matrix_geo_coords(width: int, height: int, edges: list, matrix_coords: list) -> tuple:
    lat = edges[0] - ((edges[0] - edges[1]) / width * matrix_coords[1])
    lng = edges[3] + ((edges[2] - edges[3]) / height * matrix_coords[0])
    return (lat, lng)

def closest_color(rgb: list) -> tuple:
    r, g, b = rgb
    color_diffs = []
    for color in COLORS:
        cr, cg, cb = color
        color_diff = sqrt(abs(r - cr) ** 2 + abs(g - cg) ** 2 + abs(b - cb) ** 2)
        color_diffs.append((color_diff, color))
    return min(color_diffs)[1]
