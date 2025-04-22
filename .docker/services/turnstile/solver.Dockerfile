FROM python:3.13.3

# Prevent interactive prompts during package installs
ENV DEBIAN_FRONTEND=noninteractive

# Install xvfb
RUN apt-get update && apt-get install -y xvfb x11-apps

# Install requirements
RUN pip install patchright && \
    patchright install chromium --with-deps

WORKDIR /workspaceFolder
COPY . .
RUN pip install -r requirements.txt
RUN pip install .

WORKDIR /workspaceFolder/src/turnstile_solver
RUN echo '#!/bin/bash\n\
    xvfb-run --auto-servernum --server-args="-screen 0 1024x720x24" \\\n\
    python main.py \\\n\
    --browser-args "--no-sandbox --disable-dev-shm-usage --disable-setuid-sandbox --disable-software-rasterizer"\n\
    exec "$@"' > /workspaceFolder/entrypoint.sh && chmod +x /workspaceFolder/entrypoint.sh

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD xvfb-run --auto-servernum echo "Xvfb is working!" || exit 1

RUN chmod +x /workspaceFolder/entrypoint.sh
ENTRYPOINT [ "/workspaceFolder/entrypoint.sh" ]
