import os
import xml.etree.ElementTree as ET
import zipfile

from app.core.exceptions import (
    CorruptedArchiveError,
    EmptyFileError,
    InvalidKMLError,
    InvalidShapefileError,
    PathTraversalError,
    UnsupportedFileTypeError,
)
from app.core.logging import logger

SUPPORTED_EXTENSIONS = {".zip", ".kml"}


def validate_file_extension(filename: str) -> str:
    """
    Validates that the file has a supported extension (.zip or .kml).
    Returns normalized lowercase extension.
    """
    if not filename or "." not in filename:
        raise UnsupportedFileTypeError(
            message=f"Uploaded file '{filename}' has no extension. Only .zip and .kml are supported."
        )

    ext = os.path.splitext(filename)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileTypeError(
            message=f"Unsupported file type '{ext}'. Only .zip Shapefile archives and .kml files are accepted.",
            details={"supported_extensions": list(SUPPORTED_EXTENSIONS), "provided_extension": ext}
        )
    return ext


def validate_file_size(size_bytes: int, max_bytes: int) -> None:
    """
    Ensures the uploaded file is not empty and does not exceed maximum configured size.
    """
    if size_bytes == 0:
        raise EmptyFileError("Uploaded file is empty (0 bytes).")
    if size_bytes > max_bytes:
        raise UnsupportedFileTypeError(
            message=f"File size exceeds the maximum limit of {max_bytes / (1024 * 1024):.1f} MB.",
            details={"max_bytes": max_bytes, "received_bytes": size_bytes}
        )


def validate_zip_safe_extraction(zip_path: str, extract_to_dir: str) -> list[str]:
    """
    Validates a ZIP archive against Zip-Slip / path traversal attacks and extracts it safely.
    Returns list of extracted file paths.
    """
    if not zipfile.is_zipfile(zip_path):
        raise CorruptedArchiveError("Uploaded file is not a valid or readable ZIP archive.")

    extracted_files: list[str] = []
    abs_extract_dir = os.path.abspath(extract_to_dir)

    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            infolist = zf.infolist()
            if not infolist:
                raise CorruptedArchiveError("ZIP archive is empty.")

            # Validate each member for path traversal
            for member in infolist:
                # Disallow absolute paths and directory traversal
                member_path = member.filename
                if member_path.startswith(("/", "\\")):
                    raise PathTraversalError(f"Unsafe absolute path detected in archive: {member_path}")

                target_path = os.path.abspath(os.path.join(abs_extract_dir, member_path))
                try:
                    common = os.path.commonpath([abs_extract_dir, target_path])
                except ValueError:
                    raise PathTraversalError(f"Path traversal detected in archive: {member_path}")

                if common != abs_extract_dir:
                    raise PathTraversalError(f"Zip-Slip path traversal vulnerability detected: {member_path}")

            # Safe extraction
            for member in infolist:
                # Skip macOS metadata directories or hidden folders
                if member.filename.startswith("__MACOSX") or "/." in member.filename:
                    continue
                extracted_path = zf.extract(member, abs_extract_dir)
                if not member.is_dir():
                    extracted_files.append(extracted_path)

    except zipfile.BadZipFile as e:
        raise CorruptedArchiveError(f"Corrupted or invalid ZIP archive: {e!s}")

    return extracted_files


def locate_and_validate_shapefile(extracted_files: list[str]) -> str:
    """
    Scans extracted archive files for Shapefiles.
    Ensures exactly one .shp exists, and required companion files (.shx, .dbf) are present.
    Returns the absolute path to the valid .shp file.
    """
    shp_files = [f for f in extracted_files if f.lower().endswith(".shp")]

    if not shp_files:
        raise InvalidShapefileError(
            "ZIP archive does not contain a .shp file. A valid Shapefile package is required."
        )

    if len(shp_files) > 1:
        shp_basenames = [os.path.basename(f) for f in shp_files]
        raise InvalidShapefileError(
            "Ambiguous Shapefile archive: multiple .shp files were found in the archive.",
            details={"found_shapefiles": shp_basenames}
        )

    target_shp = shp_files[0]
    base_no_ext, _ = os.path.splitext(target_shp)

    # Check required companion files
    required_extensions = [".shx", ".dbf"]
    missing_components = []

    all_normalized_paths = {os.path.abspath(f).lower() for f in extracted_files}

    for ext in required_extensions:
        expected_path = os.path.abspath(base_no_ext + ext).lower()
        if expected_path not in all_normalized_paths:
            missing_components.append(ext)

    if missing_components:
        raise InvalidShapefileError(
            f"Shapefile is missing required companion components: {', '.join(missing_components)}. "
            f"An ESRI Shapefile requires at least .shp, .shx, and .dbf files.",
            details={"missing_components": missing_components, "shapefile": os.path.basename(target_shp)}
        )

    # Note: .prj is strongly recommended for CRS detection. If missing, log warning.
    expected_prj = os.path.abspath(base_no_ext + ".prj").lower()
    if expected_prj not in all_normalized_paths:
        logger.warning(f"Shapefile '{os.path.basename(target_shp)}' is missing a .prj file. CRS will default to EPSG:4326 if unresolvable.")

    return target_shp


def validate_kml_content(kml_path: str) -> None:
    """
    Validates that a KML file is readable and structurally valid XML containing KML tags.
    """
    if not os.path.exists(kml_path) or os.path.getsize(kml_path) == 0:
        raise EmptyFileError("KML file is empty.")

    try:
        # Parse XML tree safely
        tree = ET.parse(kml_path)
        root = tree.getroot()

        # Check tag name (strip namespace if present)
        tag_name = root.tag.split("}")[-1] if "}" in root.tag else root.tag
        if tag_name.lower() not in {"kml", "document", "folder"}:
            raise InvalidKMLError(
                f"File XML root tag is '<{tag_name}>', expected '<kml>'.",
                details={"root_tag": tag_name}
            )

    except ET.ParseError as e:
        raise InvalidKMLError(f"Malformed KML file: unable to parse XML content ({e!s}).")
    except Exception as e:
        raise InvalidKMLError(f"Invalid KML file content: {e!s}")
