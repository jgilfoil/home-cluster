#!/usr/bin/env python3
import argparse
from kubernetes import client, config
from tabulate import tabulate

# Parse command-line arguments
parser = argparse.ArgumentParser(description='List resource requests for containers within pods.')
parser.add_argument('--sort-cpu', action='store_true', help='Sort the output by CPU requests for containers.')
parser.add_argument('--sort-memory', action='store_true', help='Sort the output by memory requests for containers.')
args = parser.parse_args()

# Load kubeconfig and initialize Kubernetes client
config.load_kube_config()
v1_core = client.CoreV1Api()

# Lists to hold the data and headers for the table
data = []
headers = ["Namespace", "Pod", "Container", "CPU Requests (cores)", "Memory Requests (MiB)"]

# Function to process pods and collect resource requests for each container
def process_pods(pods):
    for pod in pods.items:
        for container in pod.spec.containers:
            cpu_request = memory_request = 0
            requests = container.resources.requests or {}

            # Parse CPU requests
            cpu_val = str(requests.get('cpu', '0'))
            if cpu_val.endswith('m'):
                cpu_request = int(cpu_val[:-1]) / 1000
            elif cpu_val.isdigit():
                cpu_request = int(cpu_val)

            # Parse memory requests
            memory_val = str(requests.get('memory', '0'))
            if memory_val.endswith('Ki'):
                memory_request = int(memory_val[:-2]) / 1024
            elif memory_val.endswith('Mi'):
                memory_request = int(memory_val[:-2])
            elif memory_val.endswith('Gi'):
                memory_request = int(memory_val[:-2]) * 1024
            elif memory_val.endswith('Ti'):
                memory_request = int(memory_val[:-2]) * 1024 * 1024
            elif memory_val.isdigit():
                memory_request = int(memory_val) / (1024 * 1024)

            data.append([
                pod.metadata.namespace,
                pod.metadata.name,
                container.name,
                cpu_request,
                memory_request
            ])

# Process all pods
process_pods(v1_core.list_pod_for_all_namespaces())

# Sort the data based on the flags
if args.sort_cpu:
    data.sort(key=lambda x: x[3], reverse=True)
elif args.sort_memory:
    data.sort(key=lambda x: x[4], reverse=True)

# Convert numeric values to strings with formatting and print the table
formatted_data = [[row[0], row[1], row[2], f"{row[3]:.3f}", f"{row[4]:.1f}"] for row in data]
print(tabulate(formatted_data, headers, tablefmt="plain"))
