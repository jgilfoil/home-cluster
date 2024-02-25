#!/usr/bin/env python3
import argparse
from kubernetes import client, config
from tabulate import tabulate

# Parse command-line arguments
parser = argparse.ArgumentParser(description='List resource requests across deployments, daemonsets, and statefulsets.')
parser.add_argument('--sort-cpu', action='store_true', help='Sort the output by CPU requests.')
parser.add_argument('--sort-memory', action='store_true', help='Sort the output by memory requests.')
args = parser.parse_args()

# Load kubeconfig and initialize Kubernetes client
config.load_kube_config()
v1_apps = client.AppsV1Api()

# Lists to hold the data and headers for the table
data = []
headers = ["Resource Type", "Name", "Namespace", "CPU Requests (cores)", "Memory Requests (MiB)"]
total_cpu_requests_sum = 0
total_memory_requests_sum = 0

# Function to process resources and collect resource requests
def process_resource(resource_items, resource_type):
    global total_cpu_requests_sum, total_memory_requests_sum

    for item in resource_items:
        total_cpu_requests = 0
        total_memory_requests = 0

        for container in item.spec.template.spec.containers:
            requests = container.resources.requests or {}
            cpu_request = str(requests.get('cpu', '0'))
            memory_request = str(requests.get('memory', '0'))

            # Parse CPU and memory requests
            if cpu_request.endswith('m'):
                total_cpu_requests += int(cpu_request[:-1]) / 1000
            elif cpu_request.isdigit():
                total_cpu_requests += int(cpu_request)

            if memory_request.endswith('Ki'):
                total_memory_requests += int(memory_request[:-2]) / 1024
            elif memory_request.endswith('Mi'):
                total_memory_requests += int(memory_request[:-2])
            elif memory_request.endswith('Gi'):
                total_memory_requests += int(memory_request[:-2]) * 1024
            elif memory_request.endswith('Ti'):
                total_memory_requests += int(memory_request[:-2]) * 1024 * 1024
            elif memory_request.isdigit():
                total_memory_requests += int(memory_request) / (1024 * 1024)

        total_cpu_requests_sum += total_cpu_requests
        total_memory_requests_sum += total_memory_requests

        data.append([
            resource_type,
            item.metadata.name,
            item.metadata.namespace,
            total_cpu_requests,
            total_memory_requests
        ])

# Process Deployments, DaemonSets, and StatefulSets
process_resource(v1_apps.list_deployment_for_all_namespaces().items, "Deployment")
process_resource(v1_apps.list_daemon_set_for_all_namespaces().items, "DaemonSet")
process_resource(v1_apps.list_stateful_set_for_all_namespaces().items, "StatefulSet")

# Append total row
data.append(["Total", "", "", total_cpu_requests_sum, total_memory_requests_sum])

# Sort the data based on the flags
if args.sort_cpu:
    data = sorted(data[:-1], key=lambda x: x[3], reverse=True) + [data[-1]]
elif args.sort_memory:
    data = sorted(data[:-1], key=lambda x: x[4], reverse=True) + [data[-1]]

# Convert numeric values to strings with formatting and print the table
formatted_data = [[row[0], row[1], row[2], f"{row[3]:.3f}", f"{row[4]:.1f}"] for row in data]
print(tabulate(formatted_data, headers, tablefmt="plain"))
