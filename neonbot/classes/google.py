import asyncio
import concurrent.futures

import google.auth
import google.auth.transport.requests

_cached_credentials = None
_credentials_lock = asyncio.Lock()


async def get_google_access_token():
    global _cached_credentials

    def get_credentials(creds=None):
        if creds is None:
            creds, _ = google.auth.default()
        req = google.auth.transport.requests.Request()
        creds.refresh(req)
        return creds

    async with _credentials_lock:
        loop = asyncio.get_running_loop()

        if _cached_credentials is None:
            with concurrent.futures.ThreadPoolExecutor() as pool:
                _cached_credentials = await loop.run_in_executor(pool, get_credentials)
        elif _cached_credentials.expired:
            with concurrent.futures.ThreadPoolExecutor() as pool:
                _cached_credentials = await loop.run_in_executor(pool, get_credentials, _cached_credentials)

        return _cached_credentials.token
