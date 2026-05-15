#!/usr/bin/env python3
"""
从指定URL下载skill zip包，提取并返回skill元信息（名称、描述、类型、安装路径、下载量）。
输出JSON格式结果。
"""
import sys
import os
import json
import re
import urllib.request
import urllib.error
import zipfile
import tempfile
import shutil
from pathlib import Path


def detect_skills_directory():
    """自动检测skills目录，与 skill-recommender 保持一致。"""
    script_path = Path(__file__).resolve()
    # scripts/get_skill_meta.py -> skill-tester -> skills
    skills_dir = script_path.parent.parent.parent

    if '.openclaw' in skills_dir.parts:
        env_name = "OpenClaw"
    elif '.claude' in skills_dir.parts:
        env_name = "Ducc"
    else:
        parent_dir = skills_dir.parent.name
        env_name = parent_dir[1:].capitalize() if parent_dir.startswith('.') else "Custom Agent"

    return skills_dir, env_name


DEFAULT_SKILLS_DIR, ENVIRONMENT_NAME = detect_skills_directory()


def resolve_zip_url(url):
    """
    若传入的是 clawhub 页面 URL（HTML），自动提取真实的 zip 下载链接。
    若本身就是 zip 直链，直接返回原 URL。
    """
    # 如果 URL 已经包含明确的下载路径标志，直接返回
    if any(x in url for x in ['.zip', '/download', 'download?']):
        return url

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            content_type = resp.headers.get('Content-Type', '')
            raw = resp.read()

        # 返回的是 zip/octet-stream，说明本身就是下载链接
        if 'zip' in content_type or 'octet-stream' in content_type:
            # 把已读内容写回临时文件再交给调用方会比较麻烦，
            # 直接返回原 URL 让 download_zip 再请求一次（数据量小，可接受）
            return url

        # 尝试从 HTML 中解析 zip 下载链接
        html = raw.decode('utf-8', errors='ignore')

        # 匹配形如 href="https://...download..." 或 Download zip 附近的链接
        patterns = [
            r'href=["\']([^"\']*(?:download)[^"\']*)["\']',
            r'href=["\']([^"\']+\.zip)["\']',
        ]
        for pat in patterns:
            matches = re.findall(pat, html, re.IGNORECASE)
            for m in matches:
                # 过滤掉锚点、页面内导航等无效值
                if m.startswith('http') and ('download' in m or m.endswith('.zip')):
                    return m

        print(f"警告: 无法从页面解析 zip 下载链接，将直接尝试原始 URL", file=sys.stderr)
        return url

    except Exception as e:
        print(f"解析页面 URL 失败: {e}，将直接尝试原始 URL", file=sys.stderr)
        return url


def download_zip(url, dest_path):
    """从 URL 下载文件到 dest_path。自动处理页面 URL 和 zip 直链。"""
    zip_url = resolve_zip_url(url)
    if zip_url != url:
        print(f"已从页面解析出 zip 地址: {zip_url}", file=sys.stderr)
    try:
        req = urllib.request.Request(zip_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=60) as response:
            with open(dest_path, 'wb') as f:
                f.write(response.read())
        return True
    except Exception as e:
        print(f"下载失败: {e}", file=sys.stderr)
        return False


def infer_skill_type(description, overview):
    """根据 skill 描述和正文推断 skill 类型。"""
    text = (description + " " + overview).lower()
    if any(kw in text for kw in ['writing', '写作', '文章', '写文', 'essay', 'prose', 'author']):
        return "Writing"
    if any(kw in text for kw in ['code', 'coding', '编程', '开发', 'programming', 'debug', 'software']):
        return "Coding"
    if any(kw in text for kw in ['research', '分析', '报告', 'analysis', 'report', 'academic', '学术']):
        return "Research"
    return "General"


def extract_meta(zip_path, skill_name):
    """
    从 zip 包解压后读取 SKILL.md 和 _meta.json，返回元信息 dict。
    """
    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp()
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(temp_dir)

        skill_dir = Path(temp_dir) / skill_name
        if not skill_dir.exists():
            # 尝试找到解压后的第一个目录
            subdirs = [p for p in Path(temp_dir).iterdir() if p.is_dir()]
            if subdirs:
                skill_dir = subdirs[0]
                skill_name = skill_dir.name

        skill_md = skill_dir / "SKILL.md"
        meta_json = skill_dir / "_meta.json"

        info = {
            "name": skill_name,
            "description": "",
            "overview": "",
            "skill_type": "General",
            "install_path": str(DEFAULT_SKILLS_DIR / skill_name),
            "downloads": "未知",
            "environment": ENVIRONMENT_NAME
        }

        # 解析 SKILL.md
        if skill_md.exists():
            content = skill_md.read_text(encoding='utf-8')
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    frontmatter = parts[1]
                    body = parts[2].strip()
                    for line in frontmatter.strip().split('\n'):
                        if line.startswith('name:'):
                            info['name'] = line.split(':', 1)[1].strip().strip('"\'')
                        elif line.startswith('description:'):
                            info['description'] = line.split(':', 1)[1].strip().strip('"\'')
                    # 取正文前 500 字作为 overview
                    info['overview'] = body[:500]
            else:
                info['overview'] = content[:500]

        # 解析 _meta.json（下载量）
        if meta_json.exists():
            try:
                meta = json.loads(meta_json.read_text(encoding='utf-8'))
                # 平台字段可能为 downloadCount / downloads / publishedAt 等，按需取
                info['downloads'] = meta.get('downloadCount', meta.get('downloads', '未知'))
                if info['downloads'] == 'N/A':
                    info['downloads'] = '未知'
            except Exception:
                pass

        info['skill_type'] = infer_skill_type(info['description'], info['overview'])
        return info

    except zipfile.BadZipFile:
        print("无效的 zip 文件", file=sys.stderr)
        return None
    except Exception as e:
        print(f"解析失败: {e}", file=sys.stderr)
        return None
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


def main():
    if len(sys.argv) < 2:
        print("用法: get_skill_meta.py <skill_zip_url> [skill_name]", file=sys.stderr)
        sys.exit(1)

    skill_url = sys.argv[1]
    # skill_name 可选，默认从 URL 最后一段推断
    if len(sys.argv) >= 3:
        skill_name = sys.argv[2]
    else:
        skill_name = skill_url.rstrip('/').split('/')[-1].replace('.zip', '')

    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
        tmp_path = tmp.name

    try:
        if not download_zip(skill_url, tmp_path):
            sys.exit(1)

        info = extract_meta(tmp_path, skill_name)
        if info is None:
            print("无法提取 skill 元信息", file=sys.stderr)
            sys.exit(1)

        print(json.dumps(info, ensure_ascii=False, indent=2))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


if __name__ == "__main__":
    main()
