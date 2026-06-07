"""
可选快速端口扫描 - 使用 socket 连接测试常见端口
如果安装了 naabu，优先使用 naabu
"""
import asyncio
import os
import subprocess
import json
from typing import List, Optional
from app.config import settings
from app.utils.logger import get_logger

COMMON_PORTS = [80, 443, 8080, 8443, 22, 3306, 6379, 27017, 21, 25, 110, 143, 993, 995, 5432, 3389, 5900, 9090, 3000, 5000]


async def quick_port_scan(ip_list: List[str], ports: List[int] = None, timeout: int = None) -> List[Dict]:
    """
    快速 TCP connect 端口扫描。
    返回: [{"ip": "1.2.3.4", "open_ports": [80, 443]}, ...]
    """
    ports = ports or COMMON_PORTS
    timeout = timeout or settings.port_scan_timeout
    logger = get_logger()

    naabu_path = settings.naabu_path
    if os.path.exists(naabu_path):
        return await _naabu_scan(ip_list, ports, timeout, logger)

    # 回退到纯 Python socket 扫描
    logger.info(f"Socket scanning {len(ip_list)} IPs, {len(ports)} ports each")
    semaphore = asyncio.Semaphore(100)

    async def scan_ip(ip: str) -> Dict:
        open_ports = []
        for port in ports:
            async with semaphore:
                try:
                    _, writer = await asyncio.wait_for(
                        asyncio.open_connection(ip, port),
                        timeout=2.0,
                    )
                    writer.close()
                    open_ports.append(port)
                except (asyncio.TimeoutError, OSError, ConnectionRefusedError):
                    pass
        return {"ip": ip, "open_ports": open_ports}

    tasks = [scan_ip(ip) for ip in ip_list]
    results = await asyncio.gather(*tasks)
    logger.info(f"Port scan complete: {sum(1 for r in results if r['open_ports'])} hosts have open ports")
    return list(results)


async def _naabu_scan(ip_list: List[str], ports: List[int], timeout: int, logger) -> List[Dict]:
    """使用 naabu 进行端口扫描"""
    import tempfile

    ip_str = ",".join(ip_list)
    ports_str = ",".join(str(p) for p in ports)

    cmd = [
        settings.naabu_path,
        "-host", ip_str,
        "-p", ports_str,
        "-silent",
        "-json",
        "-timeout", str(timeout * 1000),  # naabu 用毫秒
    ]

    logger.info(f"Running naabu for {len(ip_list)} IPs")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 30)

    results = {}
    for ip in ip_list:
        results[ip] = {"ip": ip, "open_ports": []}

    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        try:
            data = json.loads(line)
            ip = data.get("ip") or data.get("host")
            port = data.get("port")
            if ip and port and ip in results:
                results[ip]["open_ports"].append(int(port))
        except json.JSONDecodeError:
            continue

    return list(results.values())
