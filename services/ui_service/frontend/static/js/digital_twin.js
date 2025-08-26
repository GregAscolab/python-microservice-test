import ConnectionManager from './connection_manager.js';

let digitalTwinSub;

function initDigitalTwinsPage() {
    console.log("Initializing Digital Twin page...");
    const digitalTwinContainer = document.getElementById('digital-twin-container');

    if (digitalTwinContainer) {
        Plotly.newPlot('digital-twin-container', [], {
            margin: { l: 0, r: 0, b: 0, t: 0 },
            scene: {
                xaxis: { title: 'X', range: [-10, 10] },
                yaxis: { title: 'Y', range: [-10, 10] },
                zaxis: { title: 'Z', range: [0, 10] },
                aspectratio: { x: 1, y: 1, z: 1 }
            }
        });

        ConnectionManager.subscribe('digital_twin.data', (m) => {
            const data = ConnectionManager.jsonCodec.decode(m.data);
            console.log("Received digital twin data:", data);

            const traces = [];
            for (const partName in data) {
                const part = data[partName];
                const x = part.map(p => p[0]);
                const y = part.map(p => p[1]);
                const z = part.map(p => p[2]);

                traces.push({
                    x: x,
                    y: y,
                    z: z,
                    mode: 'lines+markers',
                    type: 'scatter3d',
                    name: partName
                });
            }

            Plotly.react('digital-twin-container', traces, {
                margin: { l: 0, r: 0, b: 0, t: 0 },
                scene: {
                    xaxis: { title: 'X', range: [-10, 10] },
                    yaxis: { title: 'Y', range: [-10, 10] },
                    zaxis: { title: 'Z', range: [0, 10] },
                    aspectratio: { x: 1, y: 1, z: 1 }
                }
            });
        }).then(sub => {
            digitalTwinSub = sub;
        });
    }
}

function cleanupDigitalTwinsPage() {
    console.log("Cleaning up Digital Twin page...");
    if (digitalTwinSub) {
        digitalTwinSub.unsubscribe();
        digitalTwinSub = null;
    }
}

window.initDigitalTwinsPage = initDigitalTwinsPage;
window.cleanupDigitalTwinsPage = cleanupDigitalTwinsPage;
