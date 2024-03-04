<div align="center">
  <img src="images/banner.png" alt="Home Kubernetes Cluster Banner">
  
  # My Home Kubernetes
  
<!-- k3s_version_badge_start -->
[![k3s version](https://img.shields.io/badge/k3s-v1.29.1%2Bk3s2-blue?style=for-the-badge&logo=kubernetes&logoColor=white)](https://k3s.io/)
<!-- k3s_version_badge_end -->
</div>

##

This repository manages my Home Kubernetes Cluster. 

This is iteration ~2.0 of my home cluster. You can see my previous iteration, archived [here](https://github.com/jgilfoil/k8s-gitops). One of my main goals for this evolution is to leverage as much automation as possible to remove overhead and maintenance tasks required to maintain this, even as I add more applications.

Inspired and based on [onedr0p's cluster template](https://github.com/onedr0p/cluster-template).

## Applications
All of the below infrastructure and suporting services combine to provide a platform to run these services in a seamless manner. More to come soon.
- **Plex:** Media server to organize and stream multimedia collections accessible from various devices.
- **Overseerr:** Request management tool for users to request new media content, integrating with Plex and feeds into the *arr workflow.
- **Prowlarr:** Indexer manager that coordinates with download clients and media servers like Sonarr and Radarr for content retrieval indexing.
- **Radarr:** Automated movie downloading and organization tool that integrates with download clients.
- **Sonarr:** Automates downloading and organization of TV show episodes, working with various download clients.
- **Transmission:** BitTorrent client used for downloading media files, integrated with Sonarr, Radarr, and Prowlarr.
- **MyMindInAI:** Custom software toolkit that provides various internal facing tools for a small business, such as a discordbot.

## Hardware

| Device Purpose    | Quantity | Model            | Processor           | Memory | Storage             |
|-------------------|----------|------------------|---------------------|--------|---------------------|
| K3s Nodes         | 3        | Odroid-H2        | Intel J4105, 2.5GHz | 32GB   | 256GB NVMe, 1TB SSD |
| DNS Servers       | 2        | Odroid-C4        | ARM Amlogic S905X3  | 4GB    | 16GB                |
| Network Switch    | 1        | Unifi USW-16-POE | -                   | -      | -                   |
| NAS Backups/Media | 1        | Synology DS1520+ | Intel Celeron J4125 | 8GB    | 25TB                |

## Cluster Support Services Overview

- **Kubernetes Distribution:** [Rancher k3s](https://k3s.io/)
- **GitOps Tooling:** [Flux](https://fluxcd.io/), [Renovatebot](https://github.com/renovatebot/renovate/)
- **Networking:** [Cilium CNI](https://cilium.io/), [Ingress-Nginx](https://kubernetes.github.io/ingress-nginx/), [K8s-gateway](https://github.com/ori-edge/k8s_gateway), [Kube-Vip](https://kube-vip.io/)
- **Security:** [Cert-Manager](https://cert-manager.io/), [Cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/) tunnel, [pod-gateway](https://github.com/k8s-at-home/pod-gateway) with VPN
- **Storage:** [Rook-Ceph](https://rook.io/), [Volsync](https://volsync.readthedocs.io/), [openEBS](https://openebs.io/), [MinIO](https://min.io/) backed by NFS Volume
- **Monitoring:** [kube-prometheus-stack](https://github.com/prometheus-operator/kube-prometheus), [Grafana](https://grafana.com/), [metrics-server](https://github.com/kubernetes-sigs/metrics-server), [Hubble](https://cilium.io/blog/2019/04/24/hubble)
- **Maintenance & Upgrades:** [system-upgrade-controller](https://github.com/rancher/system-upgrade-controller), [kured](https://github.com/weaveworks/kured)
- **Optimization:** [reloader](https://github.com/stakater/Reloader), [descheduler](https://github.com/kubernetes-sigs/descheduler), [node-feature-discovery](https://github.com/kubernetes-sigs/node-feature-discovery), [intel-gpu-device-plugins](https://github.com/intel/intel-device-plugins-for-kubernetes)

## Detailed Inventory

### Automation

- **Flux:** Automates deployment and management, ensuring the cluster state matches the defined configurations in this repo.
- **Renovatebot:** Automatically updates software dependencies, keeping the cluster components current.
- **Kured:** Automatically drains and reboots nodes one at a time, when OS patches require a reboot.
- **System Upgrade Controller:** Automatically upgrades k3s when Renovatebot detects new versions and updates the variable for `KUBE_VERSION`.

### Networking
The network currently utilizes a flat, single-subnet design. Will transition to Vlans in the future during a network refresh.Local network DNS resolution outside the cluster, is handled by ODROID-C4 servers running BIND and dnsdist, directing domain requests to the k8s-gateway within the local network.

- **Cilium CNI:** Provides advanced networking, security, and load balancing for the cluster, enhancing network performance and security.
- **CoreDNS:** DNS server that runs as a Kubernetes service and provides DNS resolution for services and pods, as well as service discovery.
- **Ingress-Nginx:** Running two nginx ingresses, on to manage services internal to the network, an another to manage external services that route in from cloudflare.
- **K8s-gateway:** CoreDNS plugin that allows services on the local network to resolve service's Load Balanced addresses, via the local network's dnsdist proxy, running on the physical DNS servers, which points at k8s-gateway.
- **Cloudflared:** Sets up a tunnel for external services, enabling secured ingress access through Cloudflare's WAF.
- **VPN (Pod-gateway):** Establishes VPN and routes traffic for designated services outbound.
- **Cert-Manager:** Automates the management and issuance of wildcard SSL certificates, securing service communications.
- **Kube-Vip:** Provides a virtual IP address for the Kubernetes control plane, ensuring high availability and load balancing for cluster access.

### Storage

- **Rook-Ceph:** Provides low-latency Persistent Volume storage across the cluster for databases, configuration or other small volumes, utilizing local SSDs.
- **NFS:** The Synology, serves as the primary storage for media and backup solutions for the cluster and other home systems.
- **Volsync:** Provides data replication and backup for Rook-Ceph RBD PVCs, backups up to the NFS on Synology.
- **OpenEBS:** Used in my cluster to provide local host path Persistent Volumes for cache and other emphemeral needs.

### Monitoring and Alerts

- **Kube-Prometheus-Stack:** Provides comprehensive monitoring capabilities across the cluster.
- **Grafana:** Visualizes monitoring data and offers customizable dashboards.
- **metrics-server:** Aggregates resource usage data across the cluster.
- **Hubble:** Provides visibility into network traffic and security policies.

### Optimization

  - **Reloader:** Dynamically updates pods when linked ConfigMaps or Secrets change.
  - **Descheduler:** Optimizes pod distribution by evicting less ideally placed pods based on predefined policies.
  - **Node-feature-discovery:** Identifies and labels node capabilities, aiding in intelligent workload scheduling to leverage node-specific features efficiently.
  - **Intel GPU Device Plugin:** Enables hardware transcoding in Plex, utilizing the integrated GPUs in the Intel CPUs.


Big shoutout to the Home Operations Community on [discord](https://discord.gg/Yv2gzFy) (formerly k8s-at-home). Without their efforts and contributions to the ecosystem, this would not be possible.