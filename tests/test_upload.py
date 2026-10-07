import io
import zipfile

from fastapi.testclient import TestClient


def test_upload_valid_kml(client: TestClient, sample_kml_bytes: bytes):
    response = client.post(
        "/api/files/",
        files={"file": ("bengaluru_parks.kml", sample_kml_bytes, "application/vnd.google-earth.kml+xml")}
    )
    assert response.status_code == 201
    data = response.json()

    assert data["id"] is not None
    assert data["filename"] == "bengaluru_parks.kml"
    assert data["file_type"] == "KML"
    assert data["status"] == "COMPLETED"
    assert data["feature_count"] == 3
    assert data["source_crs"] == "EPSG:4326"
    assert "EPSG:32643" in data["measurement_crs"]  # Bengaluru is UTM zone 43N


def test_upload_valid_shapefile_zip(client: TestClient, sample_shapefile_zip_bytes: bytes):
    response = client.post(
        "/api/files/",
        files={"file": ("berlin_parcels.zip", sample_shapefile_zip_bytes, "application/zip")}
    )
    assert response.status_code == 201
    data = response.json()

    assert data["id"] is not None
    assert data["filename"] == "berlin_parcels.zip"
    assert data["file_type"] == "SHAPEFILE_ZIP"
    assert data["status"] == "COMPLETED"
    assert data["feature_count"] == 2
    assert data["source_crs"] == "EPSG:4326"
    assert data["measurement_crs"] == "EPSG:32633"  # Berlin is UTM zone 33N


def test_upload_empty_file(client: TestClient):
    response = client.post(
        "/api/files/",
        files={"file": ("empty.kml", b"", "application/vnd.google-earth.kml+xml")}
    )
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "EMPTY_FILE"


def test_upload_unsupported_file_extension(client: TestClient):
    response = client.post(
        "/api/files/",
        files={"file": ("data.geojson", b'{"type": "FeatureCollection"}', "application/json")}
    )
    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


def test_upload_corrupted_zip(client: TestClient):
    response = client.post(
        "/api/files/",
        files={"file": ("corrupt.zip", b"Not a zip file header content", "application/zip")}
    )
    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "CORRUPTED_ARCHIVE"


def test_upload_zip_missing_shp(client: TestClient):
    # Valid ZIP but contains no .shp file
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("notes.txt", "just some notes")
    buf.seek(0)

    response = client.post(
        "/api/files/",
        files={"file": ("no_shp.zip", buf.getvalue(), "application/zip")}
    )
    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "INVALID_SHAPEFILE"
    assert "does not contain a .shp file" in data["error"]["message"]


def test_upload_invalid_kml(client: TestClient):
    bad_kml = b"<?xml version='1.0'?><invalid>Not KML</invalid>"
    response = client.post(
        "/api/files/",
        files={"file": ("bad.kml", bad_kml, "application/vnd.google-earth.kml+xml")}
    )
    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "INVALID_KML"
