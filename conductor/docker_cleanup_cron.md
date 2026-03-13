# Docker Auto-Cleanup Setup

## Objective
Set up a daily background job to automatically clean up Docker build caches, unused images, and dangling volumes to prevent storage exhaustion on the VPS.

## Implementation Steps
1. Create a shell script at `/usr/local/bin/clean_docker.sh` with the following content:
   ```bash
   #!/bin/bash
   echo "Starting Docker cleanup at $(date)" >> /var/log/docker_cleanup.log
   /usr/bin/docker system prune -af --volumes >> /var/log/docker_cleanup.log 2>&1
   echo "Cleanup finished at $(date)" >> /var/log/docker_cleanup.log
   echo "-----------------------------------" >> /var/log/docker_cleanup.log
   ```
2. Make the script executable using `chmod +x /usr/local/bin/clean_docker.sh`.
3. Add a cron job for the `root` user to execute this script every day at 1:00 AM.

## Verification
- Verify the script exists and is executable.
- Run `sudo crontab -l` to ensure the cron job is correctly registered.
