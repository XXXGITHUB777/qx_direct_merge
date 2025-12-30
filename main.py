import requests
import pytz
import concurrent.futures
from datetime import datetime
import time

# ================= 配置区域 =================

# 核心策略：【拆包】
# 哪怕是腾讯阿里，也只取核心App。其他的靠 GEOIP 兜底。
MY_APP_MAP = {
    # ==============================
    # 社交 (只留核心)
    # ==============================
    '微信': 'WeChat',
    'QQ': 'TencentQQ',          # 抛弃 Tencent 全家桶(2500条)，只留 QQ
    '微博': 'Weibo',
    '新浪': 'Sina',
    '小红书': 'XiaoHongShu',
    '豆瓣': 'DouBan',
    '知乎': 'Zhihu',

    # ==============================
    # 支付与购物 (只留核心)
    # ==============================
    '支付宝': 'AliPay',
    '淘宝': 'Taobao',           # 抛弃 Alibaba 全家桶(1300条)，只留淘宝
    '京东': 'JingDong',
    '拼多多': 'Pinduoduo',
    '美团': 'MeiTuan',
    '盒马': 'HeMa',
    '菜鸟': 'CaiNiao',
    '58同城': '58TongCheng',
    '饿了么': 'Eleme',

    # ==============================
    # 视频 (只留核心)
    # ==============================
    '抖音': 'DouYin',           # 抛弃 ByteDance 全家桶，只留抖音
    '快手': 'KuaiShou',         # 快手域名确实多，但为了视频流畅建议保留
    '哔哩哔哩': 'BiliBili',
    # 蛋播依赖 (保留，否则直播卡)
    '斗鱼直播': 'Douyu',
    '虎牙直播': 'HuYa',
    'YY直播': 'YYeTs',

    # ==============================
    # 出行 (只留核心)
    # ==============================
    '高德地图': 'GaoDe',
    '滴滴出行': 'DiDi',
    '携程旅行': 'XieCheng',
    '同程旅行': 'TongCheng',
    # 百度全家桶才200条，不算大，保留以防地图和网盘出问题
    '百度全家桶': 'Baidu',       

    # ==============================
    # 系统/工具 (剔除大体积 Apple)
    # ==============================
    'AppStore': 'AppStore',     # 抛弃 Apple (1800条)，只留商店
    'iCloud': 'iCloud',         # 只留云盘同步
    'WPS办公': 'Kingsoft',
    '迅雷下载': 'Xunlei',
    '美图系列': 'MeiTu',
    '迅飞输入法': 'iFlytek',
    '万能钥匙': 'WiFiMaster',

    # ==============================
    # 运营商 (必须保留，否则信号栏跳动)
    # ==============================
    '中国电信': 'ChinaTelecom',
    '中国联通': 'ChinaUnicom'
}

BASE_URL = "https://cdn.jsdelivr.net/gh/blackmatrix7/ios_rule_script@master/rule/QuantumultX/{name}/{name}.list"

# ================= 逻辑区域 =================

def download_single_rule(item):
    remark, rule_name = item
    url = BASE_URL.format(name=rule_name)
    headers = {'User-Agent': 'Quantumult%20X/1.0.30'}
    
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            return (rule_name, resp.text)
        else:
            return (rule_name, None)
    except Exception:
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
        
        # 依旧只保留域名，剔除 IP
        if rule_type in ["HOST", "HOST-SUFFIX", "HOST-KEYWORD", "USER-AGENT"]:
            final_rule = f"{rule_type}, {target}, direct"
            fingerprint = f"{rule_type},{target}".lower()
            processed_rules.append((fingerprint, final_rule))
            
    return processed_rules

def main():
    print(f"🚀 启动自动构建 (Ultra Lite 拆包版)...")
    start_time = time.time()
    
    unique_rules = {} 
    tasks = list(MY_APP_MAP.items())
    
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
                    pass 
            except Exception:
                pass

    sorted_rules = sorted(unique_rules.values(), key=lambda x: (x.split(',')[0], x.split(',')[1]))
    
    duration = time.time() - start_time
    print(f"\n⏱️ 耗时: {duration:.2f} 秒")
    print(f"📊 规则总数: {len(sorted_rules)}")
    
    if not sorted_rules:
        exit(1)

    tz = pytz.timezone('Asia/Shanghai')
    now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
    
    header = [
        f"# hydirect.list (Ultra Lite)",
        f"# 更新时间: {now}",
        f"# 规则总数: {len(sorted_rules)}",
        f"# 策略: 强制 DIRECT (精简拆包 + 纯域名)",
        ""
    ]
    
    with open("hydirect.list", "w", encoding="utf-8") as f:
        f.write("\n".join(header))
        f.write("\n".join(sorted_rules))
        
    print(f"🎉 文件生成成功")

if __name__ == "__main__":
    main()
