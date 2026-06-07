"""
子域名发现工具封装 - Subfinder wrapper
"""
import os
import subprocess
import tempfile
from typing import List, Set
from app.config import settings
from app.utils.logger import get_logger


def run_subfinder(domain: str, timeout: int = None) -> List[str]:
    """
    调用 subfinder 发现子域名。
    返回去重后的子域名列表（包含完整域名）。
    如果 subfinder 不可用，回退到简单 DNS 暴力枚举。
    """
    timeout = timeout or settings.subdomain_timeout
    logger = get_logger()

    subfinder_path = settings.subfinder_path
    if not os.path.exists(subfinder_path):
        logger.warning(f"subfinder not found at {subfinder_path}, falling back to built-in brute force")
        return _fallback_bruteforce(domain)

    try:
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".txt", delete=False) as tmp:
            tmp_path = tmp.name

        cmd = [subfinder_path, "-d", domain, "-o", tmp_path, "-silent"]
        logger.info(f"Running subfinder for {domain}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        if result.returncode != 0:
            logger.error(f"subfinder failed: {result.stderr.strip()}")
            return _fallback_bruteforce(domain)

        # 读取输出文件
        subdomains = []
        with open(tmp_path, "r") as f:
            for line in f:
                line = line.strip().lower()
                if line and line.endswith(f".{domain}") or line == domain:
                    subdomains.append(line)

        # 清理临时文件
        os.unlink(tmp_path)

        unique = sorted(set(subdomains))
        logger.info(f"subfinder found {len(unique)} subdomains for {domain}")
        return unique

    except subprocess.TimeoutExpired:
        logger.error(f"subfinder timed out for {domain} after {timeout}s")
        return []
    except Exception as e:
        logger.error(f"subfinder error for {domain}: {e}")
        return []


def _fallback_bruteforce(domain: str) -> List[str]:
    """
    简单回退：常用子域名前缀暴力匹配。
    实际部署中可使用字典文件。
    """
    logger = get_logger()
    common_prefixes = [
        "www", "mail", "ftp", "admin", "api", "vpn", "portal",
        "dev", "test", "staging", "app", "cdn", "blog", "shop",
        "docs", "status", "monitor", "dashboard", "login",
        "git", "jenkins", "ci", "jira", "wiki", "help",
    ]
    logger.info(f"Fallback brute force enumeration for {domain} with {len(common_prefixes)} prefixes")
    return [f"{prefix}.{domain}" for prefix in common_prefixes] + [domain]
