"""
Parallel-run notifier for the new tournament platform (issue #118).

During the one-way parallel-run bridge, the legacy Discord bot mirrors a few
events to the new Cloudflare-Worker tournament platform via its `/legacy/*`
endpoints. `post_to_platform` is the single helper used for that.

It is **synchronous and fail-open by design**:

* Synchronous, because the AWS Lambda execution environment freezes the
  moment the handler returns -- a background thread would never run. The
  call is therefore made inline, but only AFTER the handler's existing work
  and the Discord reply, so it adds no user-visible latency.
* Short-timeout, so a slow/unreachable platform can never stall the handler.
* Fail-open: every failure mode (timeout, connection error, HTTP non-2xx,
  or anything else) is caught and swallowed. The helper never raises and
  never affects the calling handler.

Configuration -- both sourced from the Lambda environment (populated from
the Sceptre/CloudFormation stack parameters, same as the bot's other
secrets / config; see ``templates/template.py`` and ``config/*/config.yaml``):

* ``PLATFORM_BASE_URL``   -- base URL of the platform API Worker, e.g.
                             ``https://api.example.com``. Endpoint paths are
                             joined onto it (``/legacy/checkin`` etc.).
* ``LEGACY_BRIDGE_SECRET`` -- shared secret; sent in the
                             ``x-legacy-bridge-secret`` request header. Must
                             match the value the platform stores under the
                             same name. Marked ``NoEcho`` in the stack.

If either value is unset the helper simply no-ops -- the bridge is optional
and its absence must never break the bot.
"""
import logging
import os

import requests

# Header the platform's `/legacy/*` endpoints expect the shared secret in.
BRIDGE_SECRET_HEADER = "x-legacy-bridge-secret"

# Short timeout (seconds): connect + read. The platform call is best-effort;
# it must never hold up the Lambda handler.
REQUEST_TIMEOUT = 3


def post_to_platform(path, payload):
    """Fire-and-forget POST of an event to a platform `/legacy/*` endpoint.

    Args:
        path: endpoint path, e.g. ``"/legacy/checkin"`` (leading slash
            optional -- it is normalised against ``PLATFORM_BASE_URL``).
        payload: JSON-serialisable request body.

    Returns:
        ``True`` if the platform accepted the event with a 2xx response,
        ``False`` for every other outcome (unconfigured, timeout, connection
        error, non-2xx, or any unexpected error).

    This function never raises; the caller is unaffected by any failure.
    """
    base_url = os.environ.get("PLATFORM_BASE_URL")
    secret = os.environ.get("LEGACY_BRIDGE_SECRET")

    if not base_url or not secret:
        # Bridge not configured -- silently skip. This is expected before the
        # platform is wired up and must not break the bot.
        logging.debug("Platform bridge not configured; skipping %s", path)
        return False

    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"

    try:
        res = requests.post(
            url,
            json=payload,
            headers={BRIDGE_SECRET_HEADER: secret},
            timeout=REQUEST_TIMEOUT,
        )
        res.raise_for_status()
        logging.info("Platform bridge: %s -> %s", path, res.status_code)
        return True
    except Exception as e:  # noqa: BLE001 -- fail-open: swallow EVERYTHING
        # Timeout, connection error, HTTP non-2xx, or anything unexpected.
        # The bridge is best-effort; log for the parallel-run audit and
        # carry on as if nothing happened.
        logging.warning("Platform bridge call to %s failed (swallowed): %s", path, e)
        return False
