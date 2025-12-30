import requests
import pytz
import concurrent.futures
from datetime import datetime
import time

# ================= 配置区域 =================

# 1. 修正后的映射表 (修复了 QQ 和 航旅纵横)
MY_APP_MAP = {
    # --- 社交与通讯 ---
    '微信': 'WeChat',
    'QQ': 'TencentQQ',          # 如果这个还报错，下面的 Tencent 全家桶会兜底
    '腾讯全家桶': 'Tencent',     # 包含 QQ/微信/元宝 等所有腾讯系
    '微博': 'Weibo',
    '小红书': 'XiaoHongShu',
    '豆瓣': 'DouBan',
    '知乎': 'Zhihu',

    # --- 阿里系 ---
    '支付宝': 'AliPay',
    '阿里全家桶': 'Alibaba',     # 包含 淘宝/闲鱼/夸克/阿里云盘/优酷

    # --- 字节系 ---
    '抖音': 'DouYin',
    '字节全家桶': 'ByteDance',   # 包含 头条/番茄/剪映/海螺/即梦AI

    # --- 购物与生活 ---
    '京东': 'JingDong',
    '拼多多': 'Pinduoduo',
    '美团': 'MeiTuan',
    '盒马': 'HeMa',
    '菜鸟': 'CaiNiao',
    '58同城': '58TongCheng',

    # --- 视频与直播 ---
    '哔哩哔哩': 'BiliBili',
    '快手': 'KuaiShou',
    '斗鱼直播': 'Douyu',
    '虎牙直播': 'HuYa',
    'YY直播': 'YYeTs',

    # --- 出行与地图 ---
    '高德地图': 'GaoDe',
    '百度全家桶': 'Baidu',
    '滴滴出行': 'DiDi',
    '携程旅行': 'XieCheng',
    '同程旅行': 'TongCheng',
    '航旅纵横': 'HangLvZongHeng', # 修正：原来叫 Umetrip，现在改用拼音匹配

    # --- 工具/系统 ---
    'Apple服务': 'Apple',
    'Apple硬件': 'AppleFirmware', # 修正：AppleFirmware 有时会归入 Apple，保留无妨
    'AppStore': 'AppStore',
    'iCloud': 'iCloud',
    'TestFlight': 'TestFlight',
    '爱思助手': 'AppleDev',
    '微软服务': 'Microsoft',
    '美图系列': 'MeiTu',
    '讯飞输入法': 'iFlytek',
    '万能钥匙': 'WiFiMaster',
    'Speedtest': 'Speedtest',
    'WPS办公': 'Kingsoft',
    '迅雷下载': 'Xunlei',

    # --- 运营商 ---
    '中国电信': 'ChinaTelecom',
    '中国联通': 'ChinaUnicom'
}

# 2. 核心修改：使用 jsDelivr CDN (极速、稳定、不需翻墙)
BASE_URL = "https://cdn.jsdelivr.net/gh/blackmatrix7/ios_rule_script@master/rule/QuantumultX/{name}/{name}.list"

# ================= 逻辑区域 =================

def download_single_rule(item):
    remark, rule_name = item
    url = BASE_URL.format(name=rule_name)
    headers = {'User-Agent': 'Quantumult%20X/1.0.30'}
    
    try:
        # CDN 速度很快，5秒超时足够
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            return (rule_name, resp.text)
        else:
            # 如果是404，说明规则名可能变了
            print(f"   [❌ 404] {remark}: 规则名可能错误 ({rule_name})")
            return (rule_name, None)
    except Exception as e:
        print(f"   [⚠️ 超时] {remark}: {e}")
        return (rule_name, None)

def process_rules(raw_text):
    processed_rules = []
    lines = raw_text.splitlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith(('#', ';', '//')) or ',' not in line:
            continue
        
        parts = [p.strip() for p in line.split(',')]
        if len(parts) < 2: continue
        
        rule_type = parts[0].upper()
        target = parts[1]
        
        if rule_type in ["HOST", "HOST-SUFFIX", "HOST-KEYWORD", "IP-CIDR", "IP-CIDR6", "USER-AGENT"]:
            # 强制 Direct
            final_rule = f"{rule_type}, {target}, direct"
            fingerprint = f"{rule_type},{target}".lower()
            processed_rules.append((fingerprint, final_rule))
            
    return processed_rules

def main():
    print(f"🚀 启动 GitHub Action 自动构建 (CDN模式)...")
    start_time = time.time()
    
    unique_rules = {} 
    tasks = list(MY_APP_MAP.items())
    
    # 多线程下载
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_rule = {executor.submit(download_single_rule, item): item for item in tasks}
        
        completed = 0
        total = len(tasks)
        
        for future in concurrent.futures.as_completed(future_to_rule):
            completed += 1
            remark = future_to_rule[future][0]
            try:
                rule_name, content = future.result()
                if content:
                    rules_list = process_rules(content)
                    count_before = len(unique_rules)
                    
                    for fp, rule in rules_list:
                        if fp not in unique_rules:
                            unique_rules[fp] = rule
                            
                    added = len(unique_rules) - count_before
                    print(f"[{completed}/{total}] ✅ {remark} -> 新增 {added} 条")
                else:
                    pass # 错误信息已在下载函数中打印
            except Exception as exc:
                print(f"[{completed}/{total}] 💥 {remark} 异常: {exc}")

    # 排序与写入
    sorted_rules = sorted(unique_rules.values(), key=lambda x: (x.split(',')[0], x.split(',')[1]))
    
    duration = time.time() - start_time
    print(f"\n⏱️ 耗时: {duration:.2f} 秒")
    print(f"📊 规则总数: {len(sorted_rules)}")
    
    if not sorted_rules:
        print("❌ 错误：未生成任何规则！")
        exit(1)

    tz = pytz.timezone('Asia/Shanghai')
    now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
    
    header = [
        f"# hydirect.list (CDN Auto Build)",
        f"# 更新时间: {now}",
        f"# 规则总数: {len(sorted_rules)}",
        f"# 策略: 强制 DIRECT (直连)",
        ""
    ]
    
    with open("hydirect.list", "w", encoding="utf-8") as f:
        f.write("\n".join(header))
        f.write("\n".join(sorted_rules))
        
    print(f"🎉 文件生成成功: hydirect.list")

if __name__ == "__main__":
    main()
