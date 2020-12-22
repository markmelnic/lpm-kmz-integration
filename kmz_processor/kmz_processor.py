import glob, csv
import pandas as pd
from lxml import html
from zipfile import ZipFile
from PIL import Image
from math import sqrt

from kmz_processor.settings import *

pd.options.mode.chained_assignment = None

class KMZ:
    def __init__(self, csv=False) -> None:
        self.kmz_zip = ZipFile(glob.glob("*.kmz")[0], "r")
        self.kml_file = self.kmz_zip.open(ZIP_KML_DOC, "r").read()

        self.globe_matrix = []
        if csv:
            self._load_df(to_csv=csv)
        else:
            self._load_df()
        self._arrange_df()

    def _load_data(self, ):
        kml_content = html.fromstring(self.kml_file)
        temp = []
        for item in kml_content.cssselect("Document GroundOverlay"):
            image = item.cssselect("name")[0].text_content()
            index = image[23:-4]
            draw_order = item.cssselect("drawOrder")[0].text_content()
            coords = item.cssselect("LatLonBox")[0]
            north = float(coords.cssselect("north")[0].text_content())
            south = float(coords.cssselect("south")[0].text_content())
            east = float(coords.cssselect("east")[0].text_content())
            west = float(coords.cssselect("west")[0].text_content())
            rotation = coords.cssselect("rotation")[0].text_content()
            temp.append([index, image, draw_order, north, south, east, west, rotation])
        return temp

    def _load_df(self, to_csv=False) -> None:
        if to_csv:
            self._data_to_csv(self._load_data())
            self.df = pd.read_csv(CSV_KML_DOC)
        else:
            self.df = pd.DataFrame(self._load_data(), columns=DF_COLUMNS)
        self.df.sort_values(by='north', ascending=False, inplace = True)

    def _data_to_csv(self, data: list) -> None:
        with open(CSV_KML_DOC, "w", newline="") as kml_csv:
            kml_csv_writer = csv.writer(kml_csv)
            kml_csv_writer.writerow(DF_COLUMNS)
            for item in data:
                kml_csv_writer.writerow(item)

    def _arrange_df(self, ) -> None:
        for i, row in self.df.iterrows():
            sub_df = self.df.loc[(self.df['north'] == row['north']) & (self.df['south'] == row['south'])]
            if not sub_df.empty:
                sub_df.sort_values(by='west', inplace = True)
                self.globe_matrix.append(sub_df)
                self.df.drop(sub_df.index, inplace = True)

    def _generate_image(self, images: list, fullvh=False, vertical=False, horizontal=False):
        if horizontal:
            widths, heights = zip(*(img.size for img in images))
            total_width = sum(widths)
            max_height = max(heights)

            new_image = Image.new('RGB', (total_width, max_height))
            x_offset = 0
            for img in images:
                new_image.paste(img, (x_offset,0))
                x_offset += img.size[0]

        elif vertical:
            widths, heights = zip(*(img.size for img in images))
            max_width = max(widths)
            total_height = sum(heights)

            new_image = Image.new('RGB', (max_width, total_height))
            y_offset = 0
            for img in images:
                new_image.paste(img, (0,y_offset))
                y_offset += img.size[1]
        elif fullvh:
            vertical_set = [self._generate_image(image, horizontal=True) for image in images]
            new_image = self._generate_image(vertical_set, vertical=True)

        return new_image

    def _closest_color(self, rgb: list) -> tuple:
            r, g, b = rgb
            color_diffs = []
            for color in COLORS:
                cr, cg, cb = color
                color_diff = sqrt(abs(r - cr) ** 2 + abs(g - cg) ** 2 + abs(b - cb) ** 2)
                color_diffs.append((color_diff, color))
            return min(color_diffs)[1]

    def coords_item(self, coords: list) -> list:
        if coords[0] > 0: # first 10
            gset = [None, -7]
            if coords[1] > 0: # last 21
                sset = [22, None]
            else:
                sset = [None, -21]
        else: # last 7
            gset = [10, None]
            if coords[1] > 0: # last 21
                sset = [22, None]
            else:
                sset = [None, -21]

        for item in self.globe_matrix[gset[0]:gset[1]]:
            for i, row in item.iloc[sset[0]:sset[1]].iterrows():
                if (row['north'] >= coords[0] >= row['south']) and (row['west'] <= coords[1] <= row['east']):
                    return row.tolist()

    def load_images(self, images, single=False, neighbours=False) -> list:
        if single:
            if neighbours:
                f = [images[:-7], images[-4:]]
                c = int(images[:-4][-3:])
                images = [
                    [c+42 , c+43, c+44],
                    [c-1  , c    , c+1],
                    [c-44, c-43, c-42],
                    ]

                edges = [0, 0, 0, 0]
                for item in self.globe_matrix:
                    for i, row in item.iterrows():
                        row = row.tolist()
                        if int(row[0]) == images[0][0]:
                            edges[0] = row[3]
                            edges[3] = row[6]
                        elif int(row[0]) == images[2][2]:
                            edges[1] = row[4]
                            edges[2] = row[5]

                for i, s in enumerate(images):
                    for j, g in enumerate(s):
                        images[i][j] = f[0]+str(g)+f[1]

                return edges, self._generate_image(self.load_images(images), fullvh=True)
            else:
                return Image.open(self.kmz_zip.open(ZIP_KMZ_IMG_FOLDER+"/"+images))
        else:
            if images:
                if type(images[0]) == list:
                    kmz_imgs = [[Image.open(self.kmz_zip.open(ZIP_KMZ_IMG_FOLDER+"/"+image)) for image in image_set] for image_set in images]
                else:
                    kmz_imgs = [Image.open(self.kmz_zip.open(ZIP_KMZ_IMG_FOLDER+"/"+image)) for image in images]
            else:
                kmz_imgs = [Image.open(self.kmz_zip.open(image)) for image in self.kmz_zip.namelist() if image.split("/")[0] == ZIP_KMZ_IMG_FOLDER]
            return kmz_imgs

    def global_imager(self, images=[]) -> None:
        if images == []:
            images = [self.load_images(matrix["image"].tolist()) for matrix in self.globe_matrix]
        self._generate_image(images, fullvh=True).save(KMZ_GLOBAL_IMAGE)
