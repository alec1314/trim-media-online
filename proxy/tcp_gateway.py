#!/usr/bin/env python3
"""TV / 盒子端 TCP 兼容网关。

飞牛影视 TV 端与部分第三方客户端不走 nginx 的 /v，而是直连影视服务 TCP 端口
8005。主代理只接管了 /var/run/trim_media.sock，因此这些客户端会绕过本扩展。
这里监听一个本地 TCP 端口，把连接原样转发到主代理的 UDS；再由 nftables 把
8005 的入站连接重定向到本端口（见 supervise.py）。

用法：tcp_gateway.py <listen_host> <listen_port> <unix_socket>
"""
from __future__ import annotations

import asyncio
import signal
import sys


async def _pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while True:
            data = await reader.read(65536)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except (asyncio.CancelledError, Exception):
        pass
    finally:
        try:
            writer.write_eof()
        except Exception:
            pass


async def _handle(client_reader: asyncio.StreamReader,
                  client_writer: asyncio.StreamWriter, target: str) -> None:
    try:
        up_reader, up_writer = await asyncio.open_unix_connection(target)
    except Exception:
        try:
            client_writer.close()
        except Exception:
            pass
        return
    try:
        await asyncio.gather(
            _pipe(client_reader, up_writer),
            _pipe(up_reader, client_writer),
        )
    finally:
        for w in (up_writer, client_writer):
            try:
                w.close()
            except Exception:
                pass


async def _serve(host: str, port: int, target: str) -> None:
    server = await asyncio.start_server(
        lambda r, w: _handle(r, w, target), host, port, backlog=256)

    async def _shutdown():
        server.close()
        await server.wait_closed()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, lambda: asyncio.create_task(_shutdown()))
        except NotImplementedError:
            pass
    print(f"[tcp-gateway] listening {host}:{port} -> {target}", flush=True)
    async with server:
        await server.serve_forever()


def main() -> int:
    if len(sys.argv) < 4:
        print("usage: tcp_gateway.py <host> <port> <uds>", file=sys.stderr)
        return 2
    host, port, target = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    try:
        asyncio.run(_serve(host, port, target))
    except KeyboardInterrupt:
        pass
    except OSError as exc:
        print(f"[tcp-gateway] bind {host}:{port} failed: {exc}", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
