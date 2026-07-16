import os
import hmac
import hashlib
import time
import urllib.parse
import logging
import requests
from typing import Dict, Any

logger = logging.getLogger(__name__)

class BinanceAPIError(Exception):
    """
    Exception raised when the Binance API returns an error response.
    """
    def __init__(self, status_code: int, error_code: int, message: str):
        super().__init__(f"Binance API Error (HTTP {status_code}): Code {error_code} - {message}")
        self.status_code = status_code
        self.error_code = error_code
        self.message = message


class BinanceClient:
    """
    Low-level Binance Futures Testnet REST API client.
    Handles authentication, HMAC-SHA256 signing, time sync, requests, and logging.
    """
    BASE_URL = "https://testnet.binancefuture.com"
    _exchange_info = None

    def __init__(self, api_key: str = None, api_secret: str = None):
        # Read from environment variables if not provided
        self.api_key = api_key or os.getenv("BINANCE_API_KEY")
        self.api_secret = api_secret or os.getenv("BINANCE_API_SECRET")

        if not self.api_key or not self.api_secret:
            raise ValueError(
                "Binance API Key and Secret must be provided or set as environment variables "
                "(BINANCE_API_KEY and BINANCE_API_SECRET)."
            )

        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/x-www-form-urlencoded",
            "X-MBX-APIKEY": self.api_key
        })
        self.time_drift = 0
        self._ticker_cache = {}
        self.sync_time()

    def get_exchange_info(self) -> Dict[str, Any]:
        """
        Retrieves and caches exchange information.
        """
        if BinanceClient._exchange_info is None:
            logger.info("Fetching exchange info from Binance server...")
            BinanceClient._exchange_info = self._request("GET", "/fapi/v1/exchangeInfo", {}, signed=False)
        return BinanceClient._exchange_info

    def get_symbol_info(self, symbol: str) -> Dict[str, Any] | None:
        """
        Retrieves filter and metadata details for a specific symbol.
        """
        info = self.get_exchange_info()
        for sym_info in info.get("symbols", []):
            if sym_info.get("symbol") == symbol:
                return sym_info
        return None

    def get_ticker_price(self, symbol: str) -> float:
        """
        Retrieves the current ticker price for a symbol, with a 5-second cache.
        """
        now = time.time()
        if symbol in self._ticker_cache:
            cache_time, price = self._ticker_cache[symbol]
            if now - cache_time < 5.0:
                return price

        res = self._request("GET", "/fapi/v1/ticker/price", {"symbol": symbol}, signed=False)
        price = float(res["price"])
        self._ticker_cache[symbol] = (now, price)
        return price

    def sync_time(self) -> None:
        """
        Syncs local clock with Binance server clock to prevent timestamp errors.
        """
        url = f"{self.BASE_URL}/fapi/v1/time"
        logger.debug(f"Syncing time with Binance server: {url}")
        try:
            # Public endpoint, no auth required
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            server_time = response.json()["serverTime"]
            local_time = int(time.time() * 1000)
            self.time_drift = server_time - local_time
            logger.info(f"Time synced. Server: {server_time}, Local: {local_time}, Drift: {self.time_drift}ms")
        except Exception as e:
            logger.warning(f"Failed to sync time with server, using local time. Error: {e}")
            self.time_drift = 0

    def _get_timestamp(self) -> int:
        """
        Returns the synchronized timestamp in milliseconds.
        """
        return int(time.time() * 1000) + self.time_drift

    def _sign(self, query_string: str) -> str:
        """
        Generates HMAC-SHA256 signature for a query string.
        """
        return hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    def _request(self, method: str, path: str, params: Dict[str, Any], signed: bool = True) -> Dict[str, Any]:
        """
        Sends an HTTP request with retry logic and logs the details.
        """
        # Create a copy of parameters to avoid mutating the caller's input
        payload = params.copy()
        
        if signed:
            payload["timestamp"] = self._get_timestamp()
            payload["recvWindow"] = 5000
            
            # Construct exact query string and generate HMAC-SHA256 signature
            query_string = urllib.parse.urlencode(payload)
            signature = self._sign(query_string)
            query_string += f"&signature={signature}"
            url = f"{self.BASE_URL}{path}?{query_string}"
        else:
            query_string = urllib.parse.urlencode(payload)
            url = f"{self.BASE_URL}{path}"
            if query_string:
                url += f"?{query_string}"

        # Redacted log representation of the URL for safety
        redacted_query = SIGNATURE_RE_REPLACE(query_string) if signed else query_string
        redacted_url = f"{self.BASE_URL}{path}"
        if redacted_query:
            redacted_url += f"?{redacted_query}"

        logger.info(f"Sending API Request: {method} {redacted_url}")

        max_retries = 2
        for attempt in range(1, max_retries + 1):
            try:
                response = self.session.request(method, url, timeout=10)
                logger.info(f"Received API Response: HTTP {response.status_code} for {method} {path}")
                
                # Check for successful response
                if response.status_code == 200:
                    try:
                        return response.json()
                    except ValueError:
                        raise ValueError(f"Invalid JSON response received from API: {response.text}")

                # Handle failure status codes
                try:
                    error_data = response.json()
                    error_code = error_data.get("code", 0)
                    error_msg = error_data.get("msg", "Unknown error")
                except ValueError:
                    error_code = response.status_code
                    error_msg = response.text

                # Raise specific Binance error
                raise BinanceAPIError(response.status_code, error_code, error_msg)

            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                logger.warning(f"Network error on attempt {attempt}/{max_retries}: {e}")
                if attempt == max_retries:
                    logger.error("Max retries reached. Network request failed.")
                    raise
                time.sleep(1.0 * attempt)  # simple exponential backoff
            except Exception as e:
                # Re-raise API errors or parsing exceptions immediately
                if isinstance(e, BinanceAPIError):
                    logger.error(f"API Error response: {e}")
                raise

        raise RuntimeError("Request failed unexpectedly without raising a specific exception.")

# Helper for string redaction of signature inside the client logger before passing to logging subsystem
def SIGNATURE_RE_REPLACE(s: str) -> str:
    import re
    return re.sub(r'(signature=)[a-fA-F0-9]+', r'\1[REDACTED]', s, flags=re.IGNORECASE)
