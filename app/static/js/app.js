/* ==========================================================================
   Geospatial File Measurement Studio - Interactive Client Logic
   ========================================================================== */

let currentMap = null;
let currentGeoJsonLayer = null;
let currentMeasurements = [];
let selectedFile = null;
const featureLayersMap = new Map();

// Allowed file extensions
const ALLOWED_EXTENSIONS = ['.zip', '.kml'];
const MAX_SIZE_BYTES = 50 * 1024 * 1024; // 50MB

document.addEventListener('DOMContentLoaded', () => {
    initMap();
    initUploadListeners();
    initTableFilters();
    checkApiHealth();
    loadRecentFiles();
});

/* ==========================================================================
   1. Map Initialization (Leaflet with CartoDB Positron Light Tiles)
   ========================================================================== */
function initMap() {
    currentMap = L.map('map', {
        zoomControl: true,
        attributionControl: true
    }).setView([20, 0], 2);

    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 20
    }).addTo(currentMap);
}

/* ==========================================================================
   2. File Pre-Validation & Upload Management
   ========================================================================== */
function initUploadListeners() {
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('fileInput');
    const btnUpload = document.getElementById('btnUpload');

    // Drag-and-drop events
    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.remove('dragover');
        });
    });

    dropzone.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files && files.length > 0) {
            handleSelectedFile(files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (fileInput.files && fileInput.files.length > 0) {
            handleSelectedFile(fileInput.files[0]);
        }
    });

    btnUpload.addEventListener('click', () => {
        if (selectedFile) {
            uploadAndProcessFile(selectedFile);
        }
    });
}

/**
 * CLIENT-SIDE PRE-VALIDATION:
 * Validates format extension, size, and readiness before network transfer.
 */
function handleSelectedFile(file) {
    selectedFile = file;
    const panel = document.getElementById('validationPanel');
    const btnUpload = document.getElementById('btnUpload');
    const valFilename = document.getElementById('valFilename');
    const valMeta = document.getElementById('valMeta');
    const valBadge = document.getElementById('valBadge');
    const valMessage = document.getElementById('valMessage');
    const valIcon = document.getElementById('valIcon');

    panel.className = 'validation-panel';
    valMessage.textContent = '';

    const filename = file.name || 'unnamed';
    const ext = filename.substring(filename.lastIndexOf('.')).toLowerCase();
    const sizeFormatted = formatFileSize(file.size);

    // 1. Check format extension
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
        panel.classList.add('invalid');
        valIcon.textContent = '⚠️';
        valFilename.textContent = filename;
        valMeta.textContent = `Size: ${sizeFormatted} • Detected extension: ${ext || 'none'}`;
        valBadge.className = 'val-badge error';
        valBadge.textContent = 'Format Rejected';
        valMessage.className = 'val-message error';
        valMessage.textContent = `Unsupported file format '${ext}'. The API strictly accepts ESRI Shapefiles (.zip) or OGC KML (.kml) files.`;
        btnUpload.disabled = true;
        return;
    }

    // 2. Check file size
    if (file.size === 0) {
        panel.classList.add('invalid');
        valIcon.textContent = '⚠️';
        valFilename.textContent = filename;
        valMeta.textContent = `Size: 0 Bytes`;
        valBadge.className = 'val-badge error';
        valBadge.textContent = 'Empty File';
        valMessage.className = 'val-message error';
        valMessage.textContent = 'The selected file is empty (0 bytes). Please select a valid dataset.';
        btnUpload.disabled = true;
        return;
    }

    if (file.size > MAX_SIZE_BYTES) {
        panel.classList.add('invalid');
        valIcon.textContent = '⚠️';
        valFilename.textContent = filename;
        valMeta.textContent = `Size: ${sizeFormatted}`;
        valBadge.className = 'val-badge error';
        valBadge.textContent = 'File Too Large';
        valMessage.className = 'val-message error';
        valMessage.textContent = `File size (${sizeFormatted}) exceeds the 50 MB threshold.`;
        btnUpload.disabled = true;
        return;
    }

    // Valid format!
    panel.classList.add('valid');
    valIcon.textContent = ext === '.zip' ? '📦' : '🗺️';
    valFilename.textContent = filename;
    const formatName = ext === '.zip' ? 'ESRI Shapefile Archive (.zip)' : 'Keyhole Markup Language (.kml)';
    valMeta.innerHTML = `<span><strong>Format:</strong> ${formatName}</span> • <span><strong>Size:</strong> ${sizeFormatted}</span>`;
    valBadge.className = 'val-badge success';
    valBadge.textContent = '✓ Format Verified';
    valMessage.className = 'val-message';
    valMessage.innerHTML = `<span style="color: var(--success); font-weight:600;">File passed pre-flight format verification. Ready to upload and compute measurements.</span>`;

    btnUpload.disabled = false;
    btnUpload.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/* ==========================================================================
   3. File Upload & Processing API Execution
   ========================================================================== */
async function uploadAndProcessFile(file) {
    const btnUpload = document.getElementById('btnUpload');
    const originalText = btnUpload.innerHTML;

    try {
        btnUpload.disabled = true;
        btnUpload.innerHTML = `<span class="spinner"></span> Processing Geospatial Data...`;

        const formData = new FormData();
        formData.append('file', file);

        // Call POST /api/files/
        const uploadRes = await fetch('/api/files/', {
            method: 'POST',
            body: formData
        });

        const uploadData = await uploadRes.json();

        if (!uploadRes.ok) {
            const errCode = uploadData.error?.code || 'ERROR';
            const errMsg = uploadData.error?.message || 'Upload processing failed.';
            alert(`Error [${errCode}]: ${errMsg}`);
            return;
        }

        const fileId = uploadData.id;

        // Fetch detailed measurements: GET /api/files/{id}/measurements/
        await loadMeasurementsForFile(fileId);
        loadRecentFiles();

    } catch (err) {
        console.error('Upload error:', err);
        alert('An unexpected network error occurred while uploading.');
    } finally {
        btnUpload.disabled = false;
        btnUpload.innerHTML = originalText;
    }
}

/* ==========================================================================
   4. Measurement Rendering & Analytics Calculation
   ========================================================================== */
async function loadMeasurementsForFile(fileId) {
    try {
        const res = await fetch(`/api/files/${fileId}/measurements/`);
        if (!res.ok) {
            throw new Error('Failed to retrieve measurements.');
        }

        const data = await res.json();
        currentMeasurements = data.measurements || [];

        // Update Overview Statistics
        document.getElementById('statTotalFeatures').textContent = data.feature_count;
        document.getElementById('statSourceCrs').textContent = data.source_crs || 'EPSG:4326';
        document.getElementById('statTargetCrs').textContent = data.measurement_crs || 'Auto UTM';

        // Calculate aggregates
        let totalArea = 0;
        let totalLength = 0;
        let polyCount = 0;
        let lineCount = 0;
        let pointCount = 0;

        currentMeasurements.forEach(m => {
            if (m.measurement_type === 'area' && m.value) {
                totalArea += m.value;
                polyCount++;
            } else if (m.measurement_type === 'length' && m.value) {
                totalLength += m.value;
                lineCount++;
            } else if (m.geometry_type.includes('Point')) {
                pointCount++;
            }
        });

        document.getElementById('statTotalArea').textContent = formatArea(totalArea);
        document.getElementById('statTotalLength').textContent = formatLength(totalLength);
        document.getElementById('statFeaturesSub').textContent = `${polyCount} Polygons • ${lineCount} Lines • ${pointCount} Points`;

        // Render Map
        renderFeaturesOnMap(currentMeasurements);

        // Render Table
        renderMeasurementsTable(currentMeasurements);

        // Scroll to dashboard results
        document.getElementById('dashboardSection').scrollIntoView({ behavior: 'smooth' });

    } catch (err) {
        console.error('Failed to load measurements:', err);
    }
}

function formatArea(sqMeters) {
    if (!sqMeters || sqMeters === 0) return '0 m²';
    if (sqMeters >= 1000000) {
        return `${(sqMeters / 1000000).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} km²`;
    }
    return `${sqMeters.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} m²`;
}

function formatLength(meters) {
    if (!meters || meters === 0) return '0 m';
    if (meters >= 1000) {
        return `${(meters / 1000).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} km`;
    }
    return `${meters.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} m`;
}

/* ==========================================================================
   5. Interactive Map Rendering
   ========================================================================== */
function renderFeaturesOnMap(measurements) {
    if (currentGeoJsonLayer) {
        currentMap.removeLayer(currentGeoJsonLayer);
    }
    featureLayersMap.clear();

    const geoJsonFeatures = [];

    measurements.forEach(m => {
        if (m.geometry) {
            geoJsonFeatures.push({
                type: 'Feature',
                properties: {
                    ...m.properties,
                    feature_id: m.feature_id,
                    geometry_type: m.geometry_type,
                    measurement_type: m.measurement_type,
                    value: m.value,
                    unit: m.unit,
                    status: m.status
                },
                geometry: m.geometry
            });
        }
    });

    if (geoJsonFeatures.length === 0) return;

    currentGeoJsonLayer = L.geoJSON({ type: 'FeatureCollection', features: geoJsonFeatures }, {
        style: (feature) => {
            const gType = feature.properties.geometry_type;
            if (gType.includes('Polygon')) {
                return {
                    color: '#059669',
                    weight: 2,
                    fillColor: '#10b981',
                    fillOpacity: 0.4
                };
            }
            if (gType.includes('Line')) {
                return {
                    color: '#4f46e5',
                    weight: 4,
                    opacity: 0.85
                };
            }
            return { color: '#f59e0b', weight: 2 };
        },
        pointToLayer: (feature, latlng) => {
            return L.circleMarker(latlng, {
                radius: 7,
                fillColor: '#f59e0b',
                color: '#ffffff',
                weight: 2,
                opacity: 1,
                fillOpacity: 0.9
            });
        },
        onEachFeature: (feature, layer) => {
            const p = feature.properties;
            featureLayersMap.set(p.feature_id, layer);

            let measHtml = '';
            if (p.measurement_type === 'area') {
                measHtml = `<strong>Area:</strong> ${formatArea(p.value)} (${p.value.toLocaleString()} sq meters)`;
            } else if (p.measurement_type === 'length') {
                measHtml = `<strong>Length:</strong> ${formatLength(p.value)} (${p.value.toLocaleString()} meters)`;
            } else {
                measHtml = `<strong>Measurement:</strong> Not Required (Point)`;
            }

            const name = p.name || p.Name || `Feature #${p.feature_id}`;
            const popupContent = `
                <div style="font-family: inherit; font-size: 0.85rem;">
                    <div style="font-weight:700; color: #0f172a; margin-bottom: 4px;">${name}</div>
                    <div style="color: #64748b; margin-bottom: 6px;">ID: ${p.feature_id} • ${p.geometry_type}</div>
                    <div style="background: #f1f5f9; padding: 6px 8px; border-radius: 4px; margin-bottom: 6px;">${measHtml}</div>
                    <div style="font-size: 0.75rem; color: #64748b;">Status: <span style="font-weight:600; color: #059669;">${p.status}</span></div>
                </div>
            `;
            layer.bindPopup(popupContent);

            // Hover interactions
            layer.on({
                mouseover: (e) => {
                    const l = e.target;
                    if (l.setStyle) {
                        l.setStyle({ weight: 4, fillOpacity: 0.65 });
                    }
                },
                mouseout: (e) => {
                    currentGeoJsonLayer.resetStyle(e.target);
                }
            });
        }
    }).addTo(currentMap);

    // Zoom to features bounds
    try {
        const bounds = currentGeoJsonLayer.getBounds();
        if (bounds.isValid()) {
            currentMap.fitBounds(bounds, { padding: [35, 35] });
        }
    } catch (e) {
        console.warn('Could not fit bounds:', e);
    }
}

function zoomToFeature(featureId) {
    const layer = featureLayersMap.get(featureId);
    if (layer && currentMap) {
        if (layer.getBounds) {
            currentMap.fitBounds(layer.getBounds(), { padding: [50, 50], maxZoom: 17 });
        } else if (layer.getLatLng) {
            currentMap.setView(layer.getLatLng(), 16);
        }
        layer.openPopup();
    }
}

/* ==========================================================================
   6. Interactive Measurements Table & Filtering
   ========================================================================= */
function renderMeasurementsTable(measurements) {
    const tbody = document.getElementById('tableBody');
    tbody.innerHTML = '';

    if (!measurements || measurements.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 2rem; color: var(--text-muted);">No feature measurements available.</td></tr>`;
        return;
    }

    measurements.forEach(m => {
        const tr = document.createElement('tr');
        tr.dataset.featureId = m.feature_id;
        tr.dataset.geometryType = m.geometry_type;

        // Badge styling for geometry
        let geomBadgeClass = 'badge-other';
        if (m.geometry_type.includes('Polygon')) geomBadgeClass = 'badge-polygon';
        else if (m.geometry_type.includes('Line')) geomBadgeClass = 'badge-line';
        else if (m.geometry_type.includes('Point')) geomBadgeClass = 'badge-point';

        // Badge styling for status
        let statusBadgeClass = 'badge-completed';
        if (m.status === 'NOT_REQUIRED') statusBadgeClass = 'badge-not-req';
        else if (m.status === 'NOT_SUPPORTED') statusBadgeClass = 'badge-unsupported';

        // Measurement value formatting
        let valueDisplay = '<span style="color: var(--text-subtle);">&mdash;</span>';
        let unitDisplay = '<span style="color: var(--text-subtle);">&mdash;</span>';
        if (m.value !== null && m.value !== undefined) {
            valueDisplay = `<span class="val-num">${m.value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 })}</span>`;
            unitDisplay = m.unit === 'square_meters' ? 'sq meters' : (m.unit || '');
        }

        // Properties preview
        const props = m.properties || {};
        const propTitle = props.name || props.Name || props.description || JSON.stringify(props).substring(0, 30);

        tr.innerHTML = `
            <td><strong>#${m.feature_id}</strong></td>
            <td><span class="badge ${geomBadgeClass}">${m.geometry_type}</span></td>
            <td>${valueDisplay}</td>
            <td>${unitDisplay}</td>
            <td><span class="badge ${statusBadgeClass}">${m.status}</span></td>
            <td style="max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title='${JSON.stringify(props)}'>
                ${propTitle}
            </td>
            <td>
                <div style="display: flex; gap: 0.35rem;">
                    <button class="btn btn-secondary btn-xs" onclick="zoomToFeature(${m.feature_id})">🔍 Zoom</button>
                    <button class="btn btn-secondary btn-xs" onclick="inspectProperties(${m.feature_id})">{ } Props</button>
                </div>
            </td>
        `;

        tr.addEventListener('click', (e) => {
            if (e.target.tagName !== 'BUTTON') {
                zoomToFeature(m.feature_id);
            }
        });

        tbody.appendChild(tr);
    });
}

function initTableFilters() {
    const searchInput = document.getElementById('tableSearch');
    const filterSelect = document.getElementById('filterGeometry');

    const filterRows = () => {
        const query = searchInput.value.toLowerCase().trim();
        const selectedType = filterSelect.value;
        const rows = document.querySelectorAll('#tableBody tr');

        rows.forEach(row => {
            const rowText = row.textContent.toLowerCase();
            const geomType = row.dataset.geometryType || '';

            const matchesQuery = !query || rowText.includes(query);
            const matchesType = selectedType === 'ALL' || geomType.includes(selectedType);

            row.style.display = matchesQuery && matchesType ? '' : 'none';
        });
    };

    searchInput.addEventListener('input', filterRows);
    filterSelect.addEventListener('change', filterRows);
}

function inspectProperties(featureId) {
    const feat = currentMeasurements.find(m => m.feature_id === featureId);
    if (!feat) return;

    document.getElementById('modalTitle').textContent = `Feature #${featureId} Properties (${feat.geometry_type})`;
    document.getElementById('modalContent').textContent = JSON.stringify(feat.properties || {}, null, 2);
    document.getElementById('propsModal').classList.add('open');
}

function closeModal() {
    document.getElementById('propsModal').classList.remove('open');
}

/* ==========================================================================
   7. Sample Dataset Quick-Loaders
   ========================================================================== */
async function loadSampleKml() {
    try {
        const kmlText = `<?xml version="1.0" encoding="UTF-8"?>
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
</kml>`;
        const blob = new Blob([kmlText], { type: 'application/vnd.google-earth.kml+xml' });
        const file = new File([blob], 'bengaluru_parks.kml', { type: 'application/vnd.google-earth.kml+xml' });
        handleSelectedFile(file);
    } catch (err) {
        console.error('Failed to load sample KML:', err);
    }
}

async function loadSampleShapefile() {
    try {
        // Fetch pre-generated sample from data directory if server exposes it, or notify
        const res = await fetch('/data/sample_data/berlin_parcels.zip');
        if (res.ok) {
            const blob = await res.blob();
            const file = new File([blob], 'berlin_parcels.zip', { type: 'application/zip' });
            handleSelectedFile(file);
            return;
        }
    } catch (e) {
        // Fallback
    }
    // Alternatively prompt user to pick from data/sample_data/
    document.getElementById('fileInput').click();
}

/* ==========================================================================
   8. Health Check & Recent Files History
   ========================================================================== */
async function checkApiHealth() {
    try {
        const res = await fetch('/api/health');
        const data = await res.json();
        if (data.status === 'online') {
            document.getElementById('apiStatusText').textContent = `API Online • DB ${data.database}`;
        }
    } catch (err) {
        document.getElementById('apiStatusText').textContent = 'API Offline';
    }
}

async function loadRecentFiles() {
    try {
        const res = await fetch('/api/files/?limit=6');
        if (!res.ok) return;

        const data = await res.json();
        const container = document.getElementById('recentFilesList');
        container.innerHTML = '';

        if (!data.items || data.items.length === 0) {
            container.innerHTML = `<div style="font-size: 0.85rem; color: var(--text-muted); grid-column: 1/-1;">No files uploaded yet. Upload a file above to begin.</div>`;
            return;
        }

        data.items.forEach(item => {
            const div = document.createElement('div');
            div.className = 'history-card';
            div.innerHTML = `
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 4px;">
                    <strong style="font-size: 0.85rem; color: var(--text-main);">${item.filename}</strong>
                    <span class="badge ${item.status === 'COMPLETED' ? 'badge-completed' : 'badge-unsupported'}">${item.status}</span>
                </div>
                <div style="font-size: 0.75rem; color: var(--text-muted);">
                    ${item.feature_count} features • ${item.file_type} • ${item.source_crs || 'EPSG:4326'}
                </div>
            `;
            div.addEventListener('click', () => {
                loadMeasurementsForFile(item.id);
            });
            container.appendChild(div);
        });
    } catch (err) {
        console.warn('Could not load recent files:', err);
    }
}
