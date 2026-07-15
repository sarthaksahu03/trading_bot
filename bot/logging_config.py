import os
import re
import logging
from logging.handlers import RotatingFileHandler

# Pattern to redact signature in queries/payloads (matches signature=HEX_STRING)
SIGNATURE_RE = re.compile(r'(signature=)[a-fA-F0-9]+', re.IGNORECASE)
# Pattern to redact API key header in logs
APIKEY_HEADER_RE = re.compile(r"('X-MBX-APIKEY':\s*')[^']+(\')", re.IGNORECASE)

class SecretRedactionFilter(logging.Filter):
    """
    Logging filter to redact API keys, API secrets, and signatures from log records
    (inspecting both record.msg and format arguments in record.args).
    """
    def __init__(self, api_key: str = None, api_secret: str = None):
        super().__init__()
        self.api_key = api_key
        self.api_secret = api_secret

    def redact_string(self, s: str) -> str:
        s = SIGNATURE_RE.sub(r'\1[REDACTED]', s)
        s = APIKEY_HEADER_RE.sub(r"\1[REDACTED]\2", s)

        # Redact API Secret if configured
        if self.api_secret and len(self.api_secret) > 4:
            s = s.replace(self.api_secret, "[REDACTED_SECRET]")

        # Redact API Key if configured
        if self.api_key and len(self.api_key) > 4:
            s = s.replace(self.api_key, "[REDACTED_KEY]")

        return s

    def filter(self, record: logging.LogRecord) -> bool:
        # Redact format arguments
        if record.args:
            args_list = list(record.args)
            for i, arg in enumerate(args_list):
                if isinstance(arg, str):
                    args_list[i] = self.redact_string(arg)
            record.args = tuple(args_list)

        # Redact main message template
        if isinstance(record.msg, str):
            record.msg = self.redact_string(record.msg)

        return True

def setup_logging(api_key: str = None, api_secret: str = None) -> logging.Logger:
    """
    Configures rotating file logging and console logging.
    Returns the root logger configured for the application.
    """
    # Ensure logs directory exists
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file = os.path.join(log_dir, "trading_bot.log")

    # Define formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Rotating File Handler (Max 5MB, up to 3 backups)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Console Handler (Only show INFO and above)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Redaction Filter
    redact_filter = SecretRedactionFilter(api_key=api_key, api_secret=api_secret)
    file_handler.addFilter(redact_filter)
    console_handler.addFilter(redact_filter)

    # Root Logger Setup
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # Avoid duplicate handlers if setup is called multiple times
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    # Suppress verbose and sensitive connection pool logs from urllib3
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    return logger
