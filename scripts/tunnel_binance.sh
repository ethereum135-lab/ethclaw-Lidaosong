#!/bin/bash
# Persistent SSH SOCKS5 tunnel through AWS (web4) for Binance API access
# This tunnel bypasses the Binance 451 geo-block on the Mac
# Port 1080 → SOCKS5 proxy via AWS server (which has unrestricted Binance access)
# Runs in foreground — launchd's KeepAlive manages persistence
SSH_PORT=1080

# Kill any stale SSH processes on this port
lsof -ti :$SSH_PORT 2>/dev/null | xargs kill 2>/dev/null || true
sleep 1

# Start SSH tunnel in foreground (launchd will keep alive)
exec ssh -o StrictHostKeyChecking=no \
    -o ConnectTimeout=10 \
    -o TCPKeepAlive=yes \
    -o ServerAliveInterval=15 \
    -o ServerAliveCountMax=4 \
    -o ExitOnForwardFailure=yes \
    -D $SSH_PORT -N web4
