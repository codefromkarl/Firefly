"""Explicit bounded public-HTTP HEAD checks; no content download or background work."""
from __future__ import annotations

import http.client
import ipaddress
import json
import socket
import ssl
import subprocess
import sys
import time
from urllib.parse import urljoin, urlsplit, urlunsplit

from .store import ControlError, utc_now


class ProbeRejected(ValueError):
    pass


def _resolve(host, port, timeout=5.0):
    # getaddrinfo has no Python timeout. Isolate only DNS resolution in a bounded
    # child process; constant code + argv, never shell code from the source.
    code = "import json,socket,sys; print(json.dumps(sorted({r[4][0] for r in socket.getaddrinfo(sys.argv[1],int(sys.argv[2]),type=socket.SOCK_STREAM)})))"
    try:
        result = subprocess.run([sys.executable, '-I', '-c', code, host, str(port)],
                                capture_output=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired as error:
        raise TimeoutError('DNS timeout') from error
    if result.returncode:
        raise OSError('DNS lookup failed')
    return json.loads(result.stdout)


def _target(url, resolver):
    try:
        parsed = urlsplit(url)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
    except (ValueError, UnicodeError) as error:
        raise ProbeRejected('invalid_url') from error
    if parsed.scheme not in {'http', 'https'} or not host or parsed.username is not None or parsed.password is not None:
        raise ProbeRejected('scheme_host_or_credentials_rejected')
    if any(ord(char) < 33 or ord(char) == 127 for char in url):
        raise ProbeRejected('url_control_characters_rejected')
    host = host.rstrip('.').encode('idna').decode('ascii').lower()
    if host == 'localhost' or host.endswith(('.localhost', '.local', '.internal')) or '%' in host:
        raise ProbeRejected('non_public_host')
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        addresses = resolver(host, port)
    else:
        addresses = [str(literal)]
    if not addresses or len(addresses) > 64:
        raise ProbeRejected('no_usable_public_address')
    for address in addresses:
        try:
            ip = ipaddress.ip_address(address)
        except ValueError as error:
            raise ProbeRejected('invalid_resolver_address') from error
        if not ip.is_global or ip.is_multicast or ip.is_unspecified or ip.is_reserved:
            raise ProbeRejected('non_public_address')
    # The transport must use this already-validated IP, not resolve host again.
    return {'url': urlunsplit((parsed.scheme, parsed.netloc, parsed.path or '/', parsed.query, '')),
            'host': host, 'port': port, 'ip': addresses[0], 'scheme': parsed.scheme,
            'request_target': urlunsplit(('', '', parsed.path or '/', parsed.query, ''))}


class _PinnedTLS(http.client.HTTPSConnection):
    def __init__(self, target, timeout):
        super().__init__(target['host'], target['port'], timeout=timeout, context=ssl.create_default_context())
        self.target = target

    def connect(self):
        raw = socket.create_connection((self.target['ip'], self.port), self.timeout)
        try:
            self.sock = self._context.wrap_socket(raw, server_hostname=self.target['host'])
        except BaseException:
            raw.close()
            raise


def _head(target, timeout):
    connection = (_PinnedTLS(target, timeout) if target['scheme'] == 'https'
                  else http.client.HTTPConnection(target['ip'], target['port'], timeout=timeout))
    host = target['host']
    if ':' in host:
        host = '[' + host + ']'
    if target['port'] != (443 if target['scheme'] == 'https' else 80):
        host += ':' + str(target['port'])
    try:
        connection.request('HEAD', target['request_target'], headers={
            'Host': host, 'User-Agent': 'CreatorSourceAvailability/1.0', 'Accept': '*/*', 'Connection': 'close'})
        response = connection.getresponse()
        # Headers only. Never call read(), render HTML, follow meta refresh, or run page commands.
        return {'http_status': response.status, 'location': response.getheader('Location')}
    finally:
        connection.close()


def check_web_source(store, source_id, *, timeout=5.0, max_redirects=3, transport=None, resolver=None):
    """Return immutable receipt of a HEAD probe, not a body or semantic verification.

    transport(target_dict, timeout_seconds) and resolver(host, port)->[IP] are
    injectable for offline tests. They must not be exposed as untrusted CLI options.
    """
    if isinstance(timeout, bool) or not isinstance(timeout, (float, int)) or not 0 < timeout <= 15:
        raise ControlError('Probe timeout must be 0 < seconds <= 15')
    if isinstance(max_redirects, bool) or not isinstance(max_redirects, int) or not 0 <= max_redirects <= 5:
        raise ControlError('Probe redirects must be 0..5')
    source = store.get('source', source_id)
    version_id = source['data']['active_version_id']
    version = store.get('source_version', version_id)
    url = version['data'].get('url')
    if not url:
        raise ControlError('Current source version has no web URL')
    if source['data'].get('withdrawn'):
        raise ControlError('Withdrawn source is not probed')
    transport = transport or _head
    started = utc_now()
    deadline = time.monotonic() + timeout
    current, status, reason, http_status = url, 'unknown', 'not_checked', None
    visited, hops = set(), []
    for count in range(max_redirects + 1):
        if current in visited:
            reason = 'redirect_loop'
            break
        visited.add(current)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            reason = 'timeout'
            break
        try:
            lookup = resolver if resolver is not None else lambda host, port: _resolve(host, port, remaining)
            target = _target(current, lookup)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                reason = 'timeout'
                break
            response = transport(target, remaining)
            if time.monotonic() > deadline:
                reason = 'timeout'
                break
            http_status = response['http_status']
            if isinstance(http_status, bool) or not isinstance(http_status, int) or not 100 <= http_status <= 599:
                raise ValueError('invalid HTTP status')
            current = target['url']
            hops.append({'url': current, 'http_status': http_status})
            if http_status in {301, 302, 303, 307, 308}:
                location = response.get('location')
                if not isinstance(location, str) or not location:
                    reason = 'redirect_without_location'
                    break
                if count == max_redirects:
                    reason = 'redirect_limit'
                    break
                current = urljoin(current, location)
                continue
            if 200 <= http_status < 300:
                status, reason = 'reachable', 'head_succeeded'
            elif http_status in {404, 410}:
                status, reason = 'unavailable', 'http_not_found_or_gone'
            elif http_status in {401, 403}:
                reason = 'access_restricted_not_deleted'
            elif http_status == 405:
                reason = 'head_unsupported_no_get_fallback'
            elif http_status == 429:
                reason = 'rate_limited'
            else:
                reason = 'http_inconclusive'
            break
        except ProbeRejected as error:
            reason = 'target_rejected:' + str(error)
            break
        except (TimeoutError, socket.timeout):
            reason = 'timeout'
            break
        except (OSError, http.client.HTTPException, ValueError, UnicodeError):
            reason = 'transport_or_dns_error'
            break
    return store.create('receipt', {'type': 'web_check', 'source_id': source_id,
        'source_version_id': version_id, 'url': url, 'started_at': started, 'checked_at': utc_now(),
        'status': status, 'http_status': http_status, 'final_url': current, 'hops': hops,
        'reason': reason, 'provenance': 'program_http_probe', 'method': 'HEAD',
        'body_downloaded': False, 'body_unchanged_verified': False, 'semantic_verified': False,
        'scope': 'availability_at_check_time_only', 'timeout_seconds': timeout})
