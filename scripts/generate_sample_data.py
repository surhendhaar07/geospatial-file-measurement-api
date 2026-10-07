import os
import tempfile
import zipfile

import geopandas as gpd
from shapely.geometry import Polygon

os.makedirs("data/sample_data", exist_ok=True)

# 1. bengaluru_parks.kml
kml_content = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Bengaluru Parks Survey</name>
    <Placemark>
      <name>Cubbon Park Polygon</name>
      <description>Urban green park in Bengaluru</description>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              77.5900,12.9750,0
              77.5950,12.9750,0
              77.5950,12.9800,0
              77.5900,12.9800,0
              77.5900,12.9750,0
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
    <Placemark>
      <name>Kasturba Road Walkway</name>
      <description>Footpath boundary</description>
      <LineString>
        <coordinates>
          77.5910,12.9760,0
          77.5930,12.9780,0
          77.5945,12.9790,0
        </coordinates>
      </LineString>
    </Placemark>
    <Placemark>
      <name>Bandstand Landmark</name>
      <description>Historic bandstand point</description>
      <Point>
        <coordinates>
          77.5925,12.9775,0
        </coordinates>
      </Point>
    </Placemark>
  </Document>
</kml>
"""

with open("data/sample_data/bengaluru_parks.kml", "w", encoding="utf-8") as f:
    f.write(kml_content)

# 2. berlin_parcels.zip
with tempfile.TemporaryDirectory() as tmpdir:
    shp_path = os.path.join(tmpdir, "parcels.shp")
    poly1 = Polygon([(13.3888, 52.5170), (13.3988, 52.5170), (13.3988, 52.5270), (13.3888, 52.5270), (13.3888, 52.5170)])
    poly2 = Polygon([(13.4000, 52.5200), (13.4100, 52.5200), (13.4100, 52.5300), (13.4000, 52.5300), (13.4000, 52.5200)])
    gdf = gpd.GeoDataFrame([
        {"id": 1, "name": "Brandenburg Park", "type": "park", "geometry": poly1},
        {"id": 2, "name": "Alexanderplatz Sector", "type": "commercial", "geometry": poly2}
    ], crs="EPSG:4326")
    gdf.to_file(shp_path, driver="ESRI Shapefile")

    with zipfile.ZipFile("data/sample_data/berlin_parcels.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        for fname in os.listdir(tmpdir):
            zf.write(os.path.join(tmpdir, fname), arcname=fname)

print("Sample datasets generated successfully in data/sample_data/")
