import logging

from colored import Fore
from colored import Style as style


class LoggerFormatter(logging.Formatter):
    """Custom formatter for logging messages with colors"""

    FORMATS = {
        logging.DEBUG: f"[{Fore.GREY_3}%(asctime)s{style.reset}] [{Fore.DARK_ORANGE}%(name)s{Fore.WHITE}:{Fore.DARK_ORANGE}%(lineno)d{style.reset}] {Fore.WHITE}%(message)s{style.reset}",
        logging.INFO: f"[{Fore.GREY_3}%(asctime)s{style.reset}] [{Fore.DARK_ORANGE}%(name)s{Fore.WHITE}:{Fore.DARK_ORANGE}%(lineno)d{style.reset}] {Fore.SPRING_GREEN_1}%(message)s{style.reset}",
        logging.WARNING: f"[{Fore.GREY_3}%(asctime)s{style.reset}] [{Fore.DARK_ORANGE}%(name)s{Fore.WHITE}:{Fore.DARK_ORANGE}%(lineno)d{style.reset}] {Fore.YELLOW_1}%(message)s{style.reset}",
        logging.ERROR: f"[{Fore.GREY_3}%(asctime)s{style.reset}] [{Fore.DARK_ORANGE}%(name)s{Fore.WHITE}:{Fore.DARK_ORANGE}%(lineno)d{style.reset}] {Fore.LIGHT_RED}%(message)s{style.reset}",
        logging.CRITICAL: f"[{Fore.GREY_3}%(asctime)s{style.reset}] [{Fore.DARK_ORANGE}%(name)s{Fore.WHITE}:{Fore.DARK_ORANGE}%(lineno)d{style.reset}] {Fore.RED}%(message)s{style.reset}",
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)
