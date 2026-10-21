#!/command/with-contenv bashio
# shellcheck shell=bash
# ==============================================================================
# Render Headscale / Headplane configuration from the app options.
# ==============================================================================
mkdir -p /run/hsha /run/headscale /run/tailscale

if ! python3 -m hsha.render; then
    bashio::exit.nok "Invalid configuration, see the messages above."
fi
