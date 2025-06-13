import asyncio
import concurrent.futures

import google.auth
import google.auth.transport.requests

_cached_credentials = None
_credentials_lock = asyncio.Lock()


async def get_google_access_token():
    global _cached_credentials

    async with _credentials_lock:
        if _cached_credentials is None:

            def _sync_get_initial_credentials():
                creds, _ = google.auth.default()
                req = google.auth.transport.requests.Request()
                creds.refresh(req)
                return creds

            loop = asyncio.get_running_loop()
            with concurrent.futures.ThreadPoolExecutor() as pool:
                _cached_credentials = await loop.run_in_executor(pool, _sync_get_initial_credentials)
        else:

            def _sync_refresh_credentials(creds_obj):
                req = google.auth.transport.requests.Request()
                creds_obj.refresh(req)
                return creds_obj

            loop = asyncio.get_running_loop()
            with concurrent.futures.ThreadPoolExecutor() as pool:
                _cached_credentials = await loop.run_in_executor(pool, _sync_refresh_credentials, _cached_credentials)

        return _cached_credentials.token
