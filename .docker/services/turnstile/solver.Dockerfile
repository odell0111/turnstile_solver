FROM python:3.13.3

# Prevent interactive prompts during package installs
ENV DEBIAN_FRONTEND=noninteractive
ENV DISPLAY=:99

# Install xvfb and VNC server
RUN apt-get update && apt-get install -y \
    xvfb \
    fluxbox \
    x11vnc \
    supervisor \
    x11-utils \
    --no-install-recommends \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install requirements
RUN pip install patchright && \
    patchright install chromium --with-deps

WORKDIR /workspaceFolder
COPY . .
RUN pip install -r requirements.txt
RUN pip install .

WORKDIR /workspaceFolder/src/turnstile_solver
# RUN echo '#!/bin/bash\n\
#     # Start Xvfb (virtual display) \\\n\
#     Xvfb :99 -screen 0 1024x768x16 & \\\n\
#     # Start window manager \\\n\
#     fluxbox & \\\n\
#     # Start VNC server \\\n\
#     # x11vnc -display :99 -forever -nopw -shared -bg \\\n\
#     x11vnc -display :99 -forever -nopw -shared -listen 0.0.0.0 -rfbport 5900 -bg \\\n\
#     # Export DISPLAY for Playwright to use \\\n\
#     export DISPLAY=:99 \\\n\
#     # Start resolver \\\n\
#     python main.py \\\n\
#     --browser-args "--no-sandbox --disable-gpu --disable-software-rasterizer --disable-dev-shm-usage --disable-setuid-sandbox --start-maximized --disable-blink-features=AutomationControlled --lang=en-US,en --window-size=1024,720 --enable-unsafe-webgpu --enable-webgl --use-gl=swiftshader --enable-features=SharedArrayBuffer,TrustTokens,PrivateNetworkAccessChecksBypassingPermissionPolicy"\n\
#     exec "$@"' > /workspaceFolder/entrypoint.sh && chmod +x /workspaceFolder/entrypoint.sh

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD xvfb-run --auto-servernum echo "Xvfb is working!" || exit 1

# VNC port
EXPOSE 5900

RUN chmod +x /workspaceFolder/.docker/services/turnstile/entrypoint.sh
ENTRYPOINT [ "/workspaceFolder/.docker/services/turnstile/entrypoint.sh" ]
