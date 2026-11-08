# coding:utf8
"""easyquotation 本机冒烟测试：逐个数据源验证可用性。"""
import json
import sys
import traceback
from typing import cast

import easyquotation
from easyquotation.boc import Boc
from easyquotation.jsl import Jsl

RESULTS = {}


def _jsl() -> Jsl:
    return cast(Jsl, easyquotation.use("jsl"))


def _boc() -> Boc:
    return cast(Boc, easyquotation.use("boc"))


def check(name):
    def deco(fn):
        try:
            out = fn()
            RESULTS[name] = ("OK", out)
        except Exception as e:  # noqa
            RESULTS[name] = ("FAIL", f"{type(e).__name__}: {e}")
            traceback.print_exc()
        return fn
    return deco


@check("sina.real")
def _():
    q = easyquotation.use("sina")
    return q.real("600519")


@check("sina.real.prefix")
def _():
    q = easyquotation.use("sina")
    return q.real(["sh000001", "sz000001"], prefix=True)


@check("sina.market_snapshot")
def _():
    q = easyquotation.use("sina")
    d = q.market_snapshot(prefix=True)
    return {"count": len(d), "sample": list(d.items())[:1]}


@check("tencent.real")
def _():
    q = easyquotation.use("tencent")
    return q.real("600519")


@check("tencent.real.prefix")
def _():
    q = easyquotation.use("tencent")
    return q.real(["sh000001", "sz000001"], prefix=True)


@check("hkquote.real")
def _():
    q = easyquotation.use("hkquote")
    return q.real(["00700", "00001"])


@check("daykline.real")
def _():
    q = easyquotation.use("daykline")
    return q.real(["00700"])


@check("jsl.etfindex")
def _():
    q = _jsl()
    return q.etfindex()


@check("jsl.etfindex.paged")
def _():
    """分页参数应被真正拼进 URL（上游写死 rp=25&page=1，无法翻页）。"""
    q = _jsl()
    return q.etfindex(rp=50, page=3)


@check("jsl.etfindex.discount_filter")
def _():
    """折溢价过滤在字段为 "-" 时不应抛 ValueError。"""
    q = _jsl()
    return q.etfindex(max_discount="-0.4", min_discount="-1.3%")


@check("jsl.qdii")
def _():
    q = _jsl()
    return q.qdii()


@check("boc.get_exchange_rate")
def _():
    q = _boc()
    return q.get_exchange_rate()


@check("boc.get_exchange_rate.hkd")
def _():
    q = _boc()
    return q.get_exchange_rate("hkd")


@check("helpers.get_stock_codes")
def _():
    return len(easyquotation.get_stock_codes())


if __name__ == "__main__":
    for k, (st, v) in RESULTS.items():
        if st == "OK":
            s = json.dumps(v, ensure_ascii=False, default=str)
            print(f"[OK]   {k}: {s[:400]}")
        else:
            print(f"[FAIL] {k}: {v}")
    fails = [k for k, (st, _) in RESULTS.items() if st != "OK"]
    print("\nSUMMARY: ok=%d fail=%d %s" % (
        len(RESULTS) - len(fails), len(fails), fails))
    sys.exit(1 if fails else 0)
