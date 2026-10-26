"""Redis client (ADR-006). Named redis_client so it never shadows the `redis` package."""

from redis.asyncio import Redis

from core.config import Settings


def create_redis(settings: Settings) -> Redis:
    timeout = settings.ready_check_timeout_s
    return Redis.from_url(
        settings.redis_url.get_secret_value(),
        socket_connect_timeout=timeout,
        socket_timeout=timeout,
    )


async def ping(client: Redis) -> None:
    await client.ping()
