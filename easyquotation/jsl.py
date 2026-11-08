# coding:utf8
"""
获取集思路的数据
"""
import json
import time
from typing import Optional

import requests


def _pct(value):
    """把集思路返回的折溢价字段转成 float 或 None（"-" 表示不适用）。"""
    if value is None:
        return None
    text = str(value).strip()
    if text in ("", "-"):
        return None
    return float(text.strip("%")) / 100.0


def _pct_ge(value, threshold):
    """折溢价是否 >= threshold（"-" 视为不适用，排除）。"""
    pct = _pct(value)
    return pct is not None and pct >= threshold


def _pct_le(value, threshold):
    """折溢价是否 <= threshold（"-" 视为不适用，排除）。"""
    pct = _pct(value)
    return pct is not None and pct <= threshold


def _num(value):
    """把集思路的数值字段转成 float，缺失或 "-" 返回 None。"""
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if text in ("", "-"):
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _num_ge(value, threshold):
    """数值是否 >= threshold（缺失或 "-" 视为不满足）。"""
    num = _num(value)
    return num is not None and num >= threshold


def _parse_cookie(cookie: str) -> dict:
    """把浏览器复制的 Cookie 字符串解析成 requests 用的 dict。

    接受 "k=v; k2=v2" 这种原始格式，也接受已经是 dict 的情况。
    """
    if isinstance(cookie, dict):
        return cookie
    jar = {}
    for part in (cookie or "").split(";"):
        if "=" not in part:
            continue
        name, _, value = part.partition("=")
        name = name.strip()
        if name:
            jar[name] = value.strip()
    return jar


class Jsl:
    """
    抓取集思路的数据
    """

    # 集思录登录接口
    __jsl_login_url = "https://www.jisilu.cn/account/ajax/login_process/"

    # 集思路 ETF 接口
    # pylint: disable=line-too-long
    __etf_index_url = "https://www.jisilu.cn/data/etf/etf_list/?___jsl=LST___t={ctime:d}&rp={rp:d}&page={page:d}"

    # 黄金 ETF , 货币 ETF 留坑,未完成
    __etf_gold_url = (
        "https://www.jisilu.cn/jisiludata/etf.php?qtype=pmetf&___t={ctime:d}"
    )
    __etf_money_url = (
        "https://www.jisilu.cn/data/money_fund/list/?___t={ctime:d}"
    )

    # 集思录QDII接口
    __qdii_url = "https://www.jisilu.cn/data/qdii/qdii_list/?___t={ctime:d}"
    # 可转债
    __cb_url = "https://www.jisilu.cn/data/cbnew/cb_list/?___t={ctime:d}"

    def __init__(self):
        self.__funda = None
        self.__fundm = None
        self.__fundb = None
        self.__fundarb = None
        self.__etfindex = None
        self.__qdii = None
        self.__cb = None
        self._cookie: Optional[str] = None

    def set_cookie(self, cookie: str):
        self._cookie = cookie

    def _get_headers(self) -> dict:
        default = {
            # pylint: disable=line-too-long
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko",
        }
        if self._cookie:
            default = {**default, 'Cookie': self._cookie}
        return default

    @staticmethod
    def formatetfindexjson(fundbjson):
        """格式化集思录返回 指数ETF 的json数据,以字典形式保存"""
        result = {}
        for row in fundbjson["rows"]:
            cell = row["cell"]
            fundb_id = cell["fund_id"]
            result[fundb_id] = cell
        return result

    @staticmethod
    def formatjisilujson(data):
        result = {}
        for row in data["rows"]:
            cell = row["cell"]
            id_ = row["id"]
            result[id_] = cell
        return result

    @staticmethod
    def percentage2float(per):
        """
        将字符串的百分数转化为浮点数
        :param per:
        :return:
        """
        if per is None:
            return None
        text = str(per).strip()
        if text in ("", "-"):
            # 集思路对不适用折溢价的品种返回 "-"，上游直接 float() 会抛 ValueError
            return None
        return float(text.strip("%")) / 100.


    def etfindex(
        self,
        index_id="",
        min_volume=0,
        max_discount=None,
        min_discount=None,
        rp=25,
        page=1,
    ):
        """
        以字典形式返回 指数ETF 数据
        :param index_id: 获取指定的指数
        :param min_volume: 最小成交量
        :param max_discount: 最高溢价率, 适用于折价套利, 格式 "-1.2%", "-1.2", -0.012 三种均可
        :param min_discount: 最低溢价率, 适用于溢价套利, 格式 "-1.2%", "-1.2", -0.012 三种均可
        :param rp: 每页条数
        :param page: 页码
        :return: {"fund_id":{}}
        """
        # 添加当前的ctime
        etf_index_url = self.__etf_index_url.format(
            ctime=int(time.time()), rp=rp, page=page
        )
        # 请求数据
        # 上游用裸 requests.get，既不带 Cookie 也不带 UA：
        # 游客调用时集思录只返回前 20 条（共 1451 条），且折溢价字段全是 "-"。
        # 这里改用带 Cookie / UA 的 session，登录后即可取到完整列表与折溢价。
        session = requests.Session()
        headers = self._get_headers()
        headers["Referer"] = "https://www.jisilu.cn/data/etf/"
        headers["X-Requested-With"] = "XMLHttpRequest"
        rep = session.get(etf_index_url, headers=headers, timeout=15)
        etf_json = rep.json()

        # 格式化返回的json字符串
        data = self.formatetfindexjson(etf_json)

        # 过滤
        if index_id:
            # 指定跟踪的指数代码
            data = {
                fund_id: cell
                for fund_id, cell in data.items()
                if cell["index_id"] == index_id
            }
        if min_volume:
            # 过滤小于指定交易量的数据
            data = {
                fund_id: cell
                for fund_id, cell in data.items()
                if _num_ge(cell.get("volume"), min_volume)
            }
        if min_discount is not None:
            # 指定最小溢价率
            if isinstance(min_discount, str):
                if min_discount.endswith("%"):
                    # 如果是字符串形式,先转为浮点形式
                    min_discount = self.percentage2float(min_discount)
                else:
                    min_discount = float(min_discount) / 100.
            data = {
                fund_id: cell
                for fund_id, cell in data.items()
                if _pct_ge(cell["discount_rt"], min_discount)
            }
        if max_discount is not None:
            # 指定最大溢价率
            if isinstance(max_discount, str):
                if max_discount.endswith("%"):
                    # 如果是字符串形式,先转为浮点形式
                    max_discount = self.percentage2float(max_discount)
                else:
                    max_discount = float(max_discount) / 100.
            data = {
                fund_id: cell
                for fund_id, cell in data.items()
                if _pct_le(cell["discount_rt"], max_discount)
            }

        self.__etfindex = data
        return self.__etfindex

    def qdii(self, min_volume=0):
        """以字典形式返回QDII数据
        :param min_volume:最小交易量，单位万元
        """
        # 添加当前的ctime
        # 上游写的是 self.__qdii_url = self.__qdii_url.format(...)，
        # 第一次调用后实例属性已被替换成格式化过的 URL，第二次调用会因为
        # URL 里没有 {ctime} 占位符而保留旧时间戳。改用局部变量。
        qdii_url = self.__qdii_url.format(ctime=int(time.time()))
        # 请求数据
        rep = requests.get(qdii_url, timeout=15)
        # 获取返回的json字符串
        fundjson = json.loads(rep.text)
        # 格式化返回的json字符串
        data = self.formatjisilujson(fundjson)
        data = {x: y for x, y in data.items() if y["notes"] != "估值有问题"}
        # 过滤小于指定交易量的数据
        if min_volume:
            data = {
                k: data[k]
                for k in data
                if _num_ge(data[k].get("volume"), min_volume)
            }

        self.__qdii = data
        return self.__qdii

    # pylint: disable=invalid-name
    def cb(self, min_volume=0, cookie: str=None):
        """以字典形式返回可转债数据
        :param min_volume:最小交易量，单位万元
        :param cookie: 登陆凭证，可以从浏览器获取的对应 Cookie
        """
        # 添加当前的ctime
        cb_url = self.__cb_url.format(ctime=int(time.time()))
        # 请求数据
        session = requests.Session()
        if cookie:
            # 上游签名里有 cookie 形参却从未使用它，导致传了凭证也不生效。
            session.cookies.update(_parse_cookie(cookie))
        headers = self._get_headers()
        headers["Referer"] = "https://www.jisilu.cn/data/cbnew/"
        headers["X-Requested-With"] = "XMLHttpRequest"
        rep = session.get(cb_url, headers=headers, timeout=15)
        # 集思录未登录（或 Cookie 失效）时该接口返回 200 + 空 body，
        # 直接 json.loads 会抛出难以定位的 JSONDecodeError。
        if not rep.text.strip():
            raise ValueError(
                "集思录可转债接口返回空内容：该接口需要登录后的 Cookie，"
                "请调用 cb(cookie='从浏览器复制的 Cookie')"
            )
        # 获取返回的json字符串
        fundjson = json.loads(rep.text)
        # 格式化返回的json字符串
        data = self.formatjisilujson(fundjson)
        # 过滤小于指定交易量的数据
        if min_volume:
            data = {
                k: data[k]
                for k in data
                if _num_ge(data[k].get("volume"), min_volume)
            }

        self.__cb = data
        return self.__cb


if __name__ == "__main__":
    Jsl().etfindex(
        index_id="000016",
        min_volume=0,
        max_discount="-0.4",
        min_discount="-1.3%",
    )
