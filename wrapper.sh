
mkdir -p ~/bin
cat > ~/bin/vlc-wrapper << 'EOF'
#!/bin/bash
exec "/mnt/c/Program Files/VideoLAN/VLC/vlc.exe" "$@"
EOF

# Make it executable
chmod +x ~/bin/vlc-wrapper

# Set this as the player
sed -i '/ANI_CLI_PLAYER/d' ~/.bashrc
echo 'export ANI_CLI_PLAYER="$HOME/bin/vlc-wrapper"' >> ~/.bashrc
source ~/.bashrc

# Test
ani-cli "sentenced to be a hero"
