#!/command/with-contenv bashio
# shellcheck shell=bash
# ==============================================================================
# Render Headscale / Headplane configuration from the app options.
# ==============================================================================
mkdir -p /run/hsha /run/headscale /run/tailscale

# Never fails on a bad configuration: Headscale then waits and the setup
# wizard in the sidebar panel explains what to fix.
python3 -m hsha.render || bashio::log.error "Rendering the configuration failed, see above."
