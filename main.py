import requests
import pytz
import json
import os
import concurrent.futures
from datetime import datetime
import time

# ================= 配置区域 =================

# 你的 APP 关键词列表 (左边是你的App名，右边是匹配规则的关键词)
# 注意：右边的关键词必须是 Blackmatrix7 规则名的一部分
MY_APPS = {
    # --- 社交 ---
    '微信': 'WeChat',
    'QQ': 'TencentQQ',
    '微博': 'Weibo',
    '小红书': 'XiaoHongShu',
    '豆瓣': 'DouBan',
    '知乎': 'Zhihu',

    # --- 全家桶 ---
    '支付宝': 'AliPay',
    '阿里全家桶': 'Alibaba',
    '腾讯全家桶': 'Tencent',
    '字节全家桶': 'ByteDance',
    '百度全家桶': 'Baidu',

    # --- 购物 ---
    '京东': 'JingDong',
    '拼多多': 'Pinduoduo',
    '美团': 'MeiTuan',
    '盒马': 'HeMa',
    '菜鸟': 'CaiNiao',
    '58同城': '58TongCheng',

    # --- 视频 ---
    '哔哩哔哩': 'BiliBili',
    '快手': 'KuaiShou',
    '斗鱼': 'Douyu',
    '虎牙': 'HuYa',
    'YY': 'YYeTs',

    # --- 出行 ---
    '高德': 'GaoDe',
    '滴滴': 'DiDi',
    '携程': 'XieCheng',
    '同程': 'TongCheng',
    '航旅纵横': 'Umetrip',

    # --- 工具 ---
    'Apple': 'Apple',
    'AppStore': 'AppStore',
    'iCloud': 'iCloud',
    'Microsoft': 'Microsoft',
    'WPS': 'Kingsoft',
    '迅雷': 'Xunlei',
    '美图': 'MeiTu',
    '万能钥匙': 'WiFiMaster',
    'Speedtest': 'Speedtest',
    '迅飞': 'iFlytek',

    # --- 运营商 ---
    '电信': 'ChinaTelecom',
    '联通': 'ChinaUnicom'
}

# ================= 逻辑区域 =================

def load_rules_json():
    """读取 rules.json 文件"""
    if not os.path.exists('rules.json'):
        print("❌ 错误：未找到 rules.json 文件！请先运行油猴脚本提取链接。")
        return None
    
    with open('rules.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def get_download_url(keyword, rules_dict):
    """根据关键词在 JSON 中查找对应的 URL"""
    # 精确匹配优先
    if keyword in rules_dict:
        return keyword, rules_dict[keyword]
    
    # 模糊匹配 (比如 keyword='WeChat' 能匹配到 'WeChat')
    for name, url in rules_dict.items():
        if keyword.lower() == name.lower():
            return name, url
            
    return None, None

def download_rule(task):
    """下载单个规则"""
    app_name, rule_name, url = task
    headers = {'User-Agent': 'Quantumult%20X/1.0.30'}
    
    try:
        # 使用 10秒 超时
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            return (app_name, rule_name, resp.text)
        else:
            print(f"   [❌ 失败] {app_name}: HTTP {resp.status_code}")
            return None
    except Exception as e:
        print(f"   [⚠️ 超时] {app_name}: {e}")
        return None

def process_content(content):
    """提取规则并强制 Direct"""
    processed = []
    lines = content.splitlines()
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
            processed.append((fingerprint, final_rule))
            
    return processed

def main():
    # 1. 加载本地 JSON
    rules_dict = load_rules_json()
    if not rules_dict: return

    # 2. 构建任务列表
    tasks = []
    print(f"🔍 正在匹配链接 (共 {len(MY_APPS)} 个目标)...")
    
    for app_name, keyword in MY_APPS.items():
        rule_name, url = get_download_url(keyword, rules_dict)
        if url:
            tasks.append((app_name, rule_name, url))
        else:
            print(f"   [⚠️ 未找到] {app_name} (关键词: {keyword}) - 请检查 JSON")

    print(f"\n🚀 启动多线程下载 (任务数: {len(tasks)})...")
    
    unique_rules = {}
    start_time = time.time()
    
    # 3. 多线程下载
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(download_rule, task) for task in tasks]
        
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                app_name, rule_name, content = result
                
                # 处理内容
                extracted = process_content(content)
                count_new = 0
                for fp, rule in extracted:
                    if fp not in unique_rules:
                        unique_rules[fp] = rule
                        count_new += 1
                
                print(f"   [✅ OK] {app_name} ({rule_name}) -> 新增 {count_new} 条")

    # 4. 生成文件
    sorted_rules = sorted(unique_rules.values(), key=lambda x: (x.split(',')[0], x.split(',')[1]))
    duration = time.time() - start_time
    
    tz = pytz.timezone('Asia/Shanghai')
    now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
    
    header = [
        f"# hydirect.list (JSON Local Mode)",
        f"# 更新时间: {now}",
        f"# 耗时: {duration:.2f}s",
        f"# 规则总数: {len(sorted_rules)}",
        f"# 策略: 强制 DIRECT (直连)",
        ""
    ]
    
    with open("hydirect.list", "w", encoding="utf-8") as f:
        f.write("\n".join(header))
        f.write("\n".join(sorted_rules))
        
    print(f"\n🎉 成功！已生成 hydirect.list，共 {len(sorted_rules)} 条规则。")

if __name__ == "__main__":
    main()
