#!/bin/bash
# Custom actions script for first boot and every boot tasks
# Place this script in user_fs/main/home/custom_actions.sh
# Ensure it is executable: chmod +x user_fs/main/home/custom_actions.sh

FLAG_FILE="/usr/local/custom_actions_done"

# ────────────────
# BLOCK: Only runs on first boot
# ────────────────
run_first_boot_tasks() {
    echo "Running initial setup..."

    # Create NATS JetStream storage dir with "nats" user access
    # This is storage_dir of /etc/nats-server.conf configuration file
    NATS_JETSTREAM_DIR="/data/jetstream"
    mkdir -p $NATS_JETSTREAM_DIR
    chown -R nats:nats $NATS_JETSTREAM_DIR
    chmod -R 755 $NATS_JETSTREAM_DIR

    # Create ascolab storage dir with "owasys" user access
    ASCOLAB_DIR="/data/ascolab"
    mkdir -p $ASCOLAB_DIR
    chown -R owasys:owasys $ASCOLAB_DIR
    chmod -R 755 $ASCOLAB_DIR

    # Create the marker file to prevent running again
    touch "$FLAG_FILE"

    echo "Initial setup completed."
}

# ────────────────
# BLOCK: Runs on every boot
# ────────────────
run_always_tasks() {
    echo "Running tasks on every boot..."
    # Put here the commands that must always run
}

# ────────────────
# MAIN LOGIC
# ────────────────
if [ ! -f "$FLAG_FILE" ]; then
    run_first_boot_tasks
fi

run_always_tasks
