# CoreDNS Migration to Flux Managed Helm Install

This README outlines the steps required to migrate CoreDNS from the bootstrap version managed by k3s to a Flux managed Helm installation. After the initial deployment of the cluster, coredns will have been installed from /var/lib/rancher/k3s/server/manifests/coredns.yaml owing to the fact that flux can't operate without dns working in the cluster. However there are differences between the initial version and the version here in the flux repo, and in order to work around those we must follow the below steps.

This migration involves deleting the existing CoreDNS deployment and reinstalling it using Helm with Flux taking over the management.

## Preperation
Extract the values from the existing CoreDNS HelmRelease (located typically in `kubernetes/apps/kube-system/coredns/app/helmrelease.yaml`) and save them temporarily in a values.yaml file.

## Migration Steps

### 1. Delete the Bootstrap CoreDNS

Run the following command to delete the bootstrapped CoreDNS deployment:

```bash
kubectl delete -f /var/lib/rancher/k3s/server/manifests/coredns.yaml
```
### 2. Remove CoreDNS Manifest
Delete the coredns.yaml manifest file from each node in the cluster:

```bash
rm /var/lib/rancher/k3s/server/manifests/coredns.yaml
```

### 3. Helm Chart Installation
Install the CoreDNS Helm chart with the version specified in the HelmRelease file. Replace 1.29.0 with the current version in your HelmRelease file.

```bash
helm install coredns coredns/coredns \
  --version 1.29.0 \ # Replace with the current version
  --namespace kube-system \
  --values values.yaml
```
### 4. Update Kustomization for Flux
Modify the kustomization.yaml to include the CoreDNS kustomization.

`kubernetes/apps/kube-system/kustomization.yaml`  

This will trigger the deployment of coredns from flux. This ensures that Flux takes over the management of the Helm install.

### 5. Disable CoreDNS in k3s
Modify `/etc/rancher/k3s/config.yaml` to add the following line for coredns, otherwise coredns will be overwritten by the k3s config the next time there's an update.

```yaml
disable:
- flannel
- local-storage
- metrics-server
- servicelb
- traefik
- coredns # Add this line
```
## Verification
To verify that CoreDNS has been successfully migrated and is managed by Flux, check the HelmRelease status:

```bash
kubectl get helmrelease -n kube-system
```
You should see CoreDNS listed with the correct version and status indicating successful deployment.

## Conclusion
Following these steps will migrate CoreDNS from a bootstrap version to a Flux managed Helm installation, allowing for better version control and deployment management within your k3s cluster.
