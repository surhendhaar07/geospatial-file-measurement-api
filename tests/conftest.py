import io
import os
import tempfile
import zipfile
from collections.abc import Generator

import geopandas as gpd
import pytest
from fastapi.testclient import TestClient
from shapely.geometry import Polygon
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.session import get_db
from app.main import app
from app.models.base import Base

settings = get_settings()

# Use temporary SQLite database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(test_engine) -> Generator[Session, None, None]:
    """Provides a transactional database session per test with automatic rollback."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(autocommit=False, autoflush=False, bind=connection, expire_on_commit=False)()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with overridden database session."""
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_kml_bytes() -> bytes:
    """Returns valid KML 2.2 XML containing Polygon, LineString, and Point features in EPSG:4326."""
    kml_text = """<?xml version="1.0" encoding="UTF-8"?>
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
</kml>"""
    return kml_text.encode("utf-8")


@pytest.fixture
def sample_shapefile_zip_bytes() -> bytes:
    """
    Dynamically generates a genuine ESRI Shapefile archive containing .shp, .shx, .dbf, and .prj.
    Includes Polygon, LineString, and Point features in WGS 84 (EPSG:4326).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        shp_path = os.path.join(tmpdir, "parcels.shp")

        # Create sample polygon in Berlin (EPSG:4326)
        poly = Polygon([
            (13.3888, 52.5170),
            (13.3988, 52.5170),
            (13.3988, 52.5270),
            (13.3888, 52.5270),
            (13.3888, 52.5170)
        ])
        poly2 = Polygon([
            (13.4000, 52.5200),
            (13.4100, 52.5200),
            (13.4100, 52.5300),
            (13.4000, 52.5300),
            (13.4000, 52.5200)
        ])

        gdf = gpd.GeoDataFrame(
            [
                {"id": 1, "name": "Brandenburg Park", "type": "park", "geometry": poly},
                {"id": 2, "name": "Alexanderplatz Sector", "type": "commercial", "geometry": poly2}
            ],
            crs="EPSG:4326"
        )
        gdf.to_file(shp_path, driver="ESRI Shapefile")

        # Package into a zip archive in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for fname in os.listdir(tmpdir):
                fpath = os.path.join(tmpdir, fname)
                zf.write(fpath, arcname=fname)

        zip_buffer.seek(0)
        return zip_buffer.getvalue()
