import os
import sys

sys.path.insert(0, os.path.abspath("."))
import json

from fastapi.testclient import TestClient

from app.main import app


def run_verification():
    client = TestClient(app)

    print("=== 1. Testing Health Endpoint ===")
    res = client.get("/api/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    print("Health check response:", res.json())

    print("\n=== 2. Uploading KML Dataset (Bengaluru Parks) ===")
    with open("data/sample_data/bengaluru_parks.kml", "rb") as f:
        res = client.post("/api/files/", files={"file": ("bengaluru_parks.kml", f, "application/vnd.google-earth.kml+xml")})
    assert res.status_code == 201, f"Upload KML failed: {res.text}"
    kml_info = res.json()
    print("KML Upload Success:", json.dumps(kml_info, indent=2))
    kml_id = kml_info["id"]

    print("\n=== 3. Querying File Info GET /api/files/{id}/ ===")
    res = client.get(f"/api/files/{kml_id}/")
    assert res.status_code == 200
    print("File Info:", json.dumps(res.json(), indent=2))

    print("\n=== 4. Querying Measurements GET /api/files/{id}/measurements/ ===")
    res = client.get(f"/api/files/{kml_id}/measurements/")
    assert res.status_code == 200
    measurements = res.json()
    print("Measurements Result:", json.dumps(measurements, indent=2))

    print("\n=== 5. Uploading Shapefile ZIP Dataset (Berlin Parcels) ===")
    with open("data/sample_data/berlin_parcels.zip", "rb") as f:
        res = client.post("/api/files/", files={"file": ("berlin_parcels.zip", f, "application/zip")})
    assert res.status_code == 201, f"Upload Shapefile failed: {res.text}"
    shp_info = res.json()
    print("Shapefile Upload Success:", json.dumps(shp_info, indent=2))
    shp_id = shp_info["id"]

    print("\n=== 6. Querying Shapefile Measurements ===")
    res = client.get(f"/api/files/{shp_id}/measurements/")
    assert res.status_code == 200
    shp_measurements = res.json()
    print("Shapefile Measurements:", json.dumps(shp_measurements, indent=2))

    print("\n=== 7. Listing Files GET /api/files/ ===")
    res = client.get("/api/files/")
    assert res.status_code == 200
    print("Files count:", res.json()["total"])

    print("\n=== 8. Testing Edge Cases & Error Handling ===")
    # 8a: Non-existent file
    res = client.get("/api/files/123e4567-e89b-12d3-a456-426614174000/")
    assert res.status_code == 404
    print("404 Error Format:", res.json())

    # 8b: Unsupported file type
    res = client.post("/api/files/", files={"file": ("test.txt", b"hello world", "text/plain")})
    assert res.status_code == 400
    print("400 Unsupported Extension:", res.json())

    # 8c: Empty file
    res = client.post("/api/files/", files={"file": ("empty.kml", b"", "application/vnd.google-earth.kml+xml")})
    assert res.status_code == 400
    print("400 Empty File:", res.json())

    print("\nALL LIVE VERIFICATION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_verification()
