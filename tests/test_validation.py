import io
import zipfile

import pytest

from app.core.exceptions import (
    CorruptedArchiveError,
    EmptyFileError,
    InvalidKMLError,
    InvalidShapefileError,
    PathTraversalError,
    UnsupportedFileTypeError,
)
from app.utils.file_validation import (
    locate_and_validate_shapefile,
    validate_file_extension,
    validate_file_size,
    validate_kml_content,
    validate_zip_safe_extraction,
)


def test_validate_file_extension_valid():
    assert validate_file_extension("data.zip") == ".zip"
    assert validate_file_extension("SURVEY.ZIP") == ".zip"
    assert validate_file_extension("boundaries.kml") == ".kml"
    assert validate_file_extension("BOUNDARIES.KML") == ".kml"


def test_validate_file_extension_invalid():
    with pytest.raises(UnsupportedFileTypeError) as exc:
        validate_file_extension("report.pdf")
    assert "Unsupported file type" in str(exc.value)

    with pytest.raises(UnsupportedFileTypeError):
        validate_file_extension("archive.tar.gz")

    with pytest.raises(UnsupportedFileTypeError):
        validate_file_extension("no_extension_file")


def test_validate_file_size():
    # Valid size
    validate_file_size(1024, max_bytes=10 * 1024 * 1024)

    # Empty file
    with pytest.raises(EmptyFileError):
        validate_file_size(0, max_bytes=10 * 1024 * 1024)

    # Exceeds max
    with pytest.raises(UnsupportedFileTypeError):
        validate_file_size(11 * 1024 * 1024, max_bytes=10 * 1024 * 1024)


def test_validate_zip_corrupted(tmp_path):
    bad_zip_file = tmp_path / "corrupted.zip"
    bad_zip_file.write_bytes(b"This is completely invalid zip header content")

    with pytest.raises(CorruptedArchiveError):
        validate_zip_safe_extraction(str(bad_zip_file), str(tmp_path / "extracted"))


def test_validate_zip_path_traversal(tmp_path):
    evil_zip_path = tmp_path / "evil.zip"
    
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr("../../etc/passwd", "malicious payload")
    evil_zip_path.write_bytes(zip_buf.getvalue())

    with pytest.raises(PathTraversalError):
        validate_zip_safe_extraction(str(evil_zip_path), str(tmp_path / "extracted"))


def test_locate_shapefile_missing_shp():
    extracted = ["/tmp/file1.txt", "/tmp/data.dbf"]
    with pytest.raises(InvalidShapefileError) as exc:
        locate_and_validate_shapefile(extracted)
    assert "does not contain a .shp file" in str(exc.value)


def test_locate_shapefile_ambiguous_multiple_shp():
    extracted = ["/tmp/layer1.shp", "/tmp/layer2.shp", "/tmp/layer1.shx", "/tmp/layer1.dbf"]
    with pytest.raises(InvalidShapefileError) as exc:
        locate_and_validate_shapefile(extracted)
    assert "multiple .shp files" in str(exc.value)


def test_locate_shapefile_missing_components():
    extracted = ["/tmp/layer.shp", "/tmp/layer.shx"]  # Missing .dbf
    with pytest.raises(InvalidShapefileError) as exc:
        locate_and_validate_shapefile(extracted)
    assert "missing required companion components" in str(exc.value).lower()


def test_validate_kml_invalid_xml(tmp_path):
    bad_kml = tmp_path / "invalid.kml"
    bad_kml.write_text("<kml><Document><unclosed_tag></kml>")

    with pytest.raises(InvalidKMLError):
        validate_kml_content(str(bad_kml))


def test_validate_kml_wrong_root(tmp_path):
    not_kml = tmp_path / "wrong_root.kml"
    not_kml.write_text('<?xml version="1.0"?><html xmlns="http://www.w3.org/1999/xhtml"><body>test</body></html>')

    with pytest.raises(InvalidKMLError):
        validate_kml_content(str(not_kml))
