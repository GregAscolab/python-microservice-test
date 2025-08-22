document.addEventListener('DOMContentLoaded', function() {
    const nats = window.nats;
    const dummyDataElement = document.getElementById('dummy-data');
    const resetButton = document.getElementById('reset-dummy-counter');

    // 1. Subscribe to the data subject from our dummy service
    nats.subscribe('dummy.data', (msg) => {
        const data = JSON.parse(new TextDecoder().decode(msg.data));
        dummyDataElement.textContent = JSON.stringify(data, null, 2);
    });

    // 2. Add a click listener for our reset button
    resetButton.addEventListener('click', () => {
        // Construct the command payload
        const command = {
            command: 'reset_counter'
            // No arguments needed for this command
        };
        // Publish the command to the dummy service's command subject
        nats.publish('commands.dummy_service', JSON.stringify(command));
        console.log('Sent reset_counter command to dummy_service');
    });
});
