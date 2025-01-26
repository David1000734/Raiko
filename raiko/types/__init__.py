import logging
from dotenv import load_dotenv, dotenv_values   # noqa F401

log = logging.getLogger(__name__)
# Use to show entire module's log info
# log.setLevel(logging.DEBUG)


# region Helper Functions
def token_importer(token: str) -> str | None:
    '''
    Function will attempt to import the specified token from the .env file.
    If it failed, it will load a .env file and try again.
    If unable to import anything, raise an exception and end the program.

    :return the content of that variable or None.
    '''
    import os

    ATTEMPTS = 3
    token_value = None

    for (idx) in range(ATTEMPTS):
        token_value = os.getenv(token)

        if (token_value is not None):
            # Token found, end function
            break
        elif (token_value is None and idx < ATTEMPTS - 1):
            # Attempt to resolve missing env variable
            log.warning(
                f"Attempt: {idx + 1}, unable to find Discord Token." +
                "\nLoad env file."
            )

            # Load the env file
            load_dotenv()
        else:
            # Attempts exceeded, unable to retrieve token. Assert and end.
            log.error(
                f"Unable to retrieve \"{token}\" from .env " +
                f"after {idx + 1} attempts. Assertion end."
            )
            raise ImportError(f"Unable to find \"{token}\" in environments.")
    # For, END
    return token_value
