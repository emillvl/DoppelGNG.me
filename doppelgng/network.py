"""Keep native capture requests within the authorized origin or public networks."""
import ipaddress
import os
import socket
from urllib.parse import urlsplit

import requests
from requests.adapters import HTTPAdapter


class DestinationDenied(RuntimeError):
    pass


def origin(url):
    parts = urlsplit(url)
    if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password:
        raise DestinationDenied(f'Invalid capture destination: {url}')
    try:
        port = parts.port if parts.port is not None else (443 if parts.scheme == 'https' else 80)
        return parts.scheme, parts.hostname.encode('idna').decode('ascii').lower(), port
    except (ValueError, UnicodeError) as error:
        raise DestinationDenied(f'Invalid capture destination: {url}') from error


class DestinationPolicy:
    def __init__(self, target, authorized_origins=()):
        self.authorized_origin = origin(target)
        self.authorized_origins = {self.authorized_origin, *(origin(url) for url in authorized_origins)}

    def addresses(self, url):
        destination = origin(url)
        if destination in self.authorized_origins:
            return None
        try:
            addresses = [ipaddress.ip_address(info[4][0]) for info in socket.getaddrinfo(destination[1], destination[2], type=socket.SOCK_STREAM)]
        except (OSError, ValueError) as error:
            raise DestinationDenied(f'Cannot verify capture destination: {url}') from error
        normalized = [getattr(address, 'ipv4_mapped', None) or address for address in addresses]
        if not normalized or any(not address.is_global or address.is_multicast for address in normalized):
            raise DestinationDenied(f'Unrelated private or non-public capture destination is not authorized: {url}')
        return list(dict.fromkeys(map(str, addresses)))

    def address(self, url):
        addresses = self.addresses(url)
        return addresses[0] if addresses is not None else None


class CaptureAdapter(HTTPAdapter):
    def __init__(self, policy):
        self.policy = policy
        super().__init__()

    def get_connection_with_tls_context(self, request, verify, proxies=None, cert=None):
        request.headers['Host'] = urlsplit(request.url).netloc
        address = getattr(request, '_capture_address', None) or self.policy.address(request.url)
        if address is None:
            return super().get_connection_with_tls_context(request, verify, proxies=proxies, cert=cert)
        # Pin the socket address while retaining Host, SNI, and certificate identity.
        host_params, pool_kwargs = self.build_connection_pool_key_attributes(request, verify, cert)
        original_host = host_params['host']
        if host_params['scheme'] == 'https':
            pool_kwargs.update(server_hostname=original_host, assert_hostname=original_host)
        else:
            # HTTP pools also need an origin-specific key when hosts share IPs.
            pool_kwargs['headers'] = {'Host': request.headers['Host']}
        host_params['host'] = address
        return self.poolmanager.connection_from_host(**host_params, pool_kwargs=pool_kwargs)

    def send(self, request, **kwargs):
        addresses = self.policy.addresses(request.url)
        if addresses is None:
            return super().send(request, **kwargs)
        for index, address in enumerate(addresses):
            request._capture_address = address
            try:
                return super().send(request, **kwargs)
            except requests.ConnectionError:
                if index == len(addresses) - 1:
                    raise
            finally:
                del request._capture_address


class CaptureSession(requests.Session):
    def __init__(self, authentication=None):
        super().__init__()
        self.authentication = authentication
        if authentication is not None:
            self.cookies = authentication.cookies

    def send(self, request, **kwargs):
        login = self.authentication
        if login is not None:
            login.guard.check(request.url)
            for name in ('Cookie', 'Authorization', 'Proxy-Authorization'):
                request.headers.pop(name, None)
            cookie = login.cookie_header(request.url)
            if cookie:
                request.headers['Cookie'] = cookie
        try:
            return super().send(request, **kwargs)
        finally:
            if login is not None:
                login.observe_cookies()
                request.headers.pop('Cookie', None)


def capture_session(target, authorized_origins=(), *, authentication=None):
    session = CaptureSession(authentication)
    # Proxy DNS could bypass pinning; netrc could add unrelated credentials.
    session.trust_env = False
    session.verify = os.environ.get('REQUESTS_CA_BUNDLE') or os.environ.get('CURL_CA_BUNDLE') or True
    adapter = CaptureAdapter(DestinationPolicy(target, authorized_origins))
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session
