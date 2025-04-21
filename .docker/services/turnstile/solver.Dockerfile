FROM python:3.13.3

# Prevent interactive prompts during package installs
ENV DEBIAN_FRONTEND=noninteractive

# Install requirements
RUN pip install playwright && \
    playwright install chromium --with-deps

WORKDIR /workspaceFolder
COPY . .
RUN pip install -r requirements.txt
RUN pip install .

WORKDIR /workspaceFolder/src/turnstile_solver
RUN echo '#!/bin/bash\n\
    python main.py --headless\n\
    exec "$@"' > /workspaceFolder/entrypoint.sh

RUN chmod +x /workspaceFolder/entrypoint.sh
ENTRYPOINT [ "/workspaceFolder/entrypoint.sh" ]