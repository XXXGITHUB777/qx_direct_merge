import requests
import pytz
import concurrent.futures
from datetime import datetime
import time

# ================= 配置区域 =================

# 1. 映射表 (根据你提供的 Blackmatrix7 目录索引进行最终校对)
MY_APP_MAP = {
    # ==============================
    # 重点关注对象 (你刚刚确认的)
    # ==============================
    '饿了么': 'Eleme',          # 修正：你发来的目录里有它，单独加！
    '拼多多': 'Pinduoduo',      # 目录里有，确认
    '微博': 'Weibo',            # 目录里有，确认
    '新浪': 'Sina',             # 目录里有，作为微博的补充
    '美图': 'MeiTu',            # 目录里有，确认
    '滴滴出行': 'DiDi',         # 目录里有，确认

    # ==============================
    # 社交与通讯
    # ==============================
    '微信': 'WeChat',
    'QQ': 'TencentQQ',
    '腾讯全家桶': 'Tencent',     # 兜底所有腾讯系
    '小红书': 'XiaoHongShu',
    '豆瓣': 'DouBan',
    '知乎': 'Zhihu',

    # ==============================
    # 阿里/字节系
    # ==============================
    '支付宝': 'AliPay',
    '阿里全家桶': 'Alibaba',     # 涵盖淘宝/闲鱼/夸克/阿里云盘
    '抖音': 'DouYin',
    '字节全家桶': 'ByteDance',   # 涵盖头条/番茄/剪映

    # ==============================
    # 购物与生活
    # ==============================
    '京东': 'JingDong',
    '美团': 'MeiTuan',
    '盒马': 'HeMa',
    '菜鸟': 'CaiNiao',
    '58同城': '58TongCheng',

    # ==============================
    # 视频与直播
    # ==============================
    '哔哩哔哩': 'BiliBili',
    '快手': 'KuaiShou',
    '斗鱼直播': 'Douyu',        # 蛋播依赖
    '虎牙直播': 'HuYa',         # 蛋播依赖
    'YY直播': 'YYeTs',          # 蛋播依赖

    # ==============================
    # 出行/地图/商旅
    # ==============================
    '高德地图': 'GaoDe',
    '百度全家桶': 'Baidu',       # 涵盖地图/网盘
    '携程旅行': 'XieCheng',
    '同程旅行': 'TongCheng',
    '航旅纵横': 'HangLvZongHeng',

    # ==============================
    # 系统/工具/运营商
    # ==============================
    'Apple服务': 'Apple',
    'AppStore': 'AppStore',
    'iCloud': 'iCloud',
    '微软服务': 'Microsoft',
    '迅飞输入法': 'iFlytek',
    '万能钥匙': 'WiFiMaster',
    'Speedtest': 'Speedtest',
    'WPS办公': 'Kingsoft',
    '迅雷下载': 'Xunlei',
    '中国电信': 'ChinaTelecom',
    '中国联通': 'ChinaUnicom'
}

# 使用 jsDelivr CDN 加速 (极稳)
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
            # 这里的报错很重要，如果报错说明映射名字写错了
            print(f"   [❌ 404] {remark}: 规则名错误或不存在 ({rule_name})")
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
            final_rule = f"{rule_type}, {target}, direct"
            fingerprint = f"{rule_type},{target}".lower()
            processed_rules.append((fingerprint, final_rule))
            
    return processed_rules

def main():
    print(f"🚀 启动自动构建 (精准匹配版)...")
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
                    print(f"[{completed}/{total}] ✅ {remark} ({rule_name}) -> 新增 {added} 条")
                else:
                    pass 
            except Exception as exc:
                print(f"[{completed}/{total}] 💥 {remark} 异常: {exc}")

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
        f"# hydirect.list (Verified Edition)",
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
