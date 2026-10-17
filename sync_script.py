import os
import urllib.parse
import requests

# ================= 配置区域 =================
LIST_FILE = "gkd_subscribe_list.txt"
OUTPUT_DIR = "dist"
OUTPUT_CDN_LIST = "output_cdn_list.txt"

# 🧬 动态感知当前的 GitHub 仓库（格式如: wapython/gkd_rule_private）
GITHUB_REPO = os.environ.get("GITHUB_REPOSITORY", "wapython/gkd_rule_private")
# ============================================

os.makedirs(OUTPUT_DIR, exist_ok=True)

def fetch_links_from_list():
    """从本地 txt 文件中读取所有有效的订阅源链接"""
    if not os.path.exists(LIST_FILE):
        print(f"❌ 错误: 找不到列表文件 {LIST_FILE}")
        return []
    
    links = []
    with open(LIST_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                links.append(line)
    return links

def download_and_get_cdn_url(url):
    """下载文件（成功则更新，失败则沿用老文件），并返回对应的 jsDelivr CDN 直链"""
    try:
        # 1. 解析 URL，提取作者名和原始文件名
        parsed_url = urllib.parse.urlparse(url)
        path_parts = parsed_url.path.strip("/").split("/")

        if len(path_parts) >= 2:
            author = path_parts[0]
            filename = path_parts[-1]
            local_filename = f"{author}_{filename}"
        else:
            local_filename = path_parts[-1]

        local_path = os.path.join(OUTPUT_DIR, local_filename)
        
        # 🎯 完美路径拼接：精准生成不惧怕风控、国内秒开的 jsDelivr CDN 标准免登录直链
        jsdelivr_cdn_url = f"https://cdn.jsdelivr.net/gh/{GITHUB_REPO}@main/{OUTPUT_DIR}/{local_filename}"

        # 2. 尝试下载新文件
        try:
            print(f"正在下载: {url} -> {local_path}")
            res = requests.get(url, timeout=15)
            res.raise_for_status()
            
            # 下载成功，执行写入/覆盖更新
            with open(local_path, "w", encoding="utf-8") as f:
                f.write(res.text)
            print(f"✅ 成功同步并更新: {local_filename}")
            return jsdelivr_cdn_url

        except Exception as download_error:
            print(f"⚠️ 下载失败 [{url}]: {download_error}")
            
            # 3. 容灾机制：如果下载失败，检查本地是否已经有历史老文件
            if os.path.exists(local_path):
                print(f"ℹ️ 容灾触发: 成功检测到本地历史老文件 {local_filename}，拒绝删除，将继续沿用。")
                return jsdelivr_cdn_url
            else:
                print(f"❌ 容灾失败: 本地亦无历史缓存，该订阅源本次将被完全剔除。")
                return None

    except Exception as e:
        print(f"❌ 脚本核心逻辑错误 [{url}]: {e}")
        return None

if __name__ == "__main__":
    print("==========================================")
    print("开始执行 GKD 订阅源批量同步脚本 (jsDelivr CDN 专属版)...")
    print(f"当前运行仓库: {GITHUB_REPO}")
    print("==========================================")
    
    target_links = fetch_links_from_list()
    print(f"共找到 {len(target_links)} 个待同步的链接。")

    cdn_urls = []
    for link in target_links:
        cdn_url = download_and_get_cdn_url(link)
        if cdn_url:
            cdn_urls.append(cdn_url)

    # 4. 将所有有效存活的 CDN 直链写入到 output_cdn_list.txt
    if cdn_urls:
        with open(OUTPUT_CDN_LIST, "w", encoding="utf-8") as f:
            for url in cdn_urls:
                f.write(url + "\n")
        print(f"📝 成功将 {len(cdn_urls)} 个有效 CDN 直链导出至 {OUTPUT_CDN_LIST}")
    else:
        if os.path.exists(OUTPUT_CDN_LIST):
            os.remove(OUTPUT_CDN_LIST)
        print("⚠️ 未能生成任何有效的 CDN 直链，已清理旧列表文件。")

    print("🎉 所有文件处理完毕！")
