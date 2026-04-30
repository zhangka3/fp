#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""飞书周报文档生成器 - 保留完整格式（含grid分栏）"""

import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import requests
import re
import os
import json
from pathlib import Path
from datetime import datetime, timedelta

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
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
        url = f"{self.base_url}/wiki/v2/spaces/get_node"
        headers = {"Authorization": f"Bearer {self.tenant_access_token}"}
        resp = requests.get(url, headers=headers, params={"token": wiki_token})
        if resp.status_code == 200:
            r = resp.json()
            if r.get("code") == 0:
                return r["data"]["node"]["obj_token"]
        return None

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

    def add_children_to_block(self, doc_id, block_id, children, debug_label="", max_retries=4):
        """给指定块添加children；HTTP 429 限流时指数退避重试。"""
        import time
        url = f"{self.base_url}/docx/v1/documents/{doc_id}/blocks/{block_id}/children"
        headers = {"Authorization": f"Bearer {self.tenant_access_token}", "Content-Type": "application/json"}
        for attempt in range(max_retries + 1):
            resp = requests.post(url, headers=headers, json={"children": children})
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

        # 计算周维度催回率参数（从m0_billing_grouped.json计算）
        self._calculate_weekly_collection_rates()

        # 计算月维度催回率参数（从m0_billing.json计算，与 m0_collection_rate_7d_30d_monthly.png 对齐）
        self._calculate_monthly_collection_rates()

    def _calculate_weekly_collection_rates(self):
        """计算 {wk_colrate7d}, {wk_colrate7d_dif}, {wk_colrate15d}, {wk_colrate15d_dif}

        与 [m0_collection_rate_weekly.png] 完全对齐：
          - 数据源：m0_billing.json（不是 grouped）
          - 周分组：周日为周起始（与 screen_m0.aggregate_weekly_data 一致）
          - 成熟度：week_end + N 天 < data_fetch_date
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
                week_end = week_start + 6, 要求 week_end + mature_days < fetch_date 才成熟。
                只保留 pd1>0 且成熟的周，取最新与上一作差。"""
                mature = []
                for wk in sorted_wks:
                    week_start = datetime.strptime(wk, '%Y-%m-%d')
                    week_end = week_start + timedelta(days=6)
                    bucket = buckets[wk]
                    if bucket['pd1'] > 0 and (week_end + timedelta(days=mature_days)) < data_fetch_date:
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
        口径（与 screen_m0.aggregate_monthly_data 一致）：
          - 同期对比：每月只取 day <= (fetch_date - mature_days).day 的记录
          - mature_days=8  → 7d 催回率：col = (pd1 - pd8)/pd1 * 100
          - mature_days=31 → 30d 催回率：col = (pd1 - pd31)/pd1 * 100
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

            cutoff_7d = (fetch_date - timedelta(days=8)).day
            cutoff_30d = (fetch_date - timedelta(days=31)).day

            mth_7d = defaultdict(lambda: {'pd1': 0.0, 'pd8': 0.0})
            mth_30d = defaultdict(lambda: {'pd1': 0.0, 'pd31': 0.0})
            for row in rows:
                if not isinstance(row, list) or len(row) < 14:
                    continue
                bdate = datetime.strptime(row[0], '%Y-%m-%d')
                mkey = row[0][:7]
                if bdate.day <= cutoff_7d:
                    mth_7d[mkey]['pd1'] += float(row[4]) or 0
                    mth_7d[mkey]['pd8'] += float(row[8]) or 0
                if bdate.day <= cutoff_30d:
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

    def _set_monthly_defaults(self):
        self.params.update({
            'mth_colrate7d': 'XX.XX%', 'mth_colrate7d_dif': 'X.XX',
            'mth_colrate30d': 'XX.XX%', 'mth_colrate30d_dif': 'X.XX',
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
        for k, v in self.params.items():
            text = text.replace("{" + k + "}", str(v))
        return text.replace("[DD1]", self.params.get('DD1', '')).replace("[DD]", self.params.get('DD', '')).replace("[mm]", self.params.get('mm', ''))

    # ==================== 块处理 ====================

    BT_MAP = {
        1: ("page", "page"), 2: ("text", "text"), 3: ("heading1", "heading1"),
        4: ("heading2", "heading2"), 5: ("heading3", "heading3"),
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
                result.append({
                    "text_run": {
                        "content": self.replace_params_in_text(tr.get("content", "")),
                        "text_element_style": tr.get("text_element_style", {})
                    }
                })
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

        if bt in (2, 12, 13):
            elements = self._clone_elements(bd)
            child[dk] = {"elements": elements}
            # 复制块级样式（含 align 对齐等），保留原始排版格式
            block_style = bd.get("style")
            if block_style:
                child[dk]["style"] = block_style
        elif bt == 22:
            child[dk] = {}
        elif bt in (3, 4, 5):
            elements = self._clone_elements(bd)
            child[dk] = {"elements": elements, "style": bd.get("style", {})}
        elif bt == 24:
            child[dk] = {"column_size": bd.get("column_size", 1)}
        elif bt == 25:
            child[dk] = {"width_ratio": bd.get("width_ratio", 50)}
        elif bt == 27:
            child[dk] = {}
        else:
            return None

        return child

    def _is_png_placeholder(self, block):
        text = self._get_block_text(block).strip()
        return re.match(r'^\[([^\]]+\.png)\]$', text)

    def _needs_skip(self, block):
        text = self._get_block_text(block).strip()
        if re.match(r'^0[、.,\s]*插入参数', text):
            return "start_skip"
        if re.match(r'^一[、.,\s]*核心结果指标', text):
            return "end_skip"
        return False

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

        # ---- 收集所有图片占位符 ----
        # 使用 dict: 文件名 -> block_id（创建空图片块后填充）
        img_placeholder_map = {}  # filename -> block_id
        img_placeholder_order = []
        seen_img_blocks = set()

        def collect_placeholders(blist):
            for b in blist:
                if b.get("block_type") == 1:
                    continue
                bid = b.get("block_id", "")
                if bid in seen_img_blocks:
                    continue
                png_m = self._is_png_placeholder(b)
                if png_m:
                    seen_img_blocks.add(bid)
                    fname = png_m.group(1)
                    img_placeholder_order.append(fname)
                    img_placeholder_map[fname] = None
                for cid in b.get("children", []):
                    cb = self.blocks_by_id.get(cid)
                    if cb:
                        collect_placeholders([cb])

        collect_placeholders(blocks)
        print(f"   [INFO] 收集到 {len(img_placeholder_order)} 个图片占位符")

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

            # --- 图片占位符 -> 空图片块（标记文件名） ---
            png_m = self._is_png_placeholder(block)
            if png_m:
                img_path = Path(screenshots_dir) / png_m.group(1)
                if img_path.exists():
                    return [{"type": "block_img", "img_name": png_m.group(1),
                             "data": {"block_type": 27, "image": {}}}]
                else:
                    return []

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
                                sc = self._build_clone(scb)
                                if sc is not None:
                                    sc_png_m = self._is_png_placeholder(scb)
                                    if sc_png_m:
                                        sc_img_path = Path(screenshots_dir) / sc_png_m.group(1)
                                        if sc_img_path.exists():
                                            sc = {"block_type": 27, "image": {},
                                                  "_img_name": sc_png_m.group(1)}
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
        if not output_title:
            output_title = f"周报自动化 - {datetime.now().strftime('%Y年%m月%d日')}"
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
            """创建一个图片块并记录其ID到映射中"""
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

    def _upload_image_to_block(self, doc_id, block_id, img_path):
        import time
        try:
            from requests_toolbelt.multipart.encoder import MultipartEncoder
            import mimetypes
            fn = os.path.basename(img_path)
            with open(img_path, "rb") as f:
                fc = f.read()
            ct, _ = mimetypes.guess_type(img_path)
            # 上传阶段也加 retry：429 时退避重试
            ft = None
            for attempt in range(5):
                md = MultipartEncoder(fields={
                    "file_name": fn, "parent_type": "docx_image", "parent_node": block_id,
                    "size": str(os.path.getsize(img_path)),
                    "file": (fn, fc, ct or "image/png")
                })
                uh = {"Authorization": f"Bearer {self.tenant_access_token}", "Content-Type": md.content_type}
                ur = requests.post(f"{self.base_url}/drive/v1/medias/upload_all", headers=uh, data=md)
                if ur.status_code == 429:
                    time.sleep(0.5 * (2 ** attempt)); continue
                if ur.status_code != 200 or ur.json().get("code") != 0:
                    return False
                ft = ur.json()["data"]["file_token"]
                break
            if not ft:
                return False
            for attempt in range(5):
                pr = requests.patch(f"{self.base_url}/docx/v1/documents/{doc_id}/blocks/{block_id}",
                                    headers={"Authorization": f"Bearer {self.tenant_access_token}",
                                             "Content-Type": "application/json"},
                                    json={"replace_image": {"token": ft}})
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
        "https://fintopia.feishu.cn/wiki/IahEwSFsLi7ZAmkvvMQcOg8pnwh",
        str(_PROJECT_ROOT / "screenshots"),
    )
    if r:
        print("\n[OK] 周报生成成功!")
        webbrowser.open(r["url"])
    else:
        print("\n[ERR] 周报生成失败")


if __name__ == "__main__":
    main()
