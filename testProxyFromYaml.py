import yaml
import base64
import json
import ccxt
import asyncio
import re

def create_proxy_config(protocol, server, port):
    return f'{protocol}://{server}:{port}'

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

def parse_yaml_proxies(content):
    try:
        data = yaml.safe_load(content)
        if 'proxies' in data:
            return data['proxies']
        return []
    except yaml.YAMLError as e:
        print(f"解析YAML时出错: {e}")
        return []

def extract_proxy_info(proxy):
    server = proxy.get('server')
    port = proxy.get('port')
    proxy_type = proxy.get('type')

    if not all([server, port, proxy_type]):
        return None

    if proxy_type == 'ss':
        return create_proxy_config('socks5', server, port)
    elif proxy_type in ['vmess', 'trojan']:
        return create_proxy_config('http', server, port)
    else:
        return None

async def main():
    # 读取文件
    with open('clash.yaml', 'r', encoding='utf-8') as file:
        content = file.read()

    # 解析YAML格式的代理
    proxies_data = parse_yaml_proxies(content)

    proxies = []
    for proxy in proxies_data:
        proxy_config = extract_proxy_info(proxy)
        if proxy_config:
            proxies.append(proxy_config)

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