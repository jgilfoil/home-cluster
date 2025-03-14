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

# Set fish as the default shell
ENV SHELL=/usr/bin/fish

# Install task (taskfile.dev)
RUN sh -c "$(curl --location https://taskfile.dev/install.sh)" -- -d -b /usr/local/bin

# Install k9s (Kubernetes CLI)
RUN curl -LO "https://github.com/derailed/k9s/releases/download/v0.32.4/k9s_Linux_amd64.tar.gz" && \
    tar -xzf k9s_Linux_amd64.tar.gz && \
    mv k9s /usr/local/bin/ && \
    rm k9s_Linux_amd64.tar.gz

# Create directory for binary tools
RUN mkdir -p /workspaces/home-cluster/.bin

# Set environment variables
ENV PATH="/workspaces/home-cluster/.bin:${PATH}"