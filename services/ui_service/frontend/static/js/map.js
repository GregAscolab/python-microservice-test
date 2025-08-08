// Map JavaScript


// Initialiser la carte Leaflet
        var map = L.map('map');
        let userInteractedWithMap = false;
        let currentUirevision = 1;

        // Ajouter une couche de tuiles par défaut (Plan)
        var osmLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);

        // Ajouter une couche de tuiles satellite
        var satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
        });

        // Données GeoJSON initiales
        var geojsonData = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "name": "Tour Eiffel",
                        "description": "Un monument emblématique de Paris",
                        "hardness": {"value": 123.56, "unit": "MPa"},
                        "material": "Métal",
                        "altitude": 300
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": [2.2945, 48.8584]
                    }
                },
                {
                    "type": "Feature",
                    "properties": {
                        "name": "Louvre",
                        "description": "Un des plus grands musées du monde",
                        "hardness": {"value": 220.0, "unit": "MPa"},
                        "material": "Craie",
                        "altitude": 50
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": [2.3376, 48.8606]
                    }
                },
                {
                    "type": "Feature",
                    "properties": {
                        "name": "Notre-Dame",
                        "description": "Cathédrale historique",
                        "hardness": {"value": 200.0, "unit": "MPa"},
                        "material": "Pierre",
                        "altitude": 100
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": [2.3499, 48.8529]
                    }
                },
                {
                    "type": "Feature",
                    "properties": {
                        "name": "Arc de Triomphe",
                        "description": "Monument emblématique",
                        "hardness": {"value": 180.0, "unit": "MPa"},
                        "material": "Pierre",
                        "altitude": 70
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": [2.2950, 48.8739]
                    }
                },
                {
                    "type": "Feature",
                    "properties": {
                        "name": "Sacré-Cœur",
                        "description": "Basilique emblématique",
                        "hardness": {"value": 150.0, "unit": "MPa"},
                        "material": "Pierre",
                        "altitude": 130
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": [2.3431, 48.8867]
                    }
                }
            ]
        };

        // Stocker les marqueurs pour un accès facile plus tard
        var markers = [];
        var geoJsonLayer; // Variable globale pour la couche GeoJSON

        // Fonction pour obtenir la couleur en fonction de la dureté
        function getColor(value) {
            var maxHardness = 300;
            var intensity = value / maxHardness;
            var red = Math.floor(intensity * 255);
            var green = Math.floor(255 * (1 - intensity));
            return `rgb(${red}, ${green}, 0)`;
        }

        // Fonction pour convertir les coordonnées GPS en ECEF
        function convertToECEF(lat, lon, alt) {
            var a = 6378137.0; // Demi-grand axe de l'ellipsoïde terrestre
            var e = 0.00669437999014; // Carré de la première excentricité

            let latRad = lat * Math.PI / 180;
            let lonRad = lon * Math.PI / 180;
            let sinLat = Math.sin(latRad);
            let cosLat = Math.cos(latRad);
            let sinLon = Math.sin(lonRad);
            let cosLon = Math.cos(lonRad);

            // Rayon de courbure dans le plan du méridien
            let RN = a / Math.sqrt(1 - e * Math.pow(sinLat, 2));

            var x = (RN + alt) * cosLat * cosLon;
            var y = (RN + alt) * cosLat * sinLon;
            var z = ((RN * (1 - e)) + alt) * sinLat;

            return { x: x, y: y, z: z };
        }

        // Fonction pour calculer le centre des points
        function calculateCenter(markers) {
            let totalLat = 0, totalLon = 0, count = markers.length;
            markers.forEach(function(marker) {
                totalLat += marker.coordinates[1];
                totalLon += marker.coordinates[0];
            });

            let centerLat = totalLat / count;
            let centerLon = totalLon / count;

            // Calculer la moyenne des altitudes
            let totalAlt = 0;
            markers.forEach(function(marker) {
                totalAlt += marker.altitude;
            });
            let centerAlt = totalAlt / count;

            return { lat: centerLat, lon: centerLon, alt: centerAlt };
        }

        // Fonction pour convertir les coordonnées ECEF en ENU
        function convertECEFtoENU(x, y, z, x_ref, y_ref, z_ref, lat_ref, lon_ref) {
            let latRad = lat_ref * Math.PI / 180;
            let lonRad = lon_ref * Math.PI / 180;

            let sinLat = Math.sin(latRad);
            let cosLat = Math.cos(latRad);
            let sinLon = Math.sin(lonRad);
            let cosLon = Math.cos(lonRad);

            let dx = x - x_ref;
            let dy = y - y_ref;
            let dz = z - z_ref;

            let east = -sinLon * dx + cosLon * dy;
            let north = -cosLon * sinLat * dx - sinLat * sinLon * dy + cosLat * dz;
            let up = cosLat * cosLon * dx + cosLat * sinLon * dy + sinLat * dz;

            return { east: east, north: north, up: up };
        }

        // Ajouter les données GeoJSON à la carte Leaflet
        function addGeoJsonToMap() {
            if (geoJsonLayer) {
                map.removeLayer(geoJsonLayer);
            }

            geoJsonLayer = L.geoJSON(geojsonData, {
                pointToLayer: function(feature, latlng) {
                    var circle = L.circleMarker(latlng, {
                        radius: 8,
                        fillColor: getColor(feature.properties.hardness.value),
                        color: "#000",
                        weight: 1,
                        opacity: 1,
                        fillOpacity: 0.8
                    });

                    return circle;
                },
                onEachFeature: function(feature, layer) {
                    layer.bindPopup(`
                        <b>Matériel:</b> ${feature.properties.material}<br>
                        <b>Dureté:</b> ${feature.properties.hardness.value} ${feature.properties.hardness.unit}<br>
                        <b>Altitude:</b> ${feature.properties.altitude} mètres
                    `);
                }
            }).addTo(map);

            // Mettre à jour la liste des marqueurs
            markers = [];
            geojsonData.features.forEach(function(feature) {
                var latlng = L.latLng(feature.geometry.coordinates[1], feature.geometry.coordinates[0]);
                var circle = L.circleMarker(latlng, {
                    radius: 8,
                    fillColor: getColor(feature.properties.hardness.value),
                    color: "#000",
                    weight: 1,
                    opacity: 1,
                    fillOpacity: 0.8
                });

                markers.push({
                    circle: circle,
                    hardnessValue: feature.properties.hardness.value + ' ' + feature.properties.hardness.unit,
                    position: latlng,
                    coordinates: feature.geometry.coordinates,
                    hardness: feature.properties.hardness.value,
                    altitude: feature.properties.altitude
                });
            });

            // Rafraîchir la carte pour inclure tous les points
            if (!userInteractedWithMap) {
                fitMapToMarkers();
            }
        }

        // Ajuster la vue de la carte pour inclure tous les marqueurs
        function fitMapToMarkers() {
            var bounds = [];
            markers.forEach(function(marker) {
                bounds.push(marker.position);
            });
            if (bounds.length > 0) {
                map.fitBounds(L.featureGroup(bounds.map(latlng => L.marker(latlng))).getBounds().pad(0.5));
            }
        }

        // Rafraîchir le graphique Plotly avec les nouvelles données
        function refreshPlotlyPlot() {
            let centerGeo = calculateCenter(markers);
            let centerECEF = convertToECEF(centerGeo.lat, centerGeo.lon, centerGeo.alt);

            var traceData = {
                x: [],
                y: [],
                z: [],
                mode: 'markers',
                marker: {
                    size: 6,
                    color: []
                },
                opacity: 0.8,
                type: 'scatter3d',
                text: []
            };

            markers.forEach(function(marker) {
                let ecef = convertToECEF(marker.coordinates[1], marker.coordinates[0], marker.altitude);
                let enu = convertECEFtoENU(ecef.x, ecef.y, ecef.z, centerECEF.x, centerECEF.y, centerECEF.z, centerGeo.lat, centerGeo.lon);

                traceData.x.push(enu.east);
                traceData.y.push(enu.north);
                traceData.z.push(enu.up);

                var colorString = getColor(marker.hardness);
                var rgbValues = colorString.match(/\d+/g).map(Number);
                traceData.marker.color.push(`rgb(${rgbValues[0]}, ${rgbValues[1]}, ${rgbValues[2]})`);
                traceData.text.push(marker.circle.options.hardnessValue);
            });

            var layout = {
                title: 'Visualisation 3D des Points d\'Intérêt (ENU)',
                autosize: true,
                height:500,
                scene: {
                    aspectmode:'manual',
		            aspectratio: {x:1, y:1, z:1},
                    xaxis: { title: {text:'East (m)'}, autorange: true },
                    yaxis: { title: {text:'North (m)'}, autorange: true },
                    zaxis: { title: {text:'Up (m)'}, autorange: true },
                    camera: {
                        eye: {x: 0.1, y: -2, z: 0.1}
                    }
                },
                uirevision:currentUirevision,
                margin: {
                    l: 0,
                    r: 0,
                    b: 5,
                    t: 5
                }
            };

            const config = {responsive: true}

            Plotly.react('plotly-3Dgraph', [traceData], layout, config);
        }

        // Fonction pour ajouter un nouveau point aléatoire aux données GeoJSON
        function addRandomPointToGeoJson() {
            // Générer des coordonnées aléatoires autour de Paris
            let randomLon = 2.35 + (Math.random() - 0.5) * 0.1;
            let randomLat = 48.85 + (Math.random() - 0.5) * 0.1;
            let randomAlt = Math.random() * 200; // Altitude aléatoire entre 0 et 200m
            let randomHardness = Math.random() * 300; // Dureté aléatoire entre 0 et 300 MPa
            let randomMaterial = ["Métal", "Pierre", "Béton", "Craie"][Math.floor(Math.random() * 4)];

            let newFeature = {
                "type": "Feature",
                "properties": {
                    "name": "Nouveau Point",
                    "description": "Point ajouté dynamiquement",
                    "hardness": {"value": randomHardness, "unit": "MPa"},
                    "material": randomMaterial,
                    "altitude": randomAlt
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [randomLon, randomLat]
                }
            };

            geojsonData.features.push(newFeature);
            addGeoJsonToMap();
            refreshPlotlyPlot();
        }

        // Initialiser les contrôles pour la carte Leaflet
        document.getElementById('toggleHardness').addEventListener('change', function(e) {
            var showHardness = e.target.checked;
            markers.forEach(function(marker) {
                if (marker.label) {
                    map.removeLayer(marker.label);
                    marker.label = null;
                }
                if (showHardness) {
                    marker.label = L.marker(marker.position, {
                        icon: L.divIcon({
                            className: 'hardness-label',
                            html: `<div style="background: white; padding: 2px 5px; border-radius: 3px; border: 1px solid #ccc;">${marker.hardnessValue}</div>`,
                            iconSize: null
                        })
                    }).addTo(map);
                }
            });
        });

        document.getElementById('mapType').addEventListener('change', function(e) {
            var mapType = e.target.value;
            if (mapType === 'plan') {
                map.removeLayer(satelliteLayer);
                osmLayer.addTo(map);
            } else {
                map.removeLayer(osmLayer);
                satelliteLayer.addTo(map);
            }
        });

        map.on('moveend zoomend', function() {
            userInteractedWithMap = true;
            console.log("Map move");
        });

        document.getElementById('resetMapView').addEventListener('click', function() {
            fitMapToMarkers();
            userInteractedWithMap = false;
        });

        // document.getElementById('resetPlotView').addEventListener('click', function() {
        //     // Logique pour recalculer la vue optimale pour le 3D
        //     refreshPlotlyPlot();
        // });

        // Initialiser la carte avec les données GeoJSON
        addGeoJsonToMap();

        // Activer l'affichage des valeurs de dureté par défaut
        // document.getElementById('toggleHardness').dispatchEvent(new Event('change'));

        // Init 3D chart
        refreshPlotlyPlot();

         // Rafraîchir les données toutes les 2 secondes
        setInterval(addRandomPointToGeoJson, 5000);
