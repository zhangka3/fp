#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
步骤5.5: 模板提前分析
在生成飞书文档前，先读取模板分析最新结构，输出：
1. 文档结构（根children列表、块类型分布）
2. 文字排版格式（加粗、颜色等样式）
3. 插入参数（{param} 占位符，如有新增/删减）
4. 插入图片信息（[xxx.png] 占位符列表）

用途：提前发现模板变更，避免生成后发现图片/参数不匹配
"""

import sys, io, json, re
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import requests
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from feishu_creds import FEISHU_CREDENTIALS_HELP, load_feishu_app_credentials

# ==================== 配置 ====================
# 凭证：项目根 feishu_app.json（见 feishu_app.example.json），或环境变量 FEISHU_APP_ID / FEISHU_APP_SECRET
APP_ID, APP_SECRET = load_feishu_app_credentials(PROJECT_ROOT)
WIKI_URL = 'https://fintopia.feishu.cn/wiki/IahEwSFsLi7ZAmkvvMQcOg8pnwh'
SCREENSHOTS_DIR = PROJECT_ROOT / "screenshots"
OUTPUT_FILE = PROJECT_ROOT / "template_analysis.json"

BT_NAMES = {
    1: 'page', 2: 'text', 3: 'heading1', 4: 'heading2', 5: 'heading3',
    6: 'heading4', 7: 'heading5', 8: 'heading6', 9: 'heading7',
    10: 'heading8', 11: 'heading9', 12: 'bullet', 13: 'ordered',
    22: 'divider', 24: 'grid', 25: 'grid_column', 27: 'image', 18: 'table'
}

# ==================== 模板分析类 ====================

class TemplateAnalyzer:
    def __init__(self, app_id, app_secret):
        self.app_id = app_id
        self.app_secret = app_secret
        self.token = None
        self.base_url = "https://open.feishu.cn/open-apis"

    def authenticate(self):
        """获取 tenant_access_token"""
        url = f"{self.base_url}/auth/v3/tenant_access_token/internal"
        resp = requests.post(url, json={"app_id": self.app_id, "app_secret": self.app_secret})
        if resp.status_code != 200:
            return False
        r = resp.json()
        if r.get("code") != 0:
            return False
        self.token = r["tenant_access_token"]
        return True

    def get_wiki_doc_id(self, wiki_token):
        """获取 wiki 页面对应的文档 ID"""
        url = f"{self.base_url}/wiki/v2/spaces/get_node"
        headers = {"Authorization": f"Bearer {self.token}"}
        resp = requests.get(url, headers=headers, params={"token": wiki_token})
        if resp.status_code != 200:
            return None
        r = resp.json()
        if r.get("code") != 0:
            return None
        return r["data"]["node"]["obj_token"]

    def get_all_blocks(self, doc_id):
        """获取文档所有块"""
        all_blocks = []
        page_token = None
        while True:
            url = f"{self.base_url}/docx/v1/documents/{doc_id}/blocks"
            headers = {"Authorization": f"Bearer {self.token}"}
            params = {"page_size": 200}
            if page_token:
                params["page_token"] = page_token
            resp = requests.get(url, headers=headers, params=params)
            if resp.status_code != 200:
                break
            r = resp.json()
            if r.get("code") != 0:
                break
            items = r.get("data", {}).get("items", [])
            all_blocks.extend(items)
            if not r.get("data", {}).get("has_more"):
                break
            page_token = r["data"].get("page_token")
        return all_blocks

    @staticmethod
    def get_text(block):
        """从块中提取文本"""
        bt = block.get("block_type")
        if bt not in (2, 3, 4, 5, 12, 13):
            return ""
        name = BT_NAMES.get(bt, "text")
        bd = block.get(name, {})
        parts = []
        for elem in bd.get("elements", []):
            if "text_run" in elem:
                parts.append(elem["text_run"].get("content", ""))
        return "".join(parts)

    def analyze(self, wiki_url):
        """主分析流程"""
        print("=" * 70)
        print("步骤5.5: 飞书模板提前分析")
        print("=" * 70)

        # 认证
        print("\n[认证] 获取访问令牌...", end="", flush=True)
        if not self.authenticate():
            print(" [ERR]")
            return None
        print(" [OK]")

        # 获取文档ID
        wiki_token = wiki_url.split("/wiki/")[-1].split("?")[0]
        print(f"[读取] Wiki token: {wiki_token}...", end="", flush=True)
        doc_id = self.get_wiki_doc_id(wiki_token)
        if not doc_id:
            print(" [ERR]")
            return None
        print(f" [OK] 文档ID: {doc_id}")

        # 获取所有块
        print("[读取] 下载模板块...", end="", flush=True)
        blocks = self.get_all_blocks(doc_id)
        if not blocks:
            print(" [ERR]")
            return None
        print(f" [OK] {len(blocks)} 个块")

        blocks_map = {b["block_id"]: b for b in blocks}
        page = next((b for b in blocks if b.get("block_type") == 1), None)
        if not page:
            print("[ERR] 找不到根页面")
            return None

        root_ids = page.get("children", [])
        analysis = {
            "doc_id": doc_id,
            "total_blocks": len(blocks),
            "root_children_count": len(root_ids),
            "analyzed_at": __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "sections": {}
        }

        # ========== 1. 文档结构 ==========
        print("\n" + "-" * 70)
        print("【1. 文档结构】")
        print("-" * 70)
        root_children = []
        for i, cid in enumerate(root_ids):
            b = blocks_map.get(cid)
            if not b:
                continue
            bt = b.get("block_type")
            bname = BT_NAMES.get(bt, f"type_{bt}")
            text = self.get_text(b)[:80]
            children = b.get("children", [])
            child_count = len(children) if children and bt not in (25,) else 0
            root_children.append({
                "index": i + 1,
                "block_type": bt,
                "type_name": bname,
                "text": text,
                "children_count": child_count
            })
            print(f"  [{i+1:2d}] {bt:3d} {bname:15s} | {text}  {f'({child_count}子块)' if child_count else ''}")
        analysis["sections"]["structure"] = root_children

        # ========== 2. 文字排版格式 ==========
        print("\n" + "-" * 70)
        print("【2. 文字排版格式】")
        print("-" * 70)
        styles_found = {}
        for b in blocks:
            bt = b.get("block_type")
            if bt not in (2, 3, 4, 5, 12, 13):
                continue
            bname = BT_NAMES.get(bt, "text")
            bd = b.get(bname, {})
            for elem in bd.get("elements", []):
                if "text_run" in elem:
                    style = elem["text_run"].get("text_element_style", {})
                    if style:
                        style_str = json.dumps(style, ensure_ascii=False)
                        if style_str not in styles_found:
                            styles_found[style_str] = {
                                "block_type": bt,
                                "type_name": bname,
                                "style": style,
                                "example": elem["text_run"].get("content", "")[:40]
                            }
        for s in styles_found.values():
            print(f"  bt={s['block_type']} {s['type_name']:12s} | bold={s['style'].get('bold')} | 示例: \"{s['example']}\"")
        analysis["sections"]["styles"] = list(styles_found.values())

        # ========== 3. 插入参数 ==========
        print("\n" + "-" * 70)
        print("【3. 插入参数（占位符）】")
        print("-" * 70)
        text_params = {}
        img_params = {}
        for b in blocks:
            text = self.get_text(b)
            for m in re.finditer(r'\{(\w+)\}', text):
                # 记录参数出现的上下文
                if m.group(1) not in text_params:
                    text_params[m.group(1)] = 0
                text_params[m.group(1)] += 1
            for m in re.finditer(r'\[([^\]]+\.png)\]', text):
                fname = m.group(1)
                parent_id = ""
                for pb in blocks:
                    if b["block_id"] in pb.get("children", []):
                        parent_id = BT_NAMES.get(pb.get("block_type"), "")
                        break
                img_params[fname] = {
                    "block_id": b.get("block_id", "")[:12] + "...",
                    "parent_type": parent_id
                }

        print(f"  文本参数 ({len(text_params)}):")
        for p in sorted(text_params.keys()):
            print(f"    {{{p}}} (出现 {text_params[p]} 次)")
        print(f"  图片参数 ({len(img_params)}):")
        for p in sorted(img_params.keys()):
            info = img_params[p]
            print(f"    [{p}]  {info['parent_type']} / block_id={info['block_id']}")
        analysis["sections"]["text_params"] = {k: {"count": v} for k, v in sorted(text_params.items())}
        analysis["sections"]["img_params"] = {k: v for k, v in sorted(img_params.items())}

        # ========== 4. 检查图表完整性 ==========
        print("\n" + "-" * 70)
        print("【4. 图表文件完整性检查】")
        print("-" * 70)
        present = []
        missing = []
        for fname in sorted(img_params.keys()):
            fp = SCREENSHOTS_DIR / fname
            if fp.exists():
                sz = fp.stat().st_size
                present.append(fname)
                print(f"  [OK] {fname:45s} ({sz/1024:.1f} KB)")
            else:
                missing.append(fname)
                print(f"  [ERR] {fname:45s} 文件不存在!")
        print(f"\n  总图片: {len(img_params)} | 就绪: {len(present)} | 缺失: {len(missing)}")
        analysis["sections"]["image_check"] = {
            "total": len(img_params),
            "present": len(present),
            "missing": len(missing),
            "missing_files": missing
        }

        # 保存分析结果
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)
        print(f"\n[保存] 分析结果已保存到 {OUTPUT_FILE}")

        # 总结
        print("\n" + "=" * 70)
        print("【分析总结】")
        print("=" * 70)
        print(f"  模板总块数: {len(blocks)}")
        print(f"  根children数: {len(root_ids)}")
        print(f"  文本参数: {len(text_params)} 个")
        print(f"  图片占位符: {len(img_params)} 个")
        print(f"  图表就绪: {len(present)}/{len(img_params)}")
        if missing:
            print(f"  ⚠ 缺失 {len(missing)} 个图表文件，需先生成!")
        print()

        return analysis


def main():
    if not APP_ID or not APP_SECRET:
        print(FEISHU_CREDENTIALS_HELP)
        sys.exit(1)
    analyzer = TemplateAnalyzer(APP_ID, APP_SECRET)
    analyzer.analyze(WIKI_URL)


if __name__ == "__main__":
    main()
