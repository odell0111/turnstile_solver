#!/bin/bash

# Start Xvfb
Xvfb :99 -screen 0 1024x768x16 &
XVFB_PID=$!

# Wait for Xvfb to become ready
for i in {1..10}; do
    if xdpyinfo -display :99 >/dev/null 2>&1; then
        echo "Xvfb is ready!"
        break
    fi
    echo "Waiting for Xvfb to start..."
    sleep 1
done

# If it's not ready after 10s, bail
if ! xdpyinfo -display :99 >/dev/null 2>&1; then
    echo "Xvfb did not start!"
    exit 1
fi

# Start window manager
fluxbox &

# Start VNC server
x11vnc -display :99 -forever -nopw -shared -listen 0.0.0.0 -rfbport 5901 -bg

# Run your app
export DISPLAY=:99
exec python main.py --browser-args "--no-sandbox --disable-gpu --disable-software-rasterizer --disable-dev-shm-usage --disable-setuid-sandbox --start-maximized --disable-blink-features=AutomationControlled --lang=en-US,en --window-size=1024,720 --enable-unsafe-webgpu --enable-webgl --use-gl=swiftshader --enable-features=SharedArrayBuffer,TrustTokens,PrivateNetworkAccessChecksBypassingPermissionPolicy"
