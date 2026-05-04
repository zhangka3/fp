#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""飞书周报文档生成器 - 保留完整格式（含grid分栏）"""

import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import copy
import requests
import re
import os
import json
from pathlib import Path
from datetime import datetime, timedelta

_PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _m0_monthly_cutoff_context(fetch_date: datetime) -> dict:
    """与 screen_m0.build_monthly_cutoff_context 一致。环境变量 M0_SP_NO_FALLBACK=1 强制始终 (fetch-1).day。"""
    forced = os.environ.get('M0_SP_NO_FALLBACK', '').strip().lower() in ('1', 'true', 'yes', 'on')
    fd = fetch_date.date()
    fetch_month_key = fd.strftime('%Y-%m')
    first_of_month = fd.replace(day=1)
    prev_month_last = first_of_month - timedelta(days=1)
    mature_limit_7d = (fetch_date - timedelta(days=8)).date()
    if forced:
        return {
            'line_fallback': False,
            'cutoff_day': (fetch_date - timedelta(days=1)).day,
            'fetch_month_key': fetch_month_key,
            'notice': None,
            'forced_normal': True,
        }
    line_fallback = not (first_of_month <= mature_limit_7d)
    if line_fallback:
        anchor = min(prev_month_last, mature_limit_7d)
        cutoff_day = anchor.day
        notice = '因为本月没有7d成熟日，所以按照上月最后一个可以观察的截止日来做图'
    else:
        cutoff_day = (fetch_date - timedelta(days=1)).day
        notice = None
    return {
        'line_fallback': line_fallback,
        'cutoff_day': cutoff_day,
        'fetch_month_key': fetch_month_key,
        'notice': notice,
        'forced_normal': False,
    }
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
from feishu_creds import FEISHU_CREDENTIALS_HELP, load_feishu_app_credentials


class FeishuReportGenerator:
    def __init__(self, app_id, app_secret, data_dir=None):
        self.app_id = app_id
        self.app_secret = app_secret
        self.tenant_access_token = None
        self.base_url = "https://open.feishu.cn/open-apis"
        self.data_dir = Path(data_dir) if data_dir else _PROJECT_ROOT / "data"
        self.params = {}
        self.blocks_by_id = {}

    # ==================== API ====================

    def get_tenant_access_token(self):
        url = f"{self.base_url}/auth/v3/tenant_access_token/internal"
        data = {"app_id": self.app_id, "app_secret": self.app_secret}
        resp = requests.post(url, json=data)
        if resp.status_code == 200:
            r = resp.json()
            if r.get("code") == 0:
                self.tenant_access_token = r["tenant_access_token"]
                return True
        return False

    def get_wiki_document_id(self, wiki_token):
        info = self.get_wiki_node_info(wiki_token)
        return info["obj_token"] if info else None

    def get_wiki_node_info(self, wiki_token):
        """解析知识库节点：返回 obj_token、space_id、node_token（用于 wiki 内复制节点）。"""
        url = f"{self.base_url}/wiki/v2/spaces/get_node"
        headers = {"Authorization": f"Bearer {self.tenant_access_token}"}
        resp = requests.get(url, headers=headers, params={"token": wiki_token})
        if resp.status_code != 200:
            return None
        r = resp.json()
        if r.get("code") != 0:
            return None
        data = r.get("data") or {}
        node = data.get("node") or {}
        obj_token = node.get("obj_token")
        if not obj_token:
            return None
        space_id = (
            node.get("space_id")
            or data.get("space_id")
            or (node.get("space") or {}).get("space_id")
            or (node.get("space") or {}).get("id")
        )
        node_token = node.get("node_token") or wiki_token
        parent_node_token = node.get("parent_node_token")
        return {
            "obj_token": obj_token,
            "space_id": space_id,
            "node_token": node_token,
            "parent_node_token": parent_node_token,
        }

    def get_document_blocks(self, document_id):
        all_blocks = []
        page_token = None
        while True:
            url = f"{self.base_url}/docx/v1/documents/{document_id}/blocks"
            headers = {"Authorization": f"Bearer {self.tenant_access_token}"}
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

    def create_document(self, title, folder_token=None):
        url = f"{self.base_url}/docx/v1/documents"
        headers = {"Authorization": f"Bearer {self.tenant_access_token}", "Content-Type": "application/json"}
        data = {"title": title}
        if folder_token:
            data["folder_token"] = folder_token
        resp = requests.post(url, headers=headers, json=data)
        if resp.status_code == 200:
            r = resp.json()
            if r.get("code") == 0:
                return r["data"]["document"]
        return None

    def add_children_to_block(self, doc_id, block_id, children, debug_label="", max_retries=4, index=None):
        """给指定块添加children；HTTP 429 限流时指数退避重试。index 为插入位置（0 为首位，-1 为末尾）。"""
        import time
        url = f"{self.base_url}/docx/v1/documents/{doc_id}/blocks/{block_id}/children"
        headers = {"Authorization": f"Bearer {self.tenant_access_token}", "Content-Type": "application/json"}
        payload = {"children": children}
        if index is not None:
            payload["index"] = index
        for attempt in range(max_retries + 1):
            resp = requests.post(url, headers=headers, json=payload)
            if resp.status_code == 429:
                # 指数退避：0.5s, 1s, 2s, 4s
                wait = 0.5 * (2 ** attempt)
                if attempt < max_retries:
                    time.sleep(wait)
                    continue
                print(f"\n   [API ERR] add_children {debug_label} -> HTTP 429 (after {max_retries} retries)")
                return None
            if resp.status_code != 200:
                print(f"\n   [API ERR] add_children {debug_label} -> HTTP {resp.status_code}: {resp.text[:200]}")
                return None
            r = resp.json()
            if r.get("code") != 0:
                # 飞书部分错误码也用 code 表达限流（如 99991663 等），重试一次
                if attempt < max_retries and r.get("code") in (99991663, 99991664, 1254607):
                    time.sleep(0.5 * (2 ** attempt))
                    continue
                print(f"\n   [API ERR] add_children {debug_label} -> code={r.get('code')} msg={r.get('msg')}")
                return None
            # 调用成功后稍作休眠，给后续请求让出 QPS 配额
            time.sleep(0.15)
            return r.get("data", {})
        return None

    def _get_drive_parent_folder_token(self, file_token):
        """云文档 file_token 所在文件夹 token，用于复制模板到同目录。"""
        url = f"{self.base_url}/drive/v1/files/{file_token}"
        headers = {"Authorization": f"Bearer {self.tenant_access_token}"}
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            return None
        r = resp.json()
        if r.get("code") != 0:
            return None
        data = r.get("data") or {}
        meta = data.get("file") or data
        return meta.get("parent_token")

    def _copy_docx_file(self, src_token, dst_folder_token, dst_name):
        """复制云文档，返回新 document_id（file_token）。失败返回 None。"""
        headers = {"Authorization": f"Bearer {self.tenant_access_token}", "Content-Type": "application/json"}
        tried = []
        # 常见两种入口：explorer v2 与 drive v1
        v2_url = f"{self.base_url}/drive/explorer/v2/file/copy/files/{src_token}"
        r2 = requests.post(v2_url, headers=headers, json={
            "type": "docx", "dst_folder_token": dst_folder_token, "dst_name": dst_name,
        })
        tried.append(("explorer_v2", r2.status_code, r2.text[:120] if r2.text else ""))
        if r2.status_code == 200 and r2.json().get("code") == 0:
            data = r2.json().get("data") or {}
            nid = data.get("file_token") or data.get("token") or (data.get("file") or {}).get("token")
            if nid:
                return nid
        v1_url = f"{self.base_url}/drive/v1/files/copy"
        r1 = requests.post(v1_url, headers=headers, json={
            "file_token": src_token, "type": "docx",
            "dst_folder_token": dst_folder_token, "name": dst_name,
        })
        tried.append(("drive_v1", r1.status_code, r1.text[:120] if r1.text else ""))
        if r1.status_code == 200 and r1.json().get("code") == 0:
            data = r1.json().get("data") or {}
            fil = data.get("file") or data
            nid = fil.get("token") or data.get("file_token")
            if nid:
                return nid
        print(f"   [copy] 复制接口均失败: {tried}")
        return None

    def _copy_wiki_docx_node(self, space_id, node_token, dst_title, parent_node_token=None):
        """在知识库内复制 docx 节点（保留文档级标题编号等样式），返回新文档 obj_token。"""
        import time
        if not space_id or not node_token:
            return None
        sid_str = str(space_id).strip()
        url = f"{self.base_url}/wiki/v2/spaces/{sid_str}/nodes/{node_token}/copy"
        headers = {"Authorization": f"Bearer {self.tenant_access_token}", "Content-Type": "application/json"}
        # 官方说明：目标知识空间 ID 与目标父节点不可同时为空；复制到同目录需带上 target_space_id（及父节点）
        body = {"title": dst_title, "target_space_id": sid_str}
        if parent_node_token:
            body["target_parent_token"] = parent_node_token
        for attempt in range(5):
            resp = requests.post(url, headers=headers, json=body)
            if resp.status_code == 429:
                time.sleep(0.5 * (2 ** attempt))
                continue
            if resp.status_code != 200:
                print(f"   [copy] wiki copy HTTP {resp.status_code}: {resp.text[:200]}")
                return None
            r = resp.json()
            if r.get("code") != 0:
                print(f"   [copy] wiki copy code={r.get('code')} msg={r.get('msg')}")
                if r.get("code") == 131006:
                    print("       -> 请在目标知识库中将应用加入为可编辑成员，并开通权限 wiki:node:copy / wiki:wiki")
                    print("       -> 说明：https://open.feishu.cn/document/ukTMukTMukTM/uUDN04SN0QjL1QDN/wiki-v2/wiki-qa")
                return None
            node = (r.get("data") or {}).get("node") or {}
            nid = node.get("obj_token")
            if nid:
                return nid
            print(f"   [copy] wiki copy 响应无 obj_token: {str(r)[:200]}")
            return None
        return None

    def _batch_delete_children(self, doc_id, parent_block_id, start_index, end_index, debug_label="", max_retries=4):
        """删除父块子列表 [start_index, end_index)。"""
        import time
        url = f"{self.base_url}/docx/v1/documents/{doc_id}/blocks/{parent_block_id}/children/batch_delete"
        headers = {"Authorization": f"Bearer {self.tenant_access_token}", "Content-Type": "application/json"}
        body = {"start_index": start_index, "end_index": end_index}
        for attempt in range(max_retries + 1):
            resp = requests.delete(url, headers=headers, json=body)
            if resp.status_code == 429:
                time.sleep(0.5 * (2 ** attempt))
                continue
            if resp.status_code != 200:
                print(f"\n   [API ERR] batch_delete {debug_label} -> HTTP {resp.status_code}: {resp.text[:200]}")
                return None
            r = resp.json()
            if r.get("code") != 0:
                if attempt < max_retries and r.get("code") in (99991663, 99991664, 1254607):
                    time.sleep(0.5 * (2 ** attempt))
                    continue
                print(f"\n   [API ERR] batch_delete {debug_label} -> code={r.get('code')} msg={r.get('msg')}")
                return None
            time.sleep(0.15)
            return r.get("data", {})
        return None

    def _patch_update_text_elements(self, doc_id, block_id, elements, max_retries=4):
        """PATCH 更新块内文本 elements（须整块替换）。"""
        import time
        url = f"{self.base_url}/docx/v1/documents/{doc_id}/blocks/{block_id}"
        headers = {"Authorization": f"Bearer {self.tenant_access_token}", "Content-Type": "application/json"}
        body = {"update_text_elements": {"elements": elements}}
        for attempt in range(max_retries + 1):
            resp = requests.patch(url, headers=headers, json=body)
            if resp.status_code == 429:
                time.sleep(0.5 * (2 ** attempt))
                continue
            if resp.status_code != 200:
                return False
            r = resp.json()
            if r.get("code") != 0:
                if attempt < max_retries and r.get("code") in (99991663, 99991664, 1254607):
                    time.sleep(0.5 * (2 ** attempt))
                    continue
                return False
            time.sleep(0.15)
            return True
        return False

    _PATCH_TEXT_BLOCK_TYPES = frozenset({
        2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 17,
    })

    _PARAM_BRACE_RE = re.compile(r'\{(\w+)\}')

    def _replace_bracket_shortcuts(self, text: str) -> str:
        if not text:
            return text
        return (
            text.replace("[DD1]", str(self.params.get("DD1", "")))
            .replace("[DD]", str(self.params.get("DD", "")))
            .replace("[mm]", str(self.params.get("mm", "")))
        )

    @staticmethod
    def _parse_scalar_for_dif_rule(raw):
        """将参数值解析为 float；无法解析则 None（走非数值直接替换）。"""
        if raw is None:
            return None
        t = str(raw).strip().replace(",", "")
        if not t:
            return None
        if t.endswith("%"):
            t = t[:-1].strip()
        t = t.replace("−", "-").replace("—", "-")
        try:
            return float(t)
        except ValueError:
            return None

    def _dif_rise_style(self, base: dict) -> dict:
        st = copy.deepcopy(base) if base else {}
        st["bold"] = True
        st["text_color"] = 4  # 飞书枚举：绿色
        return st

    def _dif_fall_style(self, base: dict) -> dict:
        st = copy.deepcopy(base) if base else {}
        st["bold"] = True
        st["text_color"] = 1  # 飞书枚举：红色
        return st

    def _merge_adjacent_same_style_runs(self, runs: list) -> list:
        if not runs:
            return []
        merged = [{"content": runs[0]["content"], "text_element_style": runs[0]["text_element_style"]}]
        for r in runs[1:]:
            if r["text_element_style"] == merged[-1]["text_element_style"]:
                merged[-1]["content"] += r["content"]
            else:
                merged.append({"content": r["content"], "text_element_style": r["text_element_style"]})
        return merged

    def _param_replace_text_runs(self, content, base_style=None):
        """将一段 text_run 的 content 展开为若干 {content, text_element_style}（处理 *dif 上升/下降着色）。"""
        base_style = base_style or {}
        content = self._replace_bracket_shortcuts(content)
        out = []
        i = 0
        n = len(content)
        while i < n:
            m = self._PARAM_BRACE_RE.search(content, i)
            if not m:
                tail = content[i:]
                if tail:
                    out.append({"content": tail, "text_element_style": copy.deepcopy(base_style)})
                break
            if m.start() > i:
                out.append({"content": content[i:m.start()], "text_element_style": copy.deepcopy(base_style)})
            key = m.group(1)
            val = self.params.get(key)
            val_str = "" if val is None else str(val)
            ph_end = m.end()
            has_pp = ph_end + 2 <= n and content[ph_end : ph_end + 2] == "pp"

            if key.endswith("dif"):
                num = self._parse_scalar_for_dif_rule(val)
                if num is not None:
                    prefix = "上升" if num >= 0 else "下降"
                    extra = "pp" if has_pp else ""
                    styled = prefix + val_str + extra
                    # 金额/单量逾期率差分：>=0 红、<0 绿（「坏」上升）；其余 *dif 仍 >=0 绿、<0 红
                    invert_od = key in ("rate_prin_od_dif", "rate_cnt_od_dif")
                    if invert_od:
                        st = self._dif_fall_style(base_style) if num >= 0 else self._dif_rise_style(base_style)
                    else:
                        st = self._dif_rise_style(base_style) if num >= 0 else self._dif_fall_style(base_style)
                    out.append({"content": styled, "text_element_style": st})
                    i = ph_end + (2 if has_pp else 0)
                    continue
                out.append({"content": val_str, "text_element_style": copy.deepcopy(base_style)})
                i = ph_end
                continue

            out.append({"content": val_str, "text_element_style": copy.deepcopy(base_style)})
            i = ph_end

        if not out:
            return [{"content": content, "text_element_style": copy.deepcopy(base_style)}]
        return self._merge_adjacent_same_style_runs(out)

    def _elements_after_param_replace(self, elements):
        """深拷贝 elements，替换 text_run 中的占位符；无变化返回 None。"""
        if not isinstance(elements, list) or not elements:
            return None
        out = []
        changed = False
        for el in copy.deepcopy(elements):
            tr = el.get("text_run")
            if not tr:
                out.append(el)
                continue
            old = tr.get("content", "")
            base = tr.get("text_element_style") or {}
            runs = self._param_replace_text_runs(old, base)
            if (
                len(runs) == 1
                and runs[0]["content"] == old
                and runs[0]["text_element_style"] == base
            ):
                out.append(el)
                continue
            changed = True
            for r in runs:
                out.append(
                    {
                        "text_run": {
                            "content": r["content"],
                            "text_element_style": r["text_element_style"],
                        }
                    }
                )
        return out if changed else None

    def _root_skip_delete_half_open_ranges(self, root_children_ids, blocks_by_id):
        """与 write_plan 一致的跳过区间：删「插入参数」说明直到「一、核心…」之前（不含结束标记块）。"""
        skip_mode = False
        indices = []
        for i, cid in enumerate(root_children_ids):
            block = blocks_by_id.get(cid)
            if not block:
                continue
            ns = self._needs_skip(block)
            if ns == "end_skip":
                skip_mode = False
                continue
            if ns == "start_skip":
                skip_mode = True
                indices.append(i)
                continue
            if skip_mode:
                indices.append(i)
        if not indices:
            return []
        indices = sorted(set(indices))
        ranges = []
        s = e = indices[0]
        for x in indices[1:]:
            if x == e + 1:
                e = x
            else:
                ranges.append((s, e + 1))
                s = e = x
        ranges.append((s, e + 1))
        return ranges

    def _png_jobs_grouped_by_parent(self, blocks, screenshots_dir):
        """[(parent_id, jobs), ...]；jobs 为 (idx, kind, data) 列表，idx 降序。

        kind 为 \"single\" 时 data 为 str（文件名）；为 \"multi\" 时 data 为 str 列表
        （同一文本块内连续多个 [a.png][b.png]，一次删块并插入多张图）。
        """
        from collections import defaultdict
        by_id = {b["block_id"]: b for b in blocks}
        parent_of = {}
        for b in blocks:
            for cid in b.get("children") or []:
                parent_of[cid] = b["block_id"]
        raw = []
        for b in blocks:
            fnames = self._ordered_png_placeholder_fnames(b)
            if not fnames:
                continue
            if not all((Path(screenshots_dir) / f).exists() for f in fnames):
                continue
            bid = b["block_id"]
            pid = parent_of.get(bid)
            if not pid or pid not in by_id:
                continue
            ch = by_id[pid].get("children") or []
            if bid not in ch:
                continue
            idx = ch.index(bid)
            if len(fnames) == 1:
                raw.append((pid, idx, "single", fnames[0]))
            else:
                raw.append((pid, idx, "multi", list(fnames)))
        by_parent = defaultdict(list)
        for pid, idx, kind, data in raw:
            by_parent[pid].append((idx, kind, data))
        out = []
        for pid, lst in by_parent.items():
            lst.sort(key=lambda t: -t[0])
            out.append((pid, lst))
        return out

    def _created_child_block_id(self, add_data):
        if not add_data:
            return None
        for c in add_data.get("children") or []:
            if isinstance(c, dict) and c.get("block_id"):
                return c["block_id"]
            if isinstance(c, str):
                return c
        return None

    def _created_child_block_ids(self, add_data):
        """add_children 一次写入多个子块时，按返回顺序列出 block_id。"""
        if not add_data:
            return []
        out = []
        for c in add_data.get("children") or []:
            if isinstance(c, dict) and c.get("block_id"):
                out.append(c["block_id"])
            elif isinstance(c, str):
                out.append(c)
        return out

    def _report_via_copy_template(self, template_doc_id, template_blocks, output_title, screenshots_dir, img_placeholder_order, wiki_token=None):
        """复制整篇模板再原地替换占位符与图片，保留飞书原生标题编号等多级列表样式。"""
        import time
        new_id = None
        if wiki_token:
            winfo = self.get_wiki_node_info(wiki_token)
            if winfo and winfo.get("space_id"):
                new_id = self._copy_wiki_docx_node(
                    winfo["space_id"],
                    winfo["node_token"],
                    output_title,
                    parent_node_token=winfo.get("parent_node_token"),
                )
                if new_id:
                    print(f"   [copy] 已通过知识库复制模板（保留原生编号），document_id={new_id[:18]}…")
        if not new_id:
            folder = (os.environ.get("FEISHU_DST_FOLDER_TOKEN") or "").strip()
            if not folder:
                folder = self._get_drive_parent_folder_token(template_doc_id)
            if not folder:
                print("   [copy] 无法使用知识库复制且未取得云文档文件夹 token（可设置 FEISHU_DST_FOLDER_TOKEN），跳过复制模式")
                return None
            new_id = self._copy_docx_file(template_doc_id, folder, output_title)
            if not new_id:
                return None
            print(f"   [copy] 已通过云盘复制模板（保留原生编号），document_id={new_id[:18]}…")

        blocks = self.get_document_blocks(new_id)
        if not blocks:
            print("   [copy] 读取新文档块失败")
            return None
        by_id = {b["block_id"]: b for b in blocks}
        page = next((b for b in blocks if b.get("block_type") == 1), None)
        if not page:
            print("   [copy] 新文档无根页面")
            return None
        root_ids = page.get("children") or []
        for start, end in sorted(self._root_skip_delete_half_open_ranges(root_ids, by_id), key=lambda r: r[0], reverse=True):
            self._batch_delete_children(new_id, page["block_id"], start, end, debug_label=f"skip [{start},{end})")
            time.sleep(0.2)
        blocks = self.get_document_blocks(new_id)
        by_id = {b["block_id"]: b for b in blocks}
        page = next((b for b in blocks if b.get("block_type") == 1), None)
        if page:
            self.blocks_by_id = by_id

        img_placeholder_map = {n: None for n in img_placeholder_order}
        for pid, lst in self._png_jobs_grouped_by_parent(blocks, screenshots_dir):
            for idx, kind, data in lst:
                if kind == "single":
                    fname = data
                    label = fname
                    fnames = [fname]
                else:
                    fnames = data
                    label = "+".join(fnames)
                if self._batch_delete_children(new_id, pid, idx, idx + 1, debug_label=f"png del {label}") is None:
                    continue
                children = [{"block_type": 27, "image": {}} for _ in fnames]
                ad = self.add_children_to_block(
                    new_id, pid, children,
                    debug_label=f"png add {label}", index=idx,
                )
                nb_list = self._created_child_block_ids(ad)
                for fname, nb in zip(fnames, nb_list):
                    if nb:
                        img_placeholder_map[fname] = nb
                time.sleep(0.2)

        blocks = self.get_document_blocks(new_id)
        by_id = {b["block_id"]: b for b in blocks}

        def dfs_patch(bid):
            b = by_id.get(bid)
            if not b:
                return
            bt = b.get("block_type")
            if bt in self._PATCH_TEXT_BLOCK_TYPES:
                bd = self._get_block_data(b)
                if isinstance(bd, dict):
                    upd = self._elements_after_param_replace(bd.get("elements"))
                    if upd is not None:
                        self._patch_update_text_elements(new_id, bid, upd)
                        time.sleep(0.15)
            for cid in b.get("children") or []:
                dfs_patch(cid)

        page = next((b for b in blocks if b.get("block_type") == 1), None)
        if page:
            for cid in page.get("children") or []:
                dfs_patch(cid)

        nd_url = f"https://www.feishu.cn/docx/{new_id}"
        print("\n[上传图片]...")
        screenshots_path = Path(screenshots_dir)
        unmapped = [n for n in img_placeholder_order if not img_placeholder_map.get(n)]
        if unmapped:
            all_doc_blocks = self.get_document_blocks(new_id)
            imgs = [b for b in all_doc_blocks if b.get("block_type") == 27]
            used = set(v for v in img_placeholder_map.values() if v)
            avail = [b for b in imgs if b["block_id"] not in used]
            for i, name in enumerate(unmapped):
                if i < len(avail):
                    img_placeholder_map[name] = avail[i]["block_id"]
                    print(f"   [后备] {name} -> block_id={avail[i]['block_id'][:12]}...")
        up_ok = 0
        for img_name in img_placeholder_order:
            block_id = img_placeholder_map.get(img_name)
            if not block_id:
                print(f"   [WARN] 找不到图片块: {img_name}")
                continue
            img_path = screenshots_path / img_name
            if not img_path.exists():
                print(f"   [WARN] 文件不存在: {img_name}")
                continue
            if self._upload_image_to_block(new_id, block_id, str(img_path)):
                up_ok += 1
                print(f"   [OK] {img_name}")
            else:
                print(f"   [ERR] {img_name}")
        print(f"\n[OK] 完成: 图片 {up_ok}/{len(img_placeholder_order)}")
        return {"document_id": new_id, "url": nd_url, "title": output_title}

    # ==================== 参数计算 ====================

    def calculate_date_params(self):
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        self.params['mm'] = str(today.month)
        self.params['DD'] = str(today.day)
        self.params['DD1'] = str(yesterday.day)
        # {mm1} = 当前月-1（如 4 月 → 3）；{mm2} = 当前月-2（如 4 月 → 2）
        last_m_first = today.replace(day=1) - timedelta(days=1)
        last_last_m_first = last_m_first.replace(day=1) - timedelta(days=1)
        self.params['mm1'] = str(last_m_first.month)
        self.params['mm2'] = str(last_last_m_first.month)

    def calculate_data_params(self):
        try:
            m0_file = self.data_dir / "m0_billing.json"
            if not m0_file.exists():
                self._set_default_data_params(); return
            with open(m0_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            rows = data.get('rows', [])
            if not rows: self._set_default_data_params(); return
            latest_date = max(row[0] for row in rows if isinstance(row, list) and row[0])
            lm, ld = latest_date[:7], int(latest_date[8:])
            pm = (datetime.strptime(lm + "-01", "%Y-%m-%d").replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
            lc, lcp, lp, lpp = 0, 0, 0, 0
            pc, pcp, pp, ppp = 0, 0, 0, 0
            for row in rows:
                if not isinstance(row, list) or len(row) < 5: continue
                d = row[0]
                if d.startswith(lm):
                    lc += float(row[1]) or 0; lcp += float(row[2]) or 0; lp += float(row[3]) or 0; lpp += float(row[4]) or 0
                elif d.startswith(pm) and int(d[8:]) <= ld:
                    pc += float(row[1]) or 0; pcp += float(row[2]) or 0; pp += float(row[3]) or 0; ppp += float(row[4]) or 0
            cur_prin = (lpp/lp) if lp else 0
            prev_prin = (ppp/pp) if pp else 0
            cur_cnt = (lcp/lc) if lc else 0
            prev_cnt = (pcp/pc) if pc else 0
            self.params.update({
                'rate_prin_od': f"{cur_prin*100:.2f}%",
                'rate_cnt_od': f"{cur_cnt*100:.2f}%",
                'rate_prin_od_dif': f"{(cur_prin - prev_prin) * 100:.2f}",
                'rate_cnt_od_dif': f"{(cur_cnt - prev_cnt) * 100:.2f}"
            })
            print(f"   [rate_od] lm={lm}(1~{ld}) prin={cur_prin*100:.2f}%  pm={pm}(1~{ld}) prin={prev_prin*100:.2f}%  dif={(cur_prin - prev_prin)*100:+.2f}pp")
            print(f"   [rate_od] lm={lm}(1~{ld}) cnt ={cur_cnt*100:.2f}%  pm={pm}(1~{ld}) cnt ={prev_cnt*100:.2f}%  dif={(cur_cnt - prev_cnt)*100:+.2f}pp")
        except Exception:
            self._set_default_data_params()

        # 计算周维度催回率参数（从 m0_billing.json）
        self._calculate_weekly_collection_rates()

        # 计算月维度催回率参数（从 m0_billing.json，与 m0_collection_rate_7d_30d_monthly.png 对齐）
        self._calculate_monthly_collection_rates()

        # 合并订单/非合并 7d 月催回 + IND1 占比（从 m0_billing_grouped.json，与 screen_m0 分图对齐）
        self._calculate_monthly_ind_from_grouped()

    def _calculate_weekly_collection_rates(self):
        """计算 {wk_colrate7d}, {wk_colrate7d_dif}, {wk_colrate15d}, {wk_colrate15d_dif}

        与 [m0_collection_rate_weekly.png] 完全对齐：
          - 数据源：m0_billing.json（不是 grouped）
          - 周分组：周日为周起始（与 screen_m0.aggregate_weekly_data 一致）
          - 成熟度：week_end + N 天 <= data_fetch_date（与月度 billing<=fetch-N 边界一致）
          - 取最新成熟周与上一成熟周作差
        m0_billing.json header 索引: pd1=4, pd8=8, pd16=12
        """
        from collections import defaultdict
        try:
            m0_file = self.data_dir / "m0_billing.json"
            if not m0_file.exists():
                self._set_weekly_defaults(); return
            with open(m0_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            rows = data.get('rows', [])
            fetch_date_str = data.get('metadata', {}).get('data_fetch_date')
            if not rows or not fetch_date_str:
                self._set_weekly_defaults(); return
            data_fetch_date = datetime.strptime(fetch_date_str, '%Y-%m-%d')

            weekly_data = defaultdict(lambda: {'pd1': 0.0, 'pd8': 0.0, 'pd16': 0.0})
            for row in rows:
                if not isinstance(row, list) or len(row) < 13:
                    continue
                bdate = datetime.strptime(row[0], '%Y-%m-%d')
                # 周日为周起始：Sunday=0
                days_since_sunday = (bdate.weekday() + 1) % 7
                week_start = bdate - timedelta(days=days_since_sunday)
                wk_key = week_start.strftime('%Y-%m-%d')
                weekly_data[wk_key]['pd1'] += float(row[4]) or 0
                weekly_data[wk_key]['pd8'] += float(row[8]) or 0
                weekly_data[wk_key]['pd16'] += float(row[12]) or 0

            sorted_wks = sorted(weekly_data.keys())
            if not sorted_wks:
                self._set_weekly_defaults(); return

            def _last_two(buckets, key_pd_minus, mature_days):
                """与 screen_m0.generate_weekly_collection_rate 一致：
                week_end = week_start + 6，成熟条件 week_end + mature_days <= fetch_date。
                只保留 pd1>0 且成熟的周，取最新与上一作差。"""
                mature = []
                for wk in sorted_wks:
                    week_start = datetime.strptime(wk, '%Y-%m-%d')
                    week_end = week_start + timedelta(days=6)
                    bucket = buckets[wk]
                    if bucket['pd1'] > 0 and (week_end + timedelta(days=mature_days)) <= data_fetch_date:
                        mature.append((wk, bucket))
                if not mature:
                    return 0.0, 0.0, None, None
                cw_key, cw = mature[-1]
                cur = (cw['pd1'] - cw[key_pd_minus]) / cw['pd1'] * 100
                if len(mature) >= 2:
                    pw_key, pw = mature[-2]
                    prev = (pw['pd1'] - pw[key_pd_minus]) / pw['pd1'] * 100
                    return cur, cur - prev, cw_key, pw_key
                return cur, 0.0, cw_key, None

            col7d, dif7d, c7, p7 = _last_two(weekly_data, 'pd8', mature_days=8)
            col15d, dif15d, c15, p15 = _last_two(weekly_data, 'pd16', mature_days=16)

            self.params.update({
                'wk_colrate7d': f"{col7d:.2f}%",
                'wk_colrate7d_dif': f"{dif7d:.2f}",
                'wk_colrate15d': f"{col15d:.2f}%",
                'wk_colrate15d_dif': f"{dif15d:.2f}"
            })
            print(f"   [wk_col]  wk7d ={col7d:.2f}% (cur={c7} vs prev={p7})  dif={dif7d:+.2f}pp")
            print(f"   [wk_col]  wk15d={col15d:.2f}% (cur={c15} vs prev={p15})  dif={dif15d:+.2f}pp")
        except Exception as e:
            print(f"   [WARN] 周催回率计算失败: {e}")
            self._set_weekly_defaults()

    def _set_weekly_defaults(self):
        self.params.update({
            'wk_colrate7d': 'XX.XX%', 'wk_colrate7d_dif': 'X.XX',
            'wk_colrate15d': 'XX.XX%', 'wk_colrate15d_dif': 'X.XX'
        })

    def _calculate_monthly_collection_rates(self):
        """计算 {mth_colrate7d}, {mth_colrate7d_dif}, {mth_colrate30d}, {mth_colrate30d_dif}

        与 [m0_collection_rate_7d_30d_monthly.png] 图中最新月份的最后一个点对齐。
        口径（与 screen_m0 催回月图一致）：
          - 每月 day <= ctx.cutoff_day（与柱一致；月初无7d成熟且未设 M0_SP_NO_FALLBACK 时回退并跳过当月桶）
          - 7d：再要求账单日期 <= fetch_date - 8；30d：<= fetch_date - 31
        m0_billing.json header: [billing_date, billing_instalment_cnt,
            c_billing_instalment_cnt_pastdue_1d, billing_principal,
            c_billing_principal_pastdue_1d, ..., c_billing_principal_pastdue_8d (idx 8),
            ..., c_billing_principal_pastdue_31d (idx 13)]
        """
        from collections import defaultdict
        try:
            m0_file = self.data_dir / "m0_billing.json"
            if not m0_file.exists():
                self._set_monthly_defaults(); return
            with open(m0_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            rows = data.get('rows', [])
            fetch_str = data.get('metadata', {}).get('data_fetch_date')
            if not rows or not fetch_str:
                self._set_monthly_defaults(); return
            fetch_date = datetime.strptime(fetch_str, '%Y-%m-%d')
            ctx = _m0_monthly_cutoff_context(fetch_date)
            if ctx.get('forced_normal'):
                print("   [提示] 已启用 M0_SP_NO_FALLBACK：月催回率占位符按 (fetch−1).day。")
            if ctx['notice']:
                print(f"   [提示] {ctx['notice']}")

            cutoff_line = ctx['cutoff_day']
            max_billing_7d = (fetch_date - timedelta(days=8)).date()
            max_billing_30d = (fetch_date - timedelta(days=31)).date()

            mth_7d = defaultdict(lambda: {'pd1': 0.0, 'pd8': 0.0})
            mth_30d = defaultdict(lambda: {'pd1': 0.0, 'pd31': 0.0})
            for row in rows:
                if not isinstance(row, list) or len(row) < 14:
                    continue
                bdate = datetime.strptime(row[0], '%Y-%m-%d')
                mkey = row[0][:7]
                bd = bdate.date()
                if ctx['line_fallback'] and mkey == ctx['fetch_month_key']:
                    continue
                if bdate.day <= cutoff_line and bd <= max_billing_7d:
                    mth_7d[mkey]['pd1'] += float(row[4]) or 0
                    mth_7d[mkey]['pd8'] += float(row[8]) or 0
                if bdate.day <= cutoff_line and bd <= max_billing_30d:
                    mth_30d[mkey]['pd1'] += float(row[4]) or 0
                    mth_30d[mkey]['pd31'] += float(row[13]) or 0

            def _last_two(buckets, key_pd_minus):
                """与 screen_m0 一致的过滤：只保留 pd1>0 且 pd_minus>0 的月份（即数据成熟月）。
                取最新成熟月与上一成熟月作差。"""
                mature = [(m, buckets[m]) for m in sorted(buckets.keys())
                          if buckets[m]['pd1'] > 0 and buckets[m][key_pd_minus] > 0]
                if not mature:
                    return 0.0, 0.0, None, None
                cm, c = mature[-1]
                cur = (c['pd1'] - c[key_pd_minus]) / c['pd1'] * 100
                if len(mature) >= 2:
                    pm, p = mature[-2]
                    prev = (p['pd1'] - p[key_pd_minus]) / p['pd1'] * 100
                    return cur, cur - prev, cm, pm
                return cur, 0.0, cm, None

            col7d, dif7d, m7c, m7p = _last_two(mth_7d, 'pd8')
            col30d, dif30d, m30c, m30p = _last_two(mth_30d, 'pd31')

            self.params.update({
                'mth_colrate7d': f"{col7d:.2f}%",
                'mth_colrate7d_dif': f"{dif7d:.2f}",
                'mth_colrate30d': f"{col30d:.2f}%",
                'mth_colrate30d_dif': f"{dif30d:.2f}",
            })
            print(f"   mth7d={self.params['mth_colrate7d']} ({m7c} vs {m7p}), "
                  f"mth30d={self.params['mth_colrate30d']} ({m30c} vs {m30p})")
        except Exception as e:
            print(f"   [WARN] 月催回率计算失败: {e}")
            self._set_monthly_defaults()

    def _calculate_monthly_ind_from_grouped(self):
        """{mth_colrate7d_ind0/1}、占比与差分：与 m0_collection_rate_7d_30d_monthly_ind*.png / m0_ind1_ratio.png 口径一致。"""
        from collections import defaultdict

        gpath = self.data_dir / "m0_billing_grouped.json"
        if not gpath.exists():
            self._set_ind_split_defaults()
            return
        try:
            with open(gpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            rows = data.get("rows", [])
            fetch_str = data.get("metadata", {}).get("data_fetch_date")
            if not rows or not fetch_str:
                self._set_ind_split_defaults()
                return
            fetch_date = datetime.strptime(fetch_str, "%Y-%m-%d")
            ctx = _m0_monthly_cutoff_context(fetch_date)
            cutoff_line = ctx['cutoff_day']
            max_b1 = (fetch_date - timedelta(days=1)).date()
            max_billing_7d = (fetch_date - timedelta(days=8)).date()

            monthly_ind = defaultdict(lambda: {"ind0": 0.0, "ind1": 0.0})
            mth7 = {
                "0": defaultdict(lambda: {"pd1": 0.0, "pd8": 0.0}),
                "1": defaultdict(lambda: {"pd1": 0.0, "pd8": 0.0}),
            }
            for row in rows:
                if not isinstance(row, list) or len(row) < 9:
                    continue
                bdate = datetime.strptime(row[0], "%Y-%m-%d")
                mkey = row[0][:7]
                ind = str(row[1])
                if ind not in ("0", "1"):
                    continue
                bd = bdate.date()
                if bdate.day <= cutoff_line and bd <= max_b1:
                    p1 = float(row[5]) or 0.0
                    if ind == "0":
                        monthly_ind[mkey]["ind0"] += p1
                    else:
                        monthly_ind[mkey]["ind1"] += p1
                if ctx["line_fallback"] and mkey == ctx["fetch_month_key"]:
                    continue
                if bdate.day <= cutoff_line and bd <= max_billing_7d:
                    mth7[ind][mkey]["pd1"] += float(row[5]) or 0.0
                    mth7[ind][mkey]["pd8"] += float(row[8]) or 0.0

            def _last_two_7d(buckets):
                mature = [
                    (m, buckets[m])
                    for m in sorted(buckets.keys())
                    if buckets[m]["pd1"] > 0 and buckets[m]["pd8"] > 0
                ]
                if not mature:
                    return 0.0, 0.0
                cm, c = mature[-1]
                cur = (c["pd1"] - c["pd8"]) / c["pd1"] * 100
                if len(mature) >= 2:
                    pm, p = mature[-2]
                    prev = (p["pd1"] - p["pd8"]) / p["pd1"] * 100
                    return cur, cur - prev
                return cur, 0.0

            c0, d0 = _last_two_7d(mth7["0"])
            c1, d1 = _last_two_7d(mth7["1"])
            self.params.update(
                {
                    "mth_colrate7d_ind0": f"{c0:.2f}%",
                    "mth_colrate7d_ind0_dif": f"{d0:.2f}",
                    "mth_colrate7d_ind1": f"{c1:.2f}%",
                    "mth_colrate7d_ind1_dif": f"{d1:.2f}",
                }
            )

            months_sorted = sorted(monthly_ind.keys())
            ratios = []
            for m in months_sorted:
                d = monthly_ind[m]
                tot = d["ind0"] + d["ind1"]
                ratios.append((d["ind1"] / tot * 100) if tot > 0 else 0.0)
            if ratios:
                self.params["mth_ind1_ratio"] = f"{ratios[-1]:.2f}%"
                if len(ratios) >= 2:
                    self.params["mth1_ind1_ratio"] = f"{ratios[-2]:.2f}%"
                    self.params["mth_ind1_ratio_dif"] = f"{(ratios[-1] - ratios[-2]):.2f}"
                else:
                    self.params["mth1_ind1_ratio"] = f"{ratios[-1]:.2f}%"
                    self.params["mth_ind1_ratio_dif"] = "0.00"
            else:
                self.params.update(
                    {
                        "mth_ind1_ratio": "XX.XX%",
                        "mth1_ind1_ratio": "XX.XX%",
                        "mth_ind1_ratio_dif": "X.XX",
                    }
                )

            print(
                f"   [ind_mth] ind0 7d={self.params['mth_colrate7d_ind0']} "
                f"dif={self.params['mth_colrate7d_ind0_dif']}, "
                f"ind1 7d={self.params['mth_colrate7d_ind1']} "
                f"dif={self.params['mth_colrate7d_ind1_dif']}, "
                f"ind1占比={self.params.get('mth_ind1_ratio')}"
            )
        except Exception as e:
            print(f"   [WARN] grouped 月参数失败: {e}")
            self._set_ind_split_defaults()

    def _set_ind_split_defaults(self):
        self.params.update(
            {
                "mth_colrate7d_ind0": "XX.XX%",
                "mth_colrate7d_ind0_dif": "X.XX",
                "mth_colrate7d_ind1": "XX.XX%",
                "mth_colrate7d_ind1_dif": "X.XX",
                "mth_ind1_ratio": "XX.XX%",
                "mth1_ind1_ratio": "XX.XX%",
                "mth_ind1_ratio_dif": "X.XX",
            }
        )

    def _set_monthly_defaults(self):
        self.params.update({
            'mth_colrate7d': 'XX.XX%', 'mth_colrate7d_dif': 'X.XX',
            'mth_colrate30d': 'XX.XX%', 'mth_colrate30d_dif': 'X.XX',
            "mth_colrate7d_ind0": "XX.XX%",
            "mth_colrate7d_ind0_dif": "X.XX",
            "mth_colrate7d_ind1": "XX.XX%",
            "mth_colrate7d_ind1_dif": "X.XX",
            "mth_ind1_ratio": "XX.XX%",
            "mth1_ind1_ratio": "XX.XX%",
            "mth_ind1_ratio_dif": "X.XX",
        })

    def _set_default_data_params(self):
        self.params.update({'rate_prin_od': 'XX.XX%', 'rate_cnt_od': 'XX.XX%', 'rate_prin_od_dif': 'X.XX', 'rate_cnt_od_dif': 'X.XX'})

    def calculate_all_params(self):
        print("\n[参数] 开始计算...")
        self.calculate_date_params(); self.calculate_data_params()
        print(f"   mm={self.params.get('mm')}, mm1={self.params.get('mm1')}, mm2={self.params.get('mm2')}, "
              f"DD={self.params.get('DD')}, DD1={self.params.get('DD1')}")
        print(f"   prin={self.params.get('rate_prin_od')}, cnt={self.params.get('rate_cnt_od')}")
        print("[参数] 完成\n")

    def replace_params_in_text(self, text):
        """无样式场景的扁平字符串替换（不插入上升/下降；飞书正文样式请用 _param_replace_text_runs）。"""
        text = self._replace_bracket_shortcuts(text)
        for k, v in self.params.items():
            text = text.replace("{" + k + "}", str(v))
        return text

    # ==================== 块处理 ====================

    BT_MAP = {
        1: ("page", "page"), 2: ("text", "text"), 3: ("heading1", "heading1"),
        4: ("heading2", "heading2"), 5: ("heading3", "heading3"),
        6: ("heading4", "heading4"), 7: ("heading5", "heading5"),
        8: ("heading6", "heading6"), 9: ("heading7", "heading7"),
        10: ("heading8", "heading8"), 11: ("heading9", "heading9"),
        12: ("bullet", "bullet"), 13: ("ordered", "ordered"),
        22: ("divider", "divider"),
        24: ("grid", "grid"), 25: ("grid_column", "grid_column"),
        27: ("image", "image"),
    }

    def _get_block_data(self, block):
        info = self.BT_MAP.get(block.get("block_type"))
        return block.get(info[0], {}) if info else {}

    def _get_block_text(self, block):
        bd = self._get_block_data(block)
        return "".join(e["text_run"].get("content", "") for e in bd.get("elements", []) if "text_run" in e) if bd else ""

    def _clone_elements(self, block_data):
        elements = block_data.get("elements", []) if block_data else []
        result = []
        for elem in elements:
            if "text_run" in elem:
                tr = elem["text_run"]
                base = tr.get("text_element_style") or {}
                for r in self._param_replace_text_runs(tr.get("content", ""), base):
                    result.append(
                        {
                            "text_run": {
                                "content": r["content"],
                                "text_element_style": r["text_element_style"],
                            }
                        }
                    )
            else:
                result.append(elem)
        return result

    def _build_clone(self, block):
        bt = block.get("block_type")
        bd = self._get_block_data(block)
        info = self.BT_MAP.get(bt)
        if not info:
            return None
        _, dk = info

        child = {"block_type": bt}

        # 文本类块：深拷贝模板载荷再替换 elements，避免丢掉 ordered/bullet 的 style.sequence 等字段导致「序号丢失」
        if bt in (2, 12, 13):
            payload = copy.deepcopy(bd) if bd else {}
            payload["elements"] = self._clone_elements(bd or {})
            child[dk] = payload
            if bt == 13:
                st = child[dk].setdefault("style", {})
                if not isinstance(st, dict):
                    st = {}
                    child[dk]["style"] = st
                # 飞书有序列表依赖 style.sequence；API 偶发省略时需兜底，否则新建文档不显示编号
                if "sequence" not in st:
                    st["sequence"] = "auto"
        elif bt == 22:
            child[dk] = {}
        elif 3 <= bt <= 11:
            payload = copy.deepcopy(bd) if bd else {}
            payload["elements"] = self._clone_elements(bd or {})
            child[dk] = payload
        elif bt == 24:
            child[dk] = {"column_size": bd.get("column_size", 1)}
        elif bt == 25:
            child[dk] = {"width_ratio": bd.get("width_ratio", 50)}
        elif bt == 27:
            child[dk] = {}
        else:
            return None

        self._polish_block_for_publish(child, bt)
        return child

    def _join_text_runs(self, elements):
        if not elements:
            return ""
        parts = []
        for el in elements:
            tr = el.get("text_run")
            if tr:
                parts.append(tr.get("content", ""))
        return "".join(parts)

    def _polish_block_for_publish(self, child, bt):
        """写入飞书前微调版式：不修改仓库模板快照、不改 wiki 源模板，仅作用于本次克隆的块。"""
        info = self.BT_MAP.get(bt)
        if not info:
            return
        _, dk = info[0], info[1]
        bd = child.get(dk)
        if not isinstance(bd, dict):
            return
        elements = bd.get("elements")
        if isinstance(elements, list):
            for el in elements:
                tr = el.get("text_run")
                if not tr:
                    continue
                ts = tr.setdefault("text_element_style", {})
                if 3 <= bt <= 11:
                    ts["bold"] = True
        if bt == 3 and isinstance(elements, list):
            title_txt = self._join_text_runs(elements).strip()
            st = bd.setdefault("style", {})
            if title_txt.startswith(("一、", "二、")):
                st["align"] = 2
            else:
                st.setdefault("align", 1)

    def _ordered_png_placeholder_fnames(self, block):
        """块内整段仅由若干 [*.png] 组成（中间可空白）时，按从左到右顺序返回文件名列表；否则 []."""
        text = self._get_block_text(block).strip()
        matches = list(re.finditer(r'\[([^\]]+\.png)\]', text))
        if not matches:
            return []
        last_end = 0
        for m in matches:
            if text[last_end:m.start()].strip():
                return []
            last_end = m.end()
        if text[last_end:].strip():
            return []
        return [m.group(1) for m in matches]

    def _is_png_placeholder(self, block):
        """仅当块内恰好一个 [xxx.png] 且无其它字符时返回 Match（兼容旧逻辑）。"""
        text = self._get_block_text(block).strip()
        if len(self._ordered_png_placeholder_fnames(block)) != 1:
            return None
        return re.match(r'^\[([^\]]+\.png)\]$', text)

    def _needs_skip(self, block):
        text = self._get_block_text(block).strip()
        if re.match(r'^0[、.,\s]*插入参数', text):
            return "start_skip"
        if re.match(r'^一[、.,\s]*核心结果指标', text):
            return "end_skip"
        return False

    def _print_feishu_doc_guide_alignment(self, blocks_tpl):
        """对照已安装的 feishu-cli-doc-guide：说明与 Markdown 导入的差异，并做模板文本级快检（不修改飞书模板）。"""
        blob = "\n".join(filter(None, (self._get_block_text(b) for b in blocks_tpl)))
        low = blob.lower()
        print("   [doc-guide] feishu-cli-doc-guide：docx API 克隆（wiki 模板只读）")
        if "```mermaid" in low or "```plantuml" in low or "```puml" in low:
            print("       [!] 模板中含 mermaid/plantuml 围栏 → Skill 面向 Markdown→画板；本脚本不解析围栏")
        else:
            print("       ✓ 未检出 ```mermaid / plantuml 围栏（Skill 第 3-4 章主要为导入场景）")
        if re.search(r">\s*\[!([A-Z]+)\]", blob):
            print("       [!] 检出类似 MD Callout（[!NOTE] 等）→ 克隆后为普通文本；飞书高亮块为块型 19")
        else:
            print("       ✓ 未检出 MD Callout 围栏（Skill 规则 8：NOTE/WARNING/…）")
        print("       ✓ 图片：[*.png] → 上传 + replace_image（对齐 Skill TL;DR #10 思路）")
        print("       ✓ 文本：*dif →「上升/下降」+ 加粗着色（pp 跟进；rate_prin_od_dif/rate_cnt_od_dif：>=0 红、<0 绿；其余 dif：>=0 绿、<0 红）")

    # ==================== 主流程 ====================

    def generate_report(self, wiki_url, screenshots_dir, output_title=None):
        print("=" * 70)
        print("飞书周报文档生成器")
        print("=" * 70)

        self.calculate_all_params()

        print("[1/5] 获取访问令牌...")
        if not self.get_tenant_access_token():
            print("[ERR] 认证失败")
            return None
        print("[OK] 认证成功\n")

        # ============================================================
        # 模板分析步骤
        # ============================================================
        print("[2/5] 分析模板...")
        wt = wiki_url.split("/wiki/")[-1].split("?")[0] if "/wiki/" in wiki_url else wiki_url.split("/docx/")[-1].split("?")[0]
        doc_id_tpl = self.get_wiki_document_id(wt)
        if not doc_id_tpl:
            print("[ERR] 无法获取模板文档ID")
            return None
        blocks_tpl = self.get_document_blocks(doc_id_tpl)
        if not blocks_tpl:
            print("[ERR] 无法读取模板")
            return None
        print(f"[OK] 获取 {len(blocks_tpl)} 个块")
        self._print_feishu_doc_guide_alignment(blocks_tpl)

        # 分析: 文档结构
        page_tpl = next((b for b in blocks_tpl if b.get("block_type") == 1), None)
        if page_tpl:
            root_ids_tpl = page_tpl.get("children", [])
            print(f"[结构] 根children数: {len(root_ids_tpl)}")
            for i, cid in enumerate(root_ids_tpl[:5]):
                cb = {b["block_id"]: b for b in blocks_tpl}.get(cid)
                if cb:
                    bname = self.BT_MAP.get(cb.get("block_type"), ("type",))[0]
                    text = self._get_block_text(cb)[:40]
                    print(f"       [{i+1}] {bname:12s} | {text}")
            if len(root_ids_tpl) > 5:
                print(f"       ... 还有 {len(root_ids_tpl)-5} 个块")

        # 分析: 参数占位符
        all_params = set()
        all_imgs = set()
        for b in blocks_tpl:
            text = self._get_block_text(b)
            for m in re.finditer(r'\{(\w+)\}', text):
                all_params.add(m.group(1))
            for m in re.finditer(r'\[([^\]]+\.png)\]', text):
                all_imgs.add(m.group(1))
        print(f"[参数] 文本占位符: {', '.join(sorted(all_params))}")
        print(f"[参数] 图片占位符: {len(all_imgs)} 个")

        # 检查是否有未定义的参数
        defined_params = set(self.params.keys())
        undefined = all_params - defined_params
        if undefined:
            print(f"[WARN] 未定义的参数: {', '.join(sorted(undefined))}")
            # 为未定义参数添加默认值
            for p in undefined:
                self.params[p] = f"__{p}__"
                print(f"       -> 使用默认占位: {p} = __{p}__")

        # 检查图表是否齐全
        screenshots_path = Path(screenshots_dir)
        missing_imgs = [img for img in all_imgs if not (screenshots_path / img).exists()]
        if missing_imgs:
            print(f"[WARN] 缺失图表: {', '.join(missing_imgs)}")
        else:
            print(f"[OK] 全部 {len(all_imgs)} 张图表就绪")
        print()

        print("[3/6] 读取模板内容...")
        wt = wiki_url.split("/wiki/")[-1].split("?")[0] if "/wiki/" in wiki_url else wiki_url.split("/docx/")[-1].split("?")[0]
        doc_id = self.get_wiki_document_id(wt)
        if not doc_id:
            print("[ERR] 无法获取模板文档ID")
            return None
        blocks = self.get_document_blocks(doc_id)
        if not blocks:
            print("[ERR] 无法读取模板")
            return None
        print(f"[OK] 获取 {len(blocks)} 个块")

        self.blocks_by_id = {b["block_id"]: b for b in blocks}
        print(f"[OK] 索引完成\n")

        if not output_title:
            now = datetime.now()
            output_title = f"催收周报（{now.strftime('%Y-%m-%d')}）_{int(now.timestamp())}"

        # ---- 收集所有图片占位符（复制模式与克隆模式共用顺序） ----
        img_placeholder_map = {}
        img_placeholder_order = []
        seen_img_blocks = set()

        def collect_placeholders(blist):
            for b in blist:
                if b.get("block_type") == 1:
                    continue
                bid = b.get("block_id", "")
                if bid in seen_img_blocks:
                    continue
                fnames = self._ordered_png_placeholder_fnames(b)
                if fnames:
                    seen_img_blocks.add(bid)
                    for fname in fnames:
                        img_placeholder_order.append(fname)
                        img_placeholder_map[fname] = None
                for cid in b.get("children", []):
                    cb = self.blocks_by_id.get(cid)
                    if cb:
                        collect_placeholders([cb])

        collect_placeholders(blocks)
        print(f"   [INFO] 收集到 {len(img_placeholder_order)} 个图片占位符")

        use_clone_only = os.environ.get("FEISHU_REPORT_USE_CLONE", "").strip().lower() in ("1", "true", "yes")
        if not use_clone_only:
            wiki_node_token = wt if "/wiki/" in wiki_url else None
            cr = self._report_via_copy_template(
                doc_id, blocks, output_title, screenshots_dir, img_placeholder_order,
                wiki_token=wiki_node_token,
            )
            if cr:
                print("=" * 70)
                print(f"文档: {cr['title']}")
                print(f"链接: {cr['url']}")
                print("=" * 70)
                return cr
            print("   [copy] 复制模板不可用，改用空白文档逐块克隆（原生标题编号无法继承）")

        # 找到根page的children
        page_block = None
        for b in blocks:
            if b.get("block_type") == 1:
                page_block = b
                break
        if not page_block:
            print("[ERR] 无法找到根页面")
            return None

        root_children_ids = page_block.get("children", [])

        # ============================================================
        # 单次遍历模板，构建有序写入计划
        # 保持grid和普通块在root children中的原始顺序
        # ============================================================
        print("[4/6] 解析模板结构...")

        # ---- 单次遍历 root_children_ids，构建有序写入计划 ----
        # write_plan 中每个元素:
        #   {"type": "block", "data": {...}}  -> 普通块
        #   {"type": "block_img", "img_name": "xxx.png", "data": {...}}  -> 图片块（带文件名标记）
        #   {"type": "grid", ...}  -> grid框架（column内容中图片块也带有img_name标记）
        write_plan = []
        skip_mode = False

        def process_root_child(block):
            nonlocal skip_mode
            bt = block.get("block_type")
            ns = self._needs_skip(block)
            if ns == "start_skip":
                skip_mode = True
                return []
            if ns == "end_skip":
                skip_mode = False
            if skip_mode and ns != "end_skip":
                return []

            # --- 图片占位符 -> 空图片块（标记文件名）；同一块可写 [a.png][b.png] ---
            root_fnames = self._ordered_png_placeholder_fnames(block)
            if root_fnames:
                items = []
                for nm in root_fnames:
                    img_path = Path(screenshots_dir) / nm
                    if img_path.exists():
                        items.append({"type": "block_img", "img_name": nm,
                                      "data": {"block_type": 27, "image": {}}})
                return items

            # --- grid 容器 ---
            if bt == 24:
                col_cids = block.get("children", [])
                grid_clone = self._build_clone(block)
                columns_info = []
                for ccid in col_cids:
                    cb = self.blocks_by_id.get(ccid)
                    if cb and cb.get("block_type") == 25:
                        gc_clone = self._build_clone(cb)
                        col_content = []
                        for scid in cb.get("children", []):
                            scb = self.blocks_by_id.get(scid)
                            if scb:
                                col_fnames = self._ordered_png_placeholder_fnames(scb)
                                if col_fnames:
                                    for iname in col_fnames:
                                        sc_img_path = Path(screenshots_dir) / iname
                                        if sc_img_path.exists():
                                            col_content.append({
                                                "block_type": 27, "image": {},
                                                "_img_name": iname,
                                            })
                                    continue
                                sc = self._build_clone(scb)
                                if sc is not None:
                                    col_content.append(sc)
                        columns_info.append({
                            "data": gc_clone,
                            "content": col_content
                        })
                if columns_info:
                    return [{"type": "grid", "grid_clone": grid_clone, "columns": columns_info}]
                return []

            child = self._build_clone(block)
            if child is not None:
                return [{"type": "block", "data": child}]
            return []

        for cid in root_children_ids:
            cblock = self.blocks_by_id.get(cid)
            if cblock is None:
                continue
            write_plan.extend(process_root_child(cblock))

        block_count = sum(1 for item in write_plan if item["type"] in ("block", "block_img"))
        grid_count = sum(1 for item in write_plan if item["type"] == "grid")
        print(f"   [OK] 解析完成: {block_count} 个普通块, {grid_count} 个grid")

        # ============================================================
        # 写入阶段：
        #  按write_plan顺序写入
        # ============================================================

        print("[5/6] 创建并写入文档...")
        nd = self.create_document(output_title)
        if not nd:
            print("[ERR] 文档创建失败")
            return None
        nd_id = nd["document_id"]
        nd_url = f"https://www.feishu.cn/docx/{nd_id}"
        print(f"[OK] 文档ID: {nd_id}")

        # 获取根块ID
        resp = requests.get(f"{self.base_url}/docx/v1/documents/{nd_id}/blocks",
                            headers={"Authorization": f"Bearer {self.tenant_access_token}"},
                            params={"page_size": 10})
        rj = resp.json()
        if rj.get("code") != 0 or not rj["data"]["items"]:
            print("[ERR] 无法获取新文档结构")
            return None
        root_block_id = rj["data"]["items"][0]["block_id"]

        # ---- 按write_plan顺序写入 ----
        # 策略：
        #  - 普通块（type=block）→ 批量写入根page
        #  - 图片块（type=block_img）→ 逐个创建，立即建立 img_name -> block_id 映射
        #  - grid → 写入框架，然后逐个填充column内容
        batch = []
        pending_grids = []

        def create_single_img_block(parent_id, img_name):
            """创建一个图片块并记录其ID到映射中，返回 block_id 或 None"""
            data = self.add_children_to_block(nd_id, parent_id,
                                              [{"block_type": 27, "image": {}}])
            if data is None:
                return None
            created = data.get("children", [])
            for c in created:
                if isinstance(c, dict) and c.get("block_type") == 27:
                    bid = c["block_id"]
                    img_placeholder_map[img_name] = bid
                    return bid
                elif isinstance(c, str):
                    img_placeholder_map[img_name] = c
                    return c
            # 后备: add_children_to_block 可能返回不同的结构
            # 重新拉取文档块，找最后一个图片块
            try:
                all_new = self.get_document_blocks(nd_id)
                for b in reversed(all_new):
                    if b.get("block_type") == 27:
                        bid = b["block_id"]
                        img_placeholder_map[img_name] = bid
                        return bid
            except Exception:
                pass
            return None

        def flush_batch():
            nonlocal batch
            if not batch:
                return
            data = self.add_children_to_block(nd_id, root_block_id, batch)
            if data is None:
                print("[WARN] 批量写入失败")
            batch = []
            print("   .", end="", flush=True)

        for item in write_plan:
            if item["type"] == "block":
                batch.append(item["data"])
            elif item["type"] == "block_img":
                # 图片块逐个创建，建立精确的 img_name -> block_id 映射
                flush_batch()
                create_single_img_block(root_block_id, item["img_name"])
            elif item["type"] == "grid":
                # flush 当前batch
                flush_batch()
                # 写入grid框架
                grid_clone = item["grid_clone"]
                columns_info = item["columns"]
                grid_clone["grid"]["children"] = [ci["data"] for ci in columns_info]
                gdata = self.add_children_to_block(nd_id, root_block_id, [grid_clone])
                if gdata is not None:
                    print("   [G]", end="", flush=True)
                    pending_grids.append((columns_info, nd_id, root_block_id))
                else:
                    print("   [G-ERR]", end="", flush=True)

        # flush 剩余普通batch
        flush_batch()
        print()

        # ---- 填充grid_column内容 ----
        # grid column 中的图片也逐个创建，建立映射
        if pending_grids:
            print("   [填充grid列]...", end="", flush=True)
            new_blocks = self.get_document_blocks(nd_id)
            new_blocks_by_id = {b["block_id"]: b for b in new_blocks}

            new_grids_info = []
            for b in new_blocks:
                if b.get("block_type") == 24:
                    col_ids = []
                    for col_id in b.get("children", []):
                        col_b = new_blocks_by_id.get(col_id)
                        if col_b and col_b.get("block_type") == 25:
                            col_ids.append(col_id)
                    if col_ids:
                        new_grids_info.append(col_ids)

            for grid_idx, (columns_info, d_id, r_bid) in enumerate(pending_grids):
                if grid_idx >= len(new_grids_info):
                    print(f"\n[WARN] grid {grid_idx} 找不到列", end="", flush=True)
                    continue
                col_ids = new_grids_info[grid_idx]
                for col_idx, col_id in enumerate(col_ids):
                    if col_idx >= len(columns_info):
                        break
                    col_content = columns_info[col_idx]["content"]
                    if not col_content:
                        continue
                    # 批量写入整列：剔除内部 _ 前缀字段后一次 add_children
                    # 返回 children 数组按写入顺序对应 col_content 顺序，按位置精准匹配 _img_name → block_id
                    clean_items = [{k: v for k, v in item.items() if not k.startswith("_")} for item in col_content]
                    data = self.add_children_to_block(
                        d_id, col_id, clean_items,
                        debug_label=f"grid#{grid_idx} col#{col_idx} ({len(clean_items)} items)"
                    )
                    if data is None:
                        # 写入失败时，对该 col 内的图片做标记
                        for item in col_content:
                            img_name = item.get("_img_name")
                            if img_name:
                                print(f"\n   [ERR] 写入失败: grid#{grid_idx} col#{col_idx} img={img_name}", end="", flush=True)
                        continue
                    # 按位置匹配：returned children[i] ↔ col_content[i]
                    returned = data.get("children", [])
                    for i, item in enumerate(col_content):
                        img_name = item.get("_img_name")
                        if not img_name:
                            continue
                        new_bid = None
                        if i < len(returned):
                            r_item = returned[i]
                            if isinstance(r_item, dict) and r_item.get("block_type") == 27:
                                new_bid = r_item.get("block_id")
                            elif isinstance(r_item, str):
                                new_bid = r_item
                        if not new_bid:
                            # 后备：拉取该 col_id 的最新 children，找未使用的 image 块
                            col_blocks = self.get_document_blocks(d_id)
                            cb_by_id = {b["block_id"]: b for b in col_blocks}
                            col_b = cb_by_id.get(col_id)
                            if col_b:
                                used = set(v for v in img_placeholder_map.values() if v)
                                for cid in col_b.get("children", []):
                                    cb = cb_by_id.get(cid)
                                    if cb and cb.get("block_type") == 27 and cid not in used:
                                        new_bid = cid; break
                        if new_bid:
                            img_placeholder_map[img_name] = new_bid
                        else:
                            print(f"\n   [ERR] 未捕获 image block_id: grid#{grid_idx} col#{col_idx} img={img_name}", end="", flush=True)
                print(".", end="", flush=True)

            mapped_imgs = sum(1 for v in img_placeholder_map.values() if v is not None)
            print(f"\n   [OK] 已映射 {mapped_imgs}/{len(img_placeholder_order)} 个图片块")

        # ============================================================
        # 上传图片
        # ============================================================
        print("\n[上传图片]...")

        # 如果存在未映射的图片块，重新扫描文档中所有image块作为后备
        unmapped_names = [n for n in img_placeholder_order if not img_placeholder_map.get(n)]
        if unmapped_names:
            all_doc_blocks = self.get_document_blocks(nd_id)
            img_blocks_in_doc = [b for b in all_doc_blocks if b.get("block_type") == 27]
            if img_blocks_in_doc:
                # 按顺序分配：将unmapped的图片按顺序对应到文档中未使用的image块
                used_ids = set(v for v in img_placeholder_map.values() if v)
                available_img_blocks = [b for b in img_blocks_in_doc if b["block_id"] not in used_ids]
                for i, img_name in enumerate(unmapped_names):
                    if i < len(available_img_blocks):
                        img_placeholder_map[img_name] = available_img_blocks[i]["block_id"]
                        print(f"   [后备] {img_name} -> block_id={available_img_blocks[i]['block_id'][:12]}...")
                    else:
                        print(f"   [WARN] 无可用的图片块: {img_name}")

        up_ok = 0
        screenshots_path = Path(screenshots_dir)

        for img_name in img_placeholder_order:
            block_id = img_placeholder_map.get(img_name)
            if not block_id:
                print(f"   [WARN] 找不到图片块: {img_name}")
                continue
            img_path = screenshots_path / img_name
            if not img_path.exists():
                print(f"   [WARN] 文件不存在: {img_name}")
                continue
            if self._upload_image_to_block(nd_id, block_id, str(img_path)):
                up_ok += 1
                print(f"   [OK] {img_name}")
            else:
                print(f"   [ERR] {img_name}")

        print(f"\n[OK] 完成: 图片 {up_ok}/{len(img_placeholder_order)}")
        print("=" * 70)
        print(f"文档: {output_title}")
        print(f"链接: {nd_url}")
        print("=" * 70)
        return {"document_id": nd_id, "url": nd_url, "title": output_title}

    def _prepare_png_for_feishu(self, img_path: str) -> tuple[bytes, str, int, int]:
        """使用磁盘上的原始文件字节上传：不缩放、不重新编码。

        仅从文件读取像素宽高并传给 replace_image，避免飞书在未传宽高且检测失败时兜底为 100px。
        """
        from io import BytesIO
        from pathlib import Path

        p = Path(img_path)
        name = p.name
        raw = p.read_bytes()

        def _png_size_from_bytes(data: bytes) -> tuple[int, int] | None:
            if len(data) >= 24 and data[:8] == b"\x89PNG\r\n\x1a\n":
                w = int.from_bytes(data[16:20], "big")
                h = int.from_bytes(data[20:24], "big")
                if w > 0 and h > 0:
                    return w, h
            return None

        wh = _png_size_from_bytes(raw)
        if wh:
            return raw, name, wh[0], wh[1]

        try:
            from PIL import Image

            with Image.open(BytesIO(raw)) as im:
                w, h = im.size
                if w > 0 and h > 0:
                    return raw, name, w, h
        except Exception:
            pass

        # 无法解析尺寸时的保守占位（不应常见于周报 PNG）
        return raw, name, 1600, 900

    def _upload_image_to_block(self, doc_id, block_id, img_path):
        import time
        import mimetypes

        try:
            if not img_path:
                return False
            fc, fn, img_w, img_h = self._prepare_png_for_feishu(img_path)
            img_w = max(1, min(int(img_w), 8192))
            img_h = max(1, min(int(img_h), 8192))
            ct, _ = mimetypes.guess_type(img_path)
            ct = ct or "image/png"
            sz = len(fc)
            # 上传阶段也加 retry：429 时退避重试
            # 使用 requests 内置 multipart（files + data），无需 requests_toolbelt
            ft = None
            headers_auth = {"Authorization": f"Bearer {self.tenant_access_token}"}
            post_url = f"{self.base_url}/drive/v1/medias/upload_all"
            form_data = {
                "file_name": fn,
                "parent_type": "docx_image",
                "parent_node": block_id,
                "size": str(sz),
            }
            file_field = {"file": (fn, fc, ct)}
            for attempt in range(5):
                ur = requests.post(post_url, headers=headers_auth, data=form_data, files=file_field)
                if ur.status_code == 429:
                    time.sleep(0.5 * (2 ** attempt)); continue
                if ur.status_code != 200 or ur.json().get("code") != 0:
                    return False
                ft = ur.json()["data"]["file_token"]
                break
            if not ft:
                return False
            repl = {"token": ft, "width": img_w, "height": img_h, "align": 2}
            for attempt in range(5):
                pr = requests.patch(f"{self.base_url}/docx/v1/documents/{doc_id}/blocks/{block_id}",
                                    headers={"Authorization": f"Bearer {self.tenant_access_token}",
                                             "Content-Type": "application/json"},
                                    json={"replace_image": repl})
                if pr.status_code == 429:
                    time.sleep(0.5 * (2 ** attempt)); continue
                ok = pr.status_code == 200 and pr.json().get("code") == 0
                time.sleep(0.1)
                return ok
            return False
        except Exception:
            return False


def main():
    import webbrowser
    aid, sec = load_feishu_app_credentials(_PROJECT_ROOT)
    if not aid or not sec:
        print(FEISHU_CREDENTIALS_HELP)
        sys.exit(1)
    g = FeishuReportGenerator(aid, sec, str(_PROJECT_ROOT / "data"))
    r = g.generate_report(
        "https://fintopia.feishu.cn/wiki/WHruwVACAi8nWPkXYgQcrLhHnFb",
        str(_PROJECT_ROOT / "screenshots"),
    )
    if r:
        print("\n[OK] 周报生成成功!")
        webbrowser.open(r["url"])
    else:
        print("\n[ERR] 周报生成失败")


if __name__ == "__main__":
    main()
