# GKD 订阅源批量同步、GitHub 瘦身与 jsDelivr CDN 直链全自动生成方案

本项目基于 **GitHub Actions** 与 **Python** 实现，可每 6 小时自动抓取指定的 GKD 规则订阅源，自动重命名防冲突归档至 `dist/` 目录，并**无历史负担地强制覆盖推送同步到 GitHub 仓库**。

同时，本项目**彻底抛弃了容易触发内容违规审查的 Gitee**，全面拥抱免费、免注册、国内高速秒开的 **jsDelivr CDN**。脚本运行后会自动在根目录下输出可以直接在手机 App 内无缝加载的 **CDN 完美直链列表** (`output_cdn_list.txt`)。

为了防止仓库体积因自动化频繁提交而线性膨胀，本项目采用了“Orphan 孤儿分支重置历史”技术。每次运行都会自动擦除过去所有的 Commit 历史，只保留最后 1 条干净的最新提交。此操作**会完美保留包含 README.md 在内的所有本地文件**，让仓库体积永久保持在几百 KB。

---

## 🛠️ 项目架构与运作流程

1. **定时/手动触发**：GitHub Actions 根据 `cron` 定时器（每 6 小时）或用户手动点击 `workflow_dispatch` 启动虚拟机。
2. **批量抓取与命名**：Python 脚本读取 `gkd_subscribe_list.txt`，自动解析并下载目标文件，重命名为 `作者名_文件名.json5` 存入 `dist/` 目录。
3. **容灾更新机制**：尝试下载新文件，若成功则覆盖更新；若失败，检查本地是否存在同名老文件，若存在则跳过并继续沿用老文件（拒绝删除），确保直链绝不崩塌。
4. **CDN 链接静态化**：Python 脚本通过 Actions 环境变量动态获取当前的 GitHub 仓库路径（如 `wapython/gkd_rule_private`），精准拼接出对应的 jsDelivr 官方免登录直链，写入 `output_cdn_list.txt`。
5. **GitHub 瘦身强推**：利用 `git checkout --orphan` 创建全新无历史独立分支，打包包含 `README.md`、`sync_script.py` 在内的所有文件，强推覆盖远程 `main` 分支，彻底清空老旧 Commit。

---

## 📂 核心文件配置

### 1. 待抓取链接列表：`gkd_subscribe_list.txt`

在项目根目录下创建此文件，一行一个填入你想抓取的原始订阅源 URL（支持 `#` 号注释）：

```text
# Lin-arm 规则订阅源
https://raw.githubusercontent.com/Lin-arm/GKD_subscription/main/dist/gkd.json5

```

### 2. 核心自动化脚本：`sync_script.py`

在项目根目录下创建此文件，**全选覆盖**以下代码（全自动生成免受风控干扰的 jsDelivr 直链）：

```python
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

```

### 3. GitHub Actions 工作流：`.github/workflows/batch_sync.yml`

在项目根目录创建 `.github/workflows/batch_sync.yml` 文件，完全覆盖以下高效、干净的纯 GitHub 强推流配置：

```yaml
name: Batch Fetch and Sync with jsDelivr CDN

on:
  schedule:
    # 定时任务：每 6 小时自动执行一次
    - cron: '0 */6 * * *'
  workflow_dispatch:
    # 允许手动点击触发

# 赋予工作流写权限，允许推送代码
permissions:
  contents: write

jobs:
  batch_sync:
    runs-on: ubuntu-latest
    steps:
      # 1. 拉取当前的 GitHub 仓库代码
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      # 2. 初始化 Python 环境
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      # 3. 安装脚本所需的依赖
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install requests

      # 4. 执行 Python 脚本（全自动下载并生成 output_cdn_list.txt）
      - name: Run batch download script
        run: |
          python sync_script.py

      # 5. 【GitHub 端防膨胀】利用 orphan 分支清空老历史，完美保留包括 README 在内的所有文件
      - name: Commit and Force Push to GitHub
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "github-actions[bot]@users.noreply.github.com"
          
          # 创建一个全新且没有历史记录的孤儿分支 temp_branch
          git checkout --orphan temp_branch
          
          # 将当前目录下的所有文件全部加入暂存区
          git add -A
          git commit -m "chore: batch auto-update subscription files without history"
          
          # 删除原有的本地 main 分支并重命名新分支
          git branch -D main
          git branch -m main
          
          # 强推回原 GitHub 仓库，强制抹去所有的老 Commit 历史，但文件一个都不会少
          git push origin main --force

```

---

## 🚀 成果如何使用？

项目部署完成后，GitHub Actions 会完全托管后台运行。

1. 打开您仓库根目录下的 **`output_cdn_list.txt`** 文件。
2. 您会看到由脚本为您自动实时生成的、**国内网络秒开且永不封禁**的全球免费公共 CDN 直链。
3. **直接全选复制**对应的直链，将其粘贴到手机 **GKD App** 的自定义订阅源中即可！
*(例如：`https://cdn.jsdelivr.net/gh/wapython/gkd_rule_private@main/dist/ganlinte_ganlin_gkd.json5`)*

从此项目完全进入全自动、免维护运行状态，仓库体积永远只有几百 KB，直链永不断流。

---
