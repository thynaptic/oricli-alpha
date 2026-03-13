#!/bin/bash
# Oricli-Alpha Storage Sync Utility
# Syncs local models and training data to Blaze B2

REMOTE="blaze_b2:Oricli-Alpha-Alpha"
LOCAL_MODELS="/home/mike/Oricli-Alpha/models/neural_text_generator_remote"

usage() {
    echo "Usage: $0 {push|pull|status}"
    echo "  push: Sync LOCAL to REMOTE (updates B2 with new local data)"
    echo "  pull: Sync REMOTE to LOCAL (updates local with B2 data)"
    echo "  status: Show differences between local and remote"
    exit 1
}

case "$1" in
    push)
        echo "Pushing local changes to B2..."
        rclone sync "$LOCAL_MODELS" "$REMOTE/models/neural_text_generator_remote" --progress
        ;;
    pull)
        echo "Pulling remote changes from B2..."
        rclone sync "$REMOTE/models/neural_text_generator_remote" "$LOCAL_MODELS" --progress
        ;;
    status)
        echo "Checking storage status..."
        rclone check "$LOCAL_MODELS" "$REMOTE/models/neural_text_generator_remote" --one-way
        ;;
    *)
        usage
        ;;
esac
