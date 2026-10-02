"""Entry point for dbtidy."""

from dbtidy.log import setup_logging

PROJECT_NAME = "dbtidy"

# dans les autres module .py 
# import logging
#  logger = logging.getLogger(__name__)
def main() -> None:
    logger = setup_logging(PROJECT_NAME)
    logger.info("Starting %s", PROJECT_NAME)


if __name__ == "__main__":
    main()
