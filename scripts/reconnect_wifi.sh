#!/usr/bin/env bash
# Wi-Fi remediation script for Linux/macOS.
# Called by actions/network_actions.py with one argument:
#   reconnect        — disconnect and reconnect to the current known network
#   restart          — disable and re-enable the Wi-Fi interface
#   forget_and_rejoin — delete the saved connection and reconnect

set -euo pipefail

ACTION="${1:-}"

if [[ -z "$ACTION" ]]; then
    echo "Usage: $0 reconnect|restart|forget_and_rejoin" >&2
    exit 1
fi

# Detect interface: prefer nmcli, fall back to iw/ifconfig
get_wifi_iface() {
    if command -v nmcli &>/dev/null; then
        nmcli -t -f DEVICE,TYPE device | awk -F: '$2=="wifi"{print $1; exit}'
    elif command -v iw &>/dev/null; then
        iw dev | awk '/Interface/{print $2; exit}'
    else
        echo "wlan0"  # last resort guess
    fi
}

get_current_ssid() {
    if command -v nmcli &>/dev/null; then
        nmcli -t -f ACTIVE,SSID dev wifi | awk -F: '$1=="yes"{print $2; exit}'
    elif command -v iwgetid &>/dev/null; then
        iwgetid -r
    else
        echo ""
    fi
}

IFACE="$(get_wifi_iface)"

case "$ACTION" in
    reconnect)
        SSID="$(get_current_ssid)"
        if [[ -z "$SSID" ]]; then
            echo "Not connected to any Wi-Fi network." >&2
            exit 1
        fi
        echo "Disconnecting from '$SSID'..."
        if command -v nmcli &>/dev/null; then
            nmcli device disconnect "$IFACE"
            sleep 2
            nmcli device connect "$IFACE"
        else
            ip link set "$IFACE" down
            sleep 2
            ip link set "$IFACE" up
        fi
        echo "Reconnect to '$SSID' issued successfully."
        ;;

    restart)
        echo "Bringing down '$IFACE'..."
        if command -v nmcli &>/dev/null; then
            nmcli device disconnect "$IFACE" || true
        fi
        ip link set "$IFACE" down
        sleep 3
        echo "Bringing up '$IFACE'..."
        ip link set "$IFACE" up
        if command -v nmcli &>/dev/null; then
            nmcli device connect "$IFACE" || true
        fi
        echo "Adapter '$IFACE' restarted."
        ;;

    forget_and_rejoin)
        SSID="$(get_current_ssid)"
        if [[ -z "$SSID" ]]; then
            echo "Not connected — cannot forget and rejoin." >&2
            exit 1
        fi
        echo "Forgetting profile '$SSID'..."
        if command -v nmcli &>/dev/null; then
            nmcli device disconnect "$IFACE" || true
            nmcli connection delete "$SSID" || true
            sleep 2
            nmcli device wifi connect "$SSID"
        else
            echo "nmcli not available; manual reconnect required." >&2
            exit 1
        fi
        echo "Profile for '$SSID' deleted and reconnection initiated."
        ;;

    *)
        echo "Unknown action: $ACTION" >&2
        exit 1
        ;;
esac
