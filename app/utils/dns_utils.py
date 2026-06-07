"""
DNS 解析工具 - 并发 A/AAAA/CNAME 查询
支持超时控制和并发限制
"""
import asyncio
from typing import List, Dict, Tuple
import dns.resolver
import dns.exception
from app.config import settings
from app.utils.logger import get_logger

# 独立 resolver，不依赖系统 DNS 缓存
_resolver = dns.resolver.Resolver()
_resolver.timeout = 3
_resolver.lifetime = 3


async def resolve_subdomains(
    subdomains: List[str],
    concurrency: int = None,
) -> Tuple[List[Dict], List[Dict]]:
    """
    并发 DNS 解析。
    返回: (成功解析列表, 失败列表)
    每条成功记录: {"subdomain": "x.com", "ips": ["1.2.3.4"], "records": [...], "cname": "..."}
    """
    concurrency = concurrency or settings.dns_concurrency
    logger = get_logger()

    if not subdomains:
        return [], []

    logger.info(f"Starting DNS resolution for {len(subdomains)} subdomains (concurrency={concurrency})")

    semaphore = asyncio.Semaphore(concurrency)

    async def resolve_one(domain: str) -> Tuple[str, Dict | None]:
        async with semaphore:
            try:
                result = await asyncio.wait_for(
                    asyncio.to_thread(_resolve_sync, domain),
                    timeout=settings.dns_resolve_timeout,
                )
                return domain, result
            except asyncio.TimeoutError:
                logger.debug(f"DNS timeout: {domain}")
                return domain, None
            except Exception as e:
                logger.debug(f"DNS error for {domain}: {e}")
                return domain, None

    tasks = [resolve_one(sd) for sd in subdomains]
    results = await asyncio.gather(*tasks)

    resolved = []
    failed = []

    for domain, result in results:
        if result and result.get("ips"):
            resolved.append(result)
        else:
            failed.append({"subdomain": domain, "reason": "no A/AAAA records"})

    logger.info(f"DNS resolved: {len(resolved)} success, {len(failed)} failed")
    return resolved, failed


def _resolve_sync(domain: str) -> Dict | None:
    """
    同步子域名解析。返回 IP 列表 + DNS 记录。
    """
    ips = []
    cname = None
    records = []

    try:
        # 先查 CNAME
        try:
            answers = _resolver.resolve(domain, "CNAME")
            for ans in answers:
                cname = str(ans.target).rstrip(".")
                records.append({"type": "CNAME", "value": cname})
        except (dns.exception.DNSException, dns.resolver.NoAnswer):
            pass

        # 查 A 记录
        try:
            answers = _resolver.resolve(domain, "A")
            for ans in answers:
                ip = str(ans)
                ips.append(ip)
                records.append({"type": "A", "value": ip})
        except (dns.exception.DNSException, dns.resolver.NoAnswer):
            pass

        # 查 AAAA 记录
        try:
            answers = _resolver.resolve(domain, "AAAA")
            for ans in answers:
                ip = str(ans)
                ips.append(ip)
                records.append({"type": "AAAA", "value": ip})
        except (dns.exception.DNSException, dns.resolver.NoAnswer):
            pass

    except dns.exception.Timeout:
        return None
    except dns.resolver.NXDOMAIN:
        return None
    except dns.resolver.NoNameservers:
        return None
    except Exception:
        return None

    if not ips:
        return None

    return {
        "subdomain": domain,
        "ips": ips,
        "cname": cname,
        "records": records,
    }
