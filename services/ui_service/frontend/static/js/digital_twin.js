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

        let modelState = {}; // Local cache for the model's state

        // Helper to set a value in a nested object based on a path array
        function setNestedValue(obj, path, value) {
            let schema = obj;
            for (let i = 0; i < path.length - 1; i++) {
                const key = path[i];
                if (!schema[key]) {
                    schema[key] = {};
                }
                schema = schema[key];
            }
            schema[path[path.length - 1]] = value;
        }

        function drawModel() {
            if (!modelState || Object.keys(modelState).length === 0) {
                return; // Don't draw if state is empty
            }

            const traces = [];
            // This part of the logic remains similar, but it reads from `modelState`
            for (const partName in modelState) {
                if (!modelState[partName]) continue;
                
                if (modelState[partName]['plan']) {
                    const plan = modelState[partName]['plan'];
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
                            // Etc...
                            i: [0, 0, 0, 0, 3, 3, 4, 4],
                            j: [1, 2, 1, 5, 2, 6, 5, 6],
                            k: [2, 3, 5, 4, 6, 7, 6, 7],
                            type: 'mesh3d',
                            opacity: 0.8,
                            showscale: false,
                            name: partName + "Plan"
                        };
                        traces.push(p);
                    }
                }

                if (modelState[partName]['points']) {
                    const part = modelState[partName]['points'];
                    const x = part.map(p => p[0]);
                    const y = part.map(p => p[1]);
                    const z = part.map(p => p[2]);

                    traces.push({
                        x: x, y: y, z: z,
                        mode: 'lines+markers', type: 'scatter3d', name: partName
                    });
                }
            }
            traces.push(boundingPoints[0]);
            Plotly.react(digitalTwinContainer, traces, layout);
        }

        // Debounce the drawing function to avoid excessive re-renders
        const debouncedDrawModel = _.debounce(drawModel, 100);

        ConnectionManager.subscribe('digital_twin.data.>', (m) => {
            const subjectParts = m.subject.split('.');
            // Remove "digital_twin" and "data" from the path
            const path = subjectParts.slice(2);

            const data = ConnectionManager.jsonCodec.decode(m.data);
            const value = data.value;

            setNestedValue(modelState, path, value);
            debouncedDrawModel();

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
