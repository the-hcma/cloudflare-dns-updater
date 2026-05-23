"""Update Cloudflare DNS A and AAAA records from external IP discovery."""

from dns_updater.build_info import get_build_info

__version__ = get_build_info()[0]
