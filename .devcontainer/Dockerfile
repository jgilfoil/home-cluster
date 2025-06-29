# Base image using Debian
FROM mcr.microsoft.com/devcontainers/base:debian

# Install fish shell and other required packages
RUN apt-get update && apt-get install -y \
    fish \
    curl \
    python3 \
    python3-pip \
    python3-venv \
    git \
    jq \
    direnv \
    fzf \
    build-essential \
    python3-dev \
    libffi-dev \
    libssl-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install ssh client
RUN apt-get update && apt-get install -y openssh-client && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


# Install kubectl
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && \
    chmod +x kubectl && \
    mv kubectl /usr/local/bin/

# Set fish as the default shell
ENV SHELL=/usr/bin/fish

# Install task (taskfile.dev)
RUN sh -c "$(curl --location https://taskfile.dev/install.sh)" -- -d -b /usr/local/bin

# Install k9s (Kubernetes CLI)
RUN curl -LO "https://github.com/derailed/k9s/releases/download/v0.32.4/k9s_Linux_amd64.tar.gz" && \
    tar -xzf k9s_Linux_amd64.tar.gz && \
    mv k9s /usr/local/bin/ && \
    rm k9s_Linux_amd64.tar.gz

# Install Flux CLI (version 2.4.0)
RUN curl -s https://fluxcd.io/install.sh | sudo FLUX_VERSION=2.4.0 bash

# Install SOPS (Secrets OPerationS)
# Get the latest version from https://github.com/getsops/sops/releases
# As of last check, v3.10.2 was the latest.
RUN curl -L "https://github.com/getsops/sops/releases/download/v3.10.2/sops-v3.10.2.linux.amd64" -o /usr/local/bin/sops && \
    chmod +x /usr/local/bin/sops

# Create directory for binary tools
RUN mkdir -p /workspaces/home-cluster/.bin

# Set environment variables
ENV PATH="/workspaces/home-cluster/.bin:${PATH}"