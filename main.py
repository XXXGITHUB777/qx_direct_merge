import requests
import pytz
from datetime import datetime

# ================= 1. 经过全库匹配验证的映射表 =================
#这是基于你239个App列表，与Blackmatrix7全库比对后生成的精准名单
#已自动剔除 Pinterest/Tumblr 等必须走代理的App
#已自动补全 蛋播星球依赖(直播源) 和 潜在办公需求(WPS/迅雷)

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

    # --- 阿里系 (全家桶+单品) ---
    '支付宝': 'AliPay',
    '阿里全家桶': 'Alibaba', # 涵盖淘宝/闲鱼/夸克/阿里云盘/优酷
    # 脚本会自动去重，所以这里虽然有重叠，但能保证规则最全

    # --- 字节系 (全家桶+单品) ---
    '抖音': 'DouYin',
    '抖音极速版': 'DouYin',
    '字节全家桶': 'ByteDance', # 涵盖头条/番茄/剪映/海螺/即梦AI

    # --- 购物与生活 ---
    '京东': 'JingDong',
    '拼多多': 'Pinduoduo',
    '美团': 'MeiTuan', # 含猫眼
    '盒马': 'HeMa',
    '菜鸟': 'CaiNiao',
    '58同城': '58TongCheng',

    # --- 视频与直播 (含蛋播依赖) ---
    '哔哩哔哩': 'BiliBili',
    '快手': 'KuaiShou',
    '斗鱼直播': 'Douyu', # 蛋播依赖
    '虎牙直播': 'HuYa',  # 蛋播依赖
    'YY直播': 'YYeTs',   # 蛋播依赖

    # --- 出行与地图 ---
    '高德地图': 'GaoDe',
    '百度全家桶': 'Baidu', # 涵盖地图/网盘/贴吧/搜索
    '滴滴出行': 'DiDi',
    '花小猪': 'DiDi',
    '携程旅行': 'XieCheng',
    '同程旅行': 'TongCheng', # 含智行
    '航旅纵横': 'Umetrip',

    # --- 工具/系统/潜在需求 ---
    'Apple服务': 'Apple',
    'Apple硬件': 'AppleFirmware',
    'AppStore': 'AppStore',
    'iCloud': 'iCloud',
    'TestFlight': 'TestFlight',
    '爱思助手': 'AppleDev',
    '微软服务': 'Microsoft', # OnePage/Office
    '美图系列': 'MeiTu',     # 美图秀秀/Wink
    '讯飞输入法': 'iFlytek',
    '万能钥匙': 'WiFiMaster',
    'Speedtest': 'Speedtest',
    'WPS办公': 'Kingsoft',
    '迅雷下载': 'Xunlei',

    # --- 运营商 ---
    '中国电信': 'ChinaTelecom',
    '中国联通': 'ChinaUnicom'
}

# ================= 2. 核心逻辑区域 =================

def fetch_and_gen_rules():
    # 核心去重字典：Key=规则指纹, Value=完整规则
    unique_rules = {} 
    
    # 使用 ghproxy 加速下载，确保 GitHub Actions 不会连接超时
    base_url_template = "https://ghproxy.net/https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/QuantumultX/{name}/{name}.list"
    
    headers = {'User-Agent': 'Quantumult%20X/1.0.30'}
    
    print(f"--- 启动自动化构建 (目标源: {len(MY_APP_MAP)} 个) ---")
    
    success_sources = 0
    
    for remark, rule_name in MY_APP_MAP.items():
        url = base_url_template.format(name=rule_name)
        print(f"📥 正在抓取: {remark} ({rule_name}) ...", end="")
        
        try:
            resp = requests.get(url, headers=headers, timeout=20)
            if resp.status_code != 200:
                print(f" [❌ 失败] HTTP {resp.status_code}")
                continue

            lines = resp.text.splitlines()
            new_rules_count = 0
            
            for line in lines:
                line = line.strip()
                # 过滤注释和无效行
                if not line or line.startswith(('#', ';', '//')): continue
                if ',' not in line: continue
                
                parts = [p.strip() for p in line.split(',')]
                if len(parts) < 2: continue
                
                rule_type = parts[0].upper()
                target = parts[1]
                
                # 只保留有效的去广告/分流类型
                if rule_type not in ["HOST", "HOST-SUFFIX", "HOST-KEYWORD", "IP-CIDR", "IP-CIDR6", "USER-AGENT"]:
                    continue

                # ==========================================
                # 核心策略：强制 DIRECT + 自动去重
                # ==========================================
                
                # 1. 强制策略为 direct
                final_rule = f"{rule_type}, {target}, direct"
                
                # 2. 生成唯一指纹 (例如: "host,baidu.com")
                fingerprint = f"{rule_type},{target}".lower()
                
                # 3. 字典去重：如果指纹已存在，通过字典特性自动忽略，实现去重
                if fingerprint not in unique_rules:
                    unique_rules[fingerprint] = final_rule
                    new_rules_count += 1
            
            print(f" [✅ OK] 提取 {new_rules_count} 条")
            success_sources += 1
            
        except Exception as e:
            print(f" [⚠️ 出错] {e}")

    # 转为列表
    final_list = list(unique_rules.values())
    
    print(f"\n📊 统计报告:")
    print(f"   - 成功抓取源: {success_sources} / {len(MY_APP_MAP)}")
    print(f"   - 最终去重后规则数: {len(final_list)}")
    
    return final_list

def sort_priority(line):
    # 优化排序：HOST 放在前面，提高 QX 匹配效率
    if line.startswith("HOST,"): return 1
    if line.startswith("HOST-SUFFIX,"): return 2
    if line.startswith("HOST-KEYWORD,"): return 3
    return 10

def main():
    rules = fetch_and_gen_rules()
    
    if not rules:
        print("❌ 严重错误：未生成任何规则，停止写入！")
        exit(1)

    # 排序
    sorted_rules = sorted(rules, key=sort_priority)
    
    # 获取北京时间
    tz = pytz.timezone('Asia/Shanghai')
    now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
    
    # 文件头注释
    header = [
        f"# hydirect.list (Your Custom Direct List)",
        f"# 更新时间: {now}",
        f"# 规则总数: {len(sorted_rules)} (已去重)",
        f"# 适用场景: iPhone 11 极致省电 + 蛋播/WPS/直播兼容",
        f"# 策略: 强制 DIRECT (直连)",
        ""
    ]
    
    # 写入文件
    with open("hydirect.list", "w", encoding="utf-8") as f:
        f.write("\n".join(header))
        f.write("\n".join(sorted_rules))
        
    print(f"\n🎉 文件生成成功: hydirect.list")

if __name__ == "__main__":
    main()
