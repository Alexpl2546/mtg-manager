# Security Policy

## Reporting

Please report security issues privately to the repository owner. Do not open a
public issue containing bot tokens, proxy credentials, client names, server IP
addresses, or connection links.

## Secret handling

The following must never be committed:

- `.env`
- runtime `data/*.json`
- Telemt configuration files
- generated proxy links
- VPS audit archives and logs

Changing a Telemt secret or `tls_domain` invalidates existing client links and
requires a controlled migration.
