import requests
import pytz
import concurrent.futures
from datetime import datetime
import time

# ================= 配置区域 =================

# 你的定制化 App 映射表 (已去重、去毒、含依赖)
MY_APP_MAP = {
    # --- 社交与通讯 ---
    '微信': 'WeChat',
    '微信读书': 'WeChat',
    'QQ': 'TencentQQ',
    '腾讯元宝': 'Tencent',
    '微博': 'Weibo',
    '小红书': 'XiaoHongShu',
    '豆瓣': 'DouBan',
    '知乎': 'Zhihu',

    # --- 阿里系 ---
    '支付宝': 'AliPay',
    '阿里全家桶': 'Alibaba', 

    # --- 字节系 ---
    '抖音': 'DouYin',
    '字节全家桶': 'ByteDance', 

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
    '航旅纵横': 'Umetrip',

    # --- 工具/系统 ---
    'Apple服务': 'Apple',
    'Apple硬件': 'AppleFirmware',
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

# 基础链接模板
BASE_URL = "https://ghproxy.net/https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/QuantumultX/{name}/{name}.list"

# ================= 逻辑区域 =================

def download_single_rule(item):
    """
    下载单个规则的函数，用于多线程调用
    """
    remark, rule_name = item
    url = BASE_URL.format(name=rule_name)
    headers = {'User-Agent': 'Quantumult%20X/1.0.30'}
    
    try:
        # 设置 10秒 超时，防止卡死
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            return (rule_name, resp.text)
        else:
            print(f"   [❌ 失败] {remark}: HTTP {resp.status_code}")
            return (rule_name, None)
    except Exception as e:
        print(f"   [⚠️ 超时/错误] {remark}: {e}")
        return (rule_name, None)

def process_rules(raw_text):
    """
    处理文本：提取规则、强制direct、去重
    """
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
            # 生成指纹用于去重
            fingerprint = f"{rule_type},{target}".lower()
            processed_rules.append((fingerprint, final_rule))
            
    return processed_rules

def main():
    print(f"🚀 启动多线程极速下载 (目标: {len(MY_APP_MAP)} 个规则集)...")
    start_time = time.time()
    
    unique_rules = {} # 去重字典
    tasks = list(MY_APP_MAP.items())
    
    # === 多线程执行核心 ===
    # max_workers=10 表示同时下载10个文件
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # 提交所有任务
        future_to_rule = {executor.submit(download_single_rule, item): item for item in tasks}
        
        # 处理结果
        completed = 0
        total = len(tasks)
        
        for future in concurrent.futures.as_completed(future_to_rule):
            completed += 1
            remark = future_to_rule[future][0]
            try:
                rule_name, content = future.result()
                if content:
                    # 解析规则
                    rules_list = process_rules(content)
                    count_before = len(unique_rules)
                    
                    for fp, rule in rules_list:
                        if fp not in unique_rules:
                            unique_rules[fp] = rule
                            
                    added = len(unique_rules) - count_before
                    print(f"[{completed}/{total}] ✅ {remark} ({rule_name}) -> 新增 {added} 条")
                else:
                    print(f"[{completed}/{total}] ⚠️ {remark} 下载内容为空")
            except Exception as exc:
                print(f"[{completed}/{total}] 💥 {remark} 处理异常: {exc}")

    # === 结果统计与写入 ===
    sorted_rules = sorted(unique_rules.values(), key=lambda x: (x.split(',')[0], x.split(',')[1]))
    
    duration = time.time() - start_time
    print(f"\n⏱️ 耗时: {duration:.2f} 秒")
    print(f"📊 最终规则总数: {len(sorted_rules)}")
    
    if not sorted_rules:
        print("❌ 错误：未生成任何规则！")
        exit(1)

    tz = pytz.timezone('Asia/Shanghai')
    now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
    
    header = [
        f"# hydirect.list (Turbo Edition)",
        f"# 更新时间: {now}",
        f"# 耗时: {duration:.2f}s",
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
