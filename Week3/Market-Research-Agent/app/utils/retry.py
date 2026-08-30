from collections.abc import Callable

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


def deterministic_retry(
    exceptions: tuple[type[BaseException], ...], max_attempts: int = 3
) -> Callable:
    """Reusable retry policy for transient external-call failures. Deliberately
    plain and boring: fixed exponential backoff, no jitter randomness that
    would make behavior non-reproducible in tests."""
    return retry(
        reraise=True,
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        retry=retry_if_exception_type(exceptions),
    )
