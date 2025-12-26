# Add necessary USE flags for audio processing
sudo mkdir -p /etc/portage/package.use
echo "media-video/ffmpeg amr encode opus x264" | sudo tee -a /etc/portage/package.use/ffmpeg
# Install FFmpeg
sudo emerge media-video/ffmpeg

# Install Docker and Compose
sudo emerge app-containers/docker app-containers/docker-compose
# Enable and start the service
sudo systemctl enable --now docker
sudo usermod -aG docker gentoo  # Allows you to run docker without sudo

# Install git
sudo emerge acct-group/git

