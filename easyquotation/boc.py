# coding:utf8
"""中国银行外汇牌价。

上游原实现用固定下标 ``data[-13]`` / ``data[-15]`` 取值，且不指定响应编码，
在 boc.cn 改版后返回的是无意义字符串（如 ``{"sell": "40.2", "buy": "00:00:05"}``），
中文货币名还因 requests 默认按 ISO-8859-1 解码而变成乱码。

这里改为按表头语义解析每一行，并用中文名反查目标货币。
"""
import re

import requests

# 币种代码 -> 中行页面上的中文货币名
CURRENCY_NAMES = {
    "usa": "美元",
    "hkd": "港币",
    "eur": "欧元",
    "jpy": "日元",
    "gbp": "英镑",
    "aud": "澳大利亚元",
    "cad": "加拿大元",
    "chf": "瑞士法郎",
    "sgd": "新加坡元",
    "nzd": "新西兰元",
    "krw": "韩国元",
    "mop": "澳门元",
    "twd": "新台币",
    "thb": "泰国铢",
    "myr": "林吉特",
    "idr": "印尼卢比",
    "inr": "印度卢比",
    "rub": "卢布",
    "zar": "南非兰特",
    "mxn": "墨西哥比索",
    "czk": "捷克克朗",
    "dkk": "丹麦克朗",
    "sek": "瑞典克朗",
    "nok": "挪威克朗",
    "brl": "巴西雷亚尔",
    "try": "土耳其里拉",
}


class Boc:
    """中行外汇牌价"""

    url = "http://www.boc.cn/sourcedb/whpj/"

    # 表头 -> 列下标（页面结构变化时只需改这里）
    COLUMNS = {
        "name": 0,
        "现汇买入价": 1,
        "现钞买入价": 2,
        "现汇卖出价": 3,
        "现钞卖出价": 4,
        "中行折算价": 5,
    }

    def _fetch_rows(self):
        """返回 [(货币名, {列名: 值}), ...]"""
        rep = requests.get(self.url, timeout=15)
        rep.encoding = "utf-8"

        rows = []
        for raw in re.findall(r"<tr[^>]*>(.*?)</tr>", rep.text, re.S):
            cells = [
                re.sub(r"<[^>]+>", "", c).strip()
                for c in re.findall(r"<td[^>]*>(.*?)</td>", raw, re.S)
            ]
            if len(cells) < 6 or not cells[0]:
                continue
            record = {
                key: cells[idx] for key, idx in self.COLUMNS.items() if idx < len(cells)
            }
            rows.append((cells[0], record))
        return rows

    def get_exchange_rate(self, currency="usa"):
        """返回指定币种的牌价。

        :param currency: 币种代码，默认 ``usa``（美元）。也接受中文名（如 ``美元``）。
        :return: ``{"sell": 现汇卖出价, "buy": 现汇买入价, ...}``；
                 牌价语义以中行为准——``buy`` 是中行买入外汇的价格（你卖出外汇的价格），
                 ``sell`` 是中行卖出外汇的价格（你买入外汇的价格）。
                 找不到该币种时返回 ``{}``。
        """
        name = CURRENCY_NAMES.get(currency.lower(), currency)
        for currency_name, record in self._fetch_rows():
            if currency_name != name:
                continue
            result = dict(record)
            result["sell"] = record.get("现汇卖出价", "")
            result["buy"] = record.get("现汇买入价", "")
            result.pop("name", None)
            return result
        return {}

    def get_exchange_rates(self):
        """返回所有币种的牌价，键为中文货币名。"""
        return {name: record for name, record in self._fetch_rows()}
