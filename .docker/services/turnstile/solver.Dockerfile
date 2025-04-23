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

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD xvfb-run --auto-servernum echo "Xvfb is working!" || exit 1

# VNC port
EXPOSE 5900

RUN chmod +x /workspaceFolder/.docker/services/turnstile/entrypoint.sh
ENTRYPOINT [ "/workspaceFolder/.docker/services/turnstile/entrypoint.sh" ]
