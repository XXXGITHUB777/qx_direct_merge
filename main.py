import requests
import pytz
import concurrent.futures
from datetime import datetime
import time

# ================= 配置区域 =================

# 1. 瘦身后的映射表 (已剔除 Microsoft, Speedtest, QQ, 航旅纵横)
MY_APP_MAP = {
    # ==============================
    # 社交与通讯
    # ==============================
    '微信': 'WeChat',
    '腾讯全家桶': 'Tencent',     # 包含 QQ/微信/元宝/王者 等所有腾讯系，无需单独加QQ
    '微博': 'Weibo',
    '新浪': 'Sina',             # 微博配套
    '小红书': 'XiaoHongShu',
    '豆瓣': 'DouBan',
    '知乎': 'Zhihu',

    # ==============================
    # 阿里/字节系
    # ==============================
    '支付宝': 'AliPay',
    '阿里全家桶': 'Alibaba',     # 涵盖淘宝/闲鱼/夸克/饿了么
    '抖音': 'DouYin',
    '字节全家桶': 'ByteDance',   # 涵盖头条/番茄/剪映

    # ==============================
    # 购物与生活
    # ==============================
    '京东': 'JingDong',
    '拼多多': 'Pinduoduo',
    '美团': 'MeiTuan',
    '盒马': 'HeMa',
    '菜鸟': 'CaiNiao',
    '58同城': '58TongCheng',
    # 饿了么已包含在 Alibaba 全家桶中，脚本会自动处理，这里不重复写

    # ==============================
    # 视频与直播
    # ==============================
    '哔哩哔哩': 'BiliBili',
    '快手': 'KuaiShou',
    '斗鱼直播': 'Douyu',
    '虎牙直播': 'HuYa',
    'YY直播': 'YYeTs',

    # ==============================
    # 出行/地图
    # ==============================
    '高德地图': 'GaoDe',
    '百度全家桶': 'Baidu',
    '携程旅行': 'XieCheng',
    '同程旅行': 'TongCheng',
    '滴滴出行': 'DiDi',

    # ==============================
    # 系统/工具 (已剔除 Microsoft, Speedtest)
    # ==============================
    'Apple服务': 'Apple',       # 包含 AppStore/iCloud/固件
    '美图系列': 'MeiTu',
    '迅飞输入法': 'iFlytek',
    '万能钥匙': 'WiFiMaster',
    'WPS办公': 'Kingsoft',
    '迅雷下载': 'Xunlei',

    # ==============================
    # 运营商
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
            # 404 就跳过，不强求
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
        
        # === 核心改动：极简模式 ===
        # 只保留 HOST (域名) 相关规则
        # ❌ 彻底剔除 IP-CIDR (IP地址)，这会让规则体积减小 60% 以上！
        if rule_type in ["HOST", "HOST-SUFFIX", "HOST-KEYWORD", "USER-AGENT"]:
            final_rule = f"{rule_type}, {target}, direct"
            fingerprint = f"{rule_type},{target}".lower()
            processed_rules.append((fingerprint, final_rule))
            
    return processed_rules

def main():
    print(f"🚀 启动自动构建 (极简瘦身版)...")
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
                    # 如果新增0条，可能是全被去重了，也可能是全是IP被过滤了
                    print(f"[{completed}/{total}] ✅ {remark} -> 新增 {added} 条 (纯域名)")
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
        f"# hydirect.list (Slim Domain Only)",
        f"# 更新时间: {now}",
        f"# 规则总数: {len(sorted_rules)}",
        f"# 策略: 强制 DIRECT (已剔除IP规则，保留纯域名)",
        ""
    ]
    
    with open("hydirect.list", "w", encoding="utf-8") as f:
        f.write("\n".join(header))
        f.write("\n".join(sorted_rules))
        
    print(f"🎉 文件生成成功")

if __name__ == "__main__":
    main()
