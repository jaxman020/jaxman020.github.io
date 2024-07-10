import base64
import json
import ccxt
import asyncio
import re

def decode_vmess(vmess_url):
    encoded = vmess_url.split('://')[-1]
    decoded = base64.b64decode(encoded).decode('utf-8')
    return json.loads(decoded)

def create_proxy_config(protocol, server, port):
    return f'{protocol}://{server}:{port}'

def parse_ss_url(ss_url):
    parts = ss_url.split('@')
    server_port = parts[1].split('#')[0].split(':')
    return server_port[0], int(server_port[1])

async def test_proxy(exchange_class, proxy):
    try:
        exchange = exchange_class({
            'proxies': {
                'http': proxy,
                'https': proxy
            },
            'timeout': 10000,
            'enableRateLimit': True,
        })
        await exchange.load_markets()
        print(f"代理可用: {proxy}")
        return True
    except Exception as e:
        print(f"代理不可用: {proxy}")
        print(f"错误: {str(e)}")
        return False

def extract_urls(content):
    ss_pattern = r'ss://[A-Za-z0-9+/=]+@[^#\s]+(?:#[^\s]+)?'
    vmess_pattern = r'vmess://[A-Za-z0-9+/=]+'
    trojan_pattern = r'trojan://[^#\s]+(?:#[^\s]+)?'
    
    ss_urls = re.findall(ss_pattern, content)
    vmess_urls = re.findall(vmess_pattern, content)
    trojan_urls = re.findall(trojan_pattern, content)
    
    return ss_urls, vmess_urls, trojan_urls

async def main():
    # 读取1.txt文件
    with open('1.txt', 'r', encoding='utf-8') as file:
        content = file.read()

    # 解析文件中的代理URL
    ss_urls, vmess_urls, trojan_urls = extract_urls(content)

    proxies = []

    # 解析SS协议
    for ss_url in ss_urls:
        server, port = parse_ss_url(ss_url)
        proxies.append(create_proxy_config('socks5', server, port))

    # 解析VMess协议
    for vmess_url in vmess_urls:
        try:
            vmess_info = decode_vmess(vmess_url)
            proxies.append(create_proxy_config('http', vmess_info['add'], vmess_info['port']))
        except:
            print(f"无法解析VMess URL: {vmess_url}")

    # 解析Trojan协议
    for trojan_url in trojan_urls:
        try:
            server_port = trojan_url.split('@')[1].split('#')[0].split(':')
            proxies.append(create_proxy_config('http', server_port[0], server_port[1]))
        except:
            print(f"无法解析Trojan URL: {trojan_url}")

    # 测试代理
    exchange_class = ccxt.binance
    tasks = [test_proxy(exchange_class, proxy) for proxy in proxies]
    results = await asyncio.gather(*tasks)

    working_proxies = [proxy for proxy, result in zip(proxies, results) if result]
    print(f"\n可用代理数量: {len(working_proxies)}")
    for proxy in working_proxies:
        print(proxy)

if __name__ == '__main__':
    asyncio.run(main())