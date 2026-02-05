#!/bin/bash

echo "=== System Information ==="
echo "Hostname: $(hostname)"
echo "OS: $(uname -s)"
echo "Kernel: $(uname -r)"
echo "Architecture: $(uname -m)"
echo ""
echo "=== CPU Info ==="
lscpu | grep "Model name"
echo ""
echo "=== Memory Usage ==="
free -h
echo ""
echo "=== Disk Usage ==="
df -h | grep -v "tmpfs"
echo ""
echo "=== Network Interfaces ==="
ip addr show | grep "inet "
