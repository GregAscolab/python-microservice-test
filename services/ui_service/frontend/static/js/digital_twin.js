import ConnectionManager from './connection_manager.js';

let digitalTwinSub;
const digitalTwinContainer = document.getElementById('digital-twin-container');
const boundingPoints = [{
    x: [-10, 20],
    y: [-10, 10],
    z: [-10, 20],
    mode: 'lines+markers',
    type: 'scatter3d',
    name: "bounds",
    opacity: 0,
    showlegend: false
}];
const initLayout = {
    margin: { l: 0, r: 0, b: 0, t: 0 },
    scene: {
        xaxis: { title: 'X' },
        yaxis: { title: 'Y' },
        zaxis: { title: 'Z' },
        aspectmode: 'data',
        // aspectratio:{x:1, y:1, z:1},
        camera: {
            up: { x: 0, y: 0, z: 1 },
            // center:{x:0,y:0,z:0},
            eye: { x: 0, y: 3, z: 0 }
        }
    }
}
const layout = initLayout;

function initDigitalTwinsPage() {
    console.log("Initializing Digital Twin page...");

    if (digitalTwinContainer) {
        Plotly.newPlot(digitalTwinContainer, boundingPoints, layout);

        ConnectionManager.subscribe('digital_twin.data', (m) => {
            const data = ConnectionManager.jsonCodec.decode(m.data);
            // console.log("Received digital twin data:", data);

            let camera;

            const traces = [];
            for (const partName in data) {
                const part = data[partName]['points'];
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

                const plan = data[partName]['plan'];
                if (plan.length > 0) {
                    // console.log("plan=", plan)
                    const xp = plan.map(p => p[0]);
                    const yp = plan.map(p => p[1]);
                    const zp = plan.map(p => p[2]);

                    const p = {
                        x: xp,
                        y: yp,
                        z: zp,
                        // Utiliser les indices des sommets pour définir les triangles de la surface.
                        // Le plan est un quadrilatère, donc nous avons besoin de deux triangles.
                        // triangle 1: points 0, 1, 2
                        // triangle 2: points 0, 2, 3
                        i: [0, 0],
                        j: [1, 2],
                        k: [2, 3],
                        type: 'mesh3d',
                        opacity: 0.8,
                        showscale: false,
                        name: partName + "Plan"
                    };
                    traces.push(p);
                }
            }
            traces.push(boundingPoints[0]); // Add invisible bounding points for autoscale

            // layout = digitalTwinContainer.layout;
            Plotly.react(digitalTwinContainer, traces, layout);

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
