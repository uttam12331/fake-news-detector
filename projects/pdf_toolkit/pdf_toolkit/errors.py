class PdfToolkitError(Exception):
    """Base class for all expected/handled errors in this package."""


class InvalidPageRangeError(PdfToolkitError):
    pass


class IncorrectPasswordError(PdfToolkitError):
    pass


class NoFilesProvidedError(PdfToolkitError):
    pass
