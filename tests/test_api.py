from fastapi.testclient import TestClient


def test_get_file_info_endpoint(client: TestClient, sample_kml_bytes: bytes):
    # 1. Upload file
    upload_res = client.post(
        "/api/files/",
        files={"file": ("survey.kml", sample_kml_bytes, "application/vnd.google-earth.kml+xml")}
    )
    assert upload_res.status_code == 201
    file_id = upload_res.json()["id"]

    # 2. Get file info
    info_res = client.get(f"/api/files/{file_id}/")
    assert info_res.status_code == 200
    info_data = info_res.json()

    assert info_data["id"] == file_id
    assert info_data["filename"] == "survey.kml"
    assert info_data["feature_count"] == 3
    assert info_data["crs"] == "EPSG:4326"
    assert info_data["source_crs"] == "EPSG:4326"
    assert info_data["status"] == "COMPLETED"
    assert info_data["file_type"] == "KML"


def test_get_file_info_not_found(client: TestClient):
    res = client.get("/api/files/00000000-0000-0000-0000-000000000000/")
    assert res.status_code == 404
    data = res.json()
    assert data["error"]["code"] == "NOT_FOUND"


def test_get_measurements_endpoint(client: TestClient, sample_kml_bytes: bytes):
    # 1. Upload file
    upload_res = client.post(
        "/api/files/",
        files={"file": ("bengaluru.kml", sample_kml_bytes, "application/vnd.google-earth.kml+xml")}
    )
    assert upload_res.status_code == 201
    file_id = upload_res.json()["id"]

    # 2. Get measurements
    meas_res = client.get(f"/api/files/{file_id}/measurements/")
    assert meas_res.status_code == 200
    meas_data = meas_res.json()

    assert meas_data["file_id"] == file_id
    assert meas_data["filename"] == "bengaluru.kml"
    assert meas_data["feature_count"] == 3
    assert meas_data["source_crs"] == "EPSG:4326"
    assert "EPSG:32643" in meas_data["measurement_crs"]

    measurements = meas_data["measurements"]
    assert len(measurements) == 3

    # Feature 0: Polygon
    poly_feat = measurements[0]
    assert poly_feat["feature_id"] == 0
    assert poly_feat["geometry_type"] == "Polygon"
    assert poly_feat["measurement_type"] == "area"
    assert poly_feat["unit"] == "square_meters"
    assert poly_feat["status"] == "COMPLETED"
    assert poly_feat["value"] > 0
    prop_name = poly_feat["properties"].get("Name") or poly_feat["properties"].get("name", "")
    assert "Cubbon Park" in prop_name

    # Feature 1: LineString
    line_feat = measurements[1]
    assert line_feat["feature_id"] == 1
    assert line_feat["geometry_type"] == "LineString"
    assert line_feat["measurement_type"] == "length"
    assert line_feat["unit"] == "meters"
    assert line_feat["status"] == "COMPLETED"
    assert line_feat["value"] > 0

    # Feature 2: Point
    pt_feat = measurements[2]
    assert pt_feat["feature_id"] == 2
    assert pt_feat["geometry_type"] == "Point"
    assert pt_feat["measurement_type"] is None
    assert pt_feat["unit"] is None
    assert pt_feat["value"] is None
    assert pt_feat["status"] == "NOT_REQUIRED"


def test_get_measurements_not_found(client: TestClient):
    res = client.get("/api/files/nonexistent-id/measurements/")
    assert res.status_code == 404
    data = res.json()
    assert data["error"]["code"] == "NOT_FOUND"


def test_list_files_endpoint(client: TestClient, sample_kml_bytes: bytes):
    # Upload one file
    client.post(
        "/api/files/",
        files={"file": ("list_test.kml", sample_kml_bytes, "application/vnd.google-earth.kml+xml")}
    )

    res = client.get("/api/files/?skip=0&limit=10")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert data["total"] >= 1
    assert any(f["filename"] == "list_test.kml" for f in data["items"])


def test_health_check_endpoint(client: TestClient):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "online"
    assert data["database"] == "healthy"


def test_root_endpoint(client: TestClient):
    res = client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "online"
    assert "documentation" in data
    assert data["documentation"]["swagger_ui"] == "/docs"
