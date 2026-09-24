# -*- coding: utf-8 -*-
"""
菜价雷达 · 里程碑0 演示页生成器（独立运行, 不依赖 Vue/SpringBoot）
==================================================================
读取 python/data/price.db（SQLite, 经 python/config/db.py 可切 MySQL）,
用 pyecharts 生成 demo/price_demo.html, 并自动内联 echarts 库 →
**单文件、离线、双击即开**（首次生成时下载 echarts.min.js 需联网, 之后不再需要）:

  图1 · 近90天五品类批发均价趋势折线
  图2 · 大白菜近3年日度均价走势（带缩放滑块）
  图3 · 五品类最新日环比涨跌条形图（红涨绿跌）
  图4 · 大白菜近两年均价 + ARIMA 未来7天预测（虚线）+ 测试集 MAPE 标注
        ★ 预测结果仅供参考（行政性监测工具, 不构成任何买卖建议）

运行:  python demo/quick_view.py
"""
import re
import sys
import warnings
from datetime import timedelta
from pathlib import Path

# Windows 控制台中文输出保护
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]           # 工作区根目录
sys.path.insert(0, str(ROOT / "python"))             # 引入 python/config
from config.db import get_connection, cursor, DB_BACKEND  # noqa: E402

import numpy as np                                    # noqa: E402
import pandas as pd                                   # noqa: E402
from pyecharts import options as opts                 # noqa: E402
from pyecharts.charts import Bar, Line, Page          # noqa: E402
from pyecharts.commons.utils import JsCode            # noqa: E402

warnings.filterwarnings("ignore")                     # ARIMA 收敛告警等演示噪音

CATEGORIES = ["大白菜", "黄瓜", "西红柿", "猪肉", "鸡蛋"]
# 与采集器一致的品类词替换（探测实测: 西红柿/猪肉 在新发地无有效行情, 用番茄/白条猪）
OVERRIDE = {"西红柿": ["番茄"], "猪肉": ["白条猪"]}
# 品类语义优先代表品(2026-09单位核查: "鸡蛋"无精确品名; 箱鸡蛋存在 箱/斤 双计价且斤标注被箱价污染,
# 散鸡蛋为单位单一的纯斤价序列, 语义贴近日常"鸡蛋", 故优先)
PREFERRED = {"鸡蛋": "散鸡蛋"}
OUT_HTML = Path(__file__).resolve().parent / "price_demo.html"
LOCAL_JS = Path(__file__).resolve().parent / "echarts.min.js"   # 本地缓存的 echarts 库
PALETTE = ["#5470c6", "#91cc75", "#fac858", "#ee6666", "#73c0de"]
INIT = dict(width="1150px", height="440px")


# ---------------------------------------------------------------- 离线内联 echarts
def ensure_echarts_js(primary_url: str) -> bool:
    """确保本地存在 echarts.min.js（>100KB 视为有效）; 优先下载页面同版本, 失败试镜像"""
    if LOCAL_JS.exists() and LOCAL_JS.stat().st_size > 100_000:
        return True
    import requests
    mirrors = [
        primary_url,                                                # 与页面引用完全同版本
        "https://cdn.jsdelivr.net/npm/echarts@6/dist/echarts.min.js",
        "https://registry.npmmirror.com/echats/6/files/dist/echarts.min.js",
    ]
    for url in mirrors:
        try:
            r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            if r.ok and len(r.content) > 100_000:
                LOCAL_JS.write_bytes(r.content)
                print(f"已缓存 echarts.min.js ({len(r.content) // 1024} KB) <- {url}")
                return True
        except Exception as exc:
            print(f"  下载失败 {url}: {exc}")
    return False


def inline_echarts(html_path: Path) -> bool:
    """把 <script src=CDN> 替换为内联 JS → HTML 单文件化, 双击离线可开
    成功返回 True; 失败保留 CDN 引用(需联网), 返回 False"""
    html = html_path.read_text(encoding="utf-8")
    m = re.search(r'<script[^>]+src="([^"]+)"[^>]*></script>', html)
    if not m:
        return True  # 已是内联结构, 无需处理
    if not ensure_echarts_js(m.group(1)):
        print("[警告] 未能内联 echarts(下载失败), 页面将依赖联网加载 CDN")
        return False
    js = LOCAL_JS.read_text(encoding="utf-8")
    html = html.replace(m.group(0), '<script type="text/javascript">\n' + js + "\n</script>", 1)
    html_path.write_text(html, encoding="utf-8")
    return True


# ---------------------------------------------------------------- 数据加载
def load_df() -> pd.DataFrame:
    """读库 → [prod_name, pub_date, avg_price, unit_info]（只读快照, 不现场爬取）"""
    conn = get_connection()
    with cursor(conn) as cur:
        cur.execute("SELECT prod_name, pub_date, avg_price, unit_info "
                    "FROM price_daily WHERE avg_price IS NOT NULL")
        rows = cur.fetchall()
    conn.close()
    df = pd.DataFrame(rows, columns=["prod_name", "pub_date", "avg_price", "unit_info"])
    df["pub_date"] = pd.to_datetime(df["pub_date"])
    # 跨后端兼容: MySQL DECIMAL 经 pymysql 返回 Decimal(object dtype), 需显式转数值
    df["avg_price"] = pd.to_numeric(df["avg_price"], errors="coerce")
    return df[df["avg_price"].notna()]


def dominant_unit(df: pd.DataFrame, name: str) -> str:
    """某品名的主导计价单位"""
    sub = df[df["prod_name"] == name]["unit_info"].dropna()
    return str(sub.mode().iat[0]) if len(sub) else ""


def representative(df: pd.DataFrame, term: str):
    """品类词 → 实际品名: 精确 > 替换词 > 语义优先品 > 单位纯净的模糊匹配
    (单位异构治理: 优先选"计价单位只有斤"的品名, 避免箱/筐整件价混入同轴对比)"""
    names = set(df["prod_name"].unique())
    for cand in [term, *OVERRIDE.get(term, []), PREFERRED.get(term, "")]:
        if cand and cand in names:
            return cand, ("精确" if cand == term else "替换")
    like = [n for n in names if term in n]
    if like:
        clean = [n for n in like
                 if set(df[df["prod_name"] == n]["unit_info"].dropna()) == {"斤"}]
        pool = clean or like
        top = df[df["prod_name"].isin(pool)].groupby("prod_name").size().idxmax()
        return top, "模糊" + ("(单位过滤)" if clean else "")
    return None, ""


def daily_avg(df: pd.DataFrame, name: str) -> pd.Series:
    """某品名 → 按发布日期聚合的日度均价序列(仅取该品名主导单位的行, 剔除异单位污染)"""
    sub = df[df["prod_name"] == name]
    unit = dominant_unit(df, name)
    if unit:
        sub = sub[(sub["unit_info"] == unit) | (sub["unit_info"].isna())]
    return sub.groupby("pub_date")["avg_price"].mean().sort_index()


def unit_of(df: pd.DataFrame, name: str) -> str:
    """该品名的主导计价单位（新发地实测多为'斤'）"""
    sub = df[df["prod_name"] == name]["unit_info"].dropna()
    return str(sub.mode().iat[0]) if len(sub) else "斤"


def fl(v):
    """pandas/numpy 值 → JS 可序列化的 float（缺测→None）"""
    return None if pd.isna(v) else round(float(v), 3)


# ---------------------------------------------------------------- 图1: 近90天五品类趋势
def chart_90d(series_map: dict, ref) -> Line:
    start = ref - timedelta(days=89)
    xidx = pd.date_range(start, ref)
    line = Line(init_opts=opts.InitOpts(**INIT))
    line.add_xaxis([d.strftime("%m-%d") for d in xidx])
    for (name, s), color in zip(series_map.items(), PALETTE):
        line.add_yaxis(name, [fl(v) for v in s.reindex(xidx)],
                       is_symbol_show=False,
                       linestyle_opts=opts.LineStyleOpts(width=2),
                       itemstyle_opts=opts.ItemStyleOpts(color=color),
                       label_opts=opts.LabelOpts(is_show=False))
    line.set_global_opts(
        title_opts=opts.TitleOpts(title="图1 · 近90天 五品类批发均价趋势",
                             subtitle=f"数据截至 {ref:%Y-%m-%d} · 北京新发地 · 单位以各品名实际标注为准"),
        tooltip_opts=opts.TooltipOpts(trigger="axis", axis_pointer_type="cross"),
        xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=45, interval=7)),
        yaxis_opts=opts.AxisOpts(name="均价(元/斤)"),
    )
    return line


# ---------------------------------------------------------------- 图2: 单品类近3年走势
def chart_3y(s: pd.Series, ref, name: str, unit: str) -> Line:
    s = s[s.index >= ref - timedelta(days=3 * 365)]
    line = Line(init_opts=opts.InitOpts(**INIT))
    line.add_xaxis([d.strftime("%Y-%m-%d") for d in s.index])
    line.add_yaxis(f"{name}日度均价", [fl(v) for v in s.values],
                   is_symbol_show=False,
                   linestyle_opts=opts.LineStyleOpts(width=1.6, color="#5470c6"),
                   itemstyle_opts=opts.ItemStyleOpts(color="#5470c6"),
                   label_opts=opts.LabelOpts(is_show=False))
    line.set_global_opts(
        title_opts=opts.TitleOpts(title=f"图2 · {name} 近3年日度均价走势",
                             subtitle=f"元/{unit} · 拖动下方滑块可缩放时间窗口"),
        tooltip_opts=opts.TooltipOpts(trigger="axis"),
        yaxis_opts=opts.AxisOpts(name=f"元/{unit}", is_scale=True),
        datazoom_opts=[opts.DataZoomOpts(type_="slider", range_start=0, range_end=100),
                       opts.DataZoomOpts(type_="inside")],
    )
    return line


# ---------------------------------------------------------------- 图3: 环比涨跌条形图
def chart_mom(series_map: dict) -> Bar:
    cats, vals = [], []
    for name, s in series_map.items():
        if len(s) < 2 or float(s.iloc[-2]) == 0:
            continue
        d1, v1 = s.index[-1], float(s.iloc[-1])
        d0, v0 = s.index[-2], float(s.iloc[-2])
        cats.append(f"{name}\n{d1:%m-%d} vs {d0:%m-%d}")
        vals.append(round((v1 - v0) / v0 * 100, 2))
    bar = Bar(init_opts=opts.InitOpts(**INIT))
    bar.add_xaxis(cats)
    bar.add_yaxis("日环比", vals,
                  itemstyle_opts=opts.ItemStyleOpts(color=JsCode(
                      "function(p){return p.value>=0?'#d94e41':'#3aa372'}")),   # 红涨绿跌
                  label_opts=opts.LabelOpts(is_show=True, formatter="{c}%"))
    bar.set_global_opts(
        title_opts=opts.TitleOpts(title="图3 · 五品类最新日环比涨跌幅",
                             subtitle="最新交易日均价相对前一交易日的变化率（红=涨, 绿=跌）"),
        yaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(formatter="{value}%")),
    )
    return bar


# ---------------------------------------------------------------- 图4: ARIMA 预测
def arima_analyze(s: pd.Series, horizon: int = 7):
    """近两年日度均价: 重采样为连续日序列(缺测日线性插值) → 前80%训练/后20%测试
    → 小网格按 AIC 选一个 ARIMA → 返回(阶数, 测试集MAPE, 连续序列, 测试预测, 未来预测)"""
    from statsmodels.tsa.arima.model import ARIMA
    idx = pd.date_range(s.index[0], s.index[-1], freq="D")
    y = s.reindex(idx).interpolate(limit_direction="both")
    n = len(y)
    n_tr = int(n * 0.8)
    train, test = y.iloc[:n_tr].to_numpy(), y.iloc[n_tr:].to_numpy()

    best_order, best_aic, best_fit = None, np.inf, None
    for order in [(1, 1, 1), (2, 1, 1), (1, 1, 2), (2, 1, 2), (3, 1, 2)]:
        try:
            m = ARIMA(train, order=order).fit()
            if m.aic < best_aic:
                best_order, best_aic, best_fit = order, m.aic, m
        except Exception as exc:
            print(f"  ARIMA{order} 拟合失败: {exc}")
    if best_fit is None:
        raise RuntimeError("所有候选 ARIMA 阶数均拟合失败")

    pred_test = np.asarray(best_fit.forecast(steps=len(test)))
    mape = float(np.mean(np.abs((test - pred_test) / test)) * 100)

    final = ARIMA(y.to_numpy(), order=best_order).fit()      # 用全量重估同一阶数
    fc = np.asarray(final.forecast(steps=horizon))
    return best_order, mape, idx, y, pred_test, fc


def chart_arima(s: pd.Series, ref, name: str, unit: str):
    sub = s[s.index >= ref - timedelta(days=729)]            # 近两年
    order, mape, idx, y, pred_test, fc = arima_analyze(sub)
    future = pd.date_range(idx[-1] + timedelta(days=1), periods=len(fc))
    xs = [d.strftime("%Y-%m-%d") for d in list(idx) + list(future)]
    n = len(idx)

    line = Line(init_opts=opts.InitOpts(width="1150px", height="460px"))
    line.add_xaxis(xs)
    line.add_yaxis("实际日均价", [fl(v) for v in y.values],
                   is_symbol_show=False,
                   linestyle_opts=opts.LineStyleOpts(width=1.6, color="#5470c6"),
                   itemstyle_opts=opts.ItemStyleOpts(color="#5470c6"),
                   label_opts=opts.LabelOpts(is_show=False))
    line.add_yaxis("测试集预测(后20%)",
                   [None] * (n - len(pred_test)) + [fl(v) for v in pred_test],
                   is_symbol_show=False,
                   linestyle_opts=opts.LineStyleOpts(type_="dashed", width=1.5, opacity=0.55, color="#9f9f9f"),
                   itemstyle_opts=opts.ItemStyleOpts(color="#9f9f9f"),
                   label_opts=opts.LabelOpts(is_show=False))
    # 未来7天: 从最后一个实测点起笔, 便于视觉衔接
    line.add_yaxis(f"未来{len(fc)}天预测(ARIMA{order})",
                   [None] * (n - 1) + [fl(y.values[-1])] + [fl(v) for v in fc],
                   is_symbol_show=True, symbol_size=7,
                   linestyle_opts=opts.LineStyleOpts(type_="dashed", width=2.5, color="#d94e41"),
                   itemstyle_opts=opts.ItemStyleOpts(color="#d94e41"),
                   label_opts=opts.LabelOpts(is_show=True, position="top", formatter="{c}"))
    line.set_global_opts(
        title_opts=opts.TitleOpts(
            title=f"图4 · {name}近两年均价 · ARIMA未来{len(fc)}天预测（虚线）",
            subtitle=(f"训练/测试 = 前80%/后20% · 选中模型 ARIMA{order} · "
                      f"测试集 MAPE = {mape:.2f}% · 单位: 元/{unit} · "
                      "★ 预测结果仅供参考, 不构成任何买卖建议")),
        tooltip_opts=opts.TooltipOpts(trigger="axis"),
        yaxis_opts=opts.AxisOpts(name=f"元/{unit}", is_scale=True),
    )
    return line, order, mape


# ---------------------------------------------------------------- 主流程
def main() -> int:
    print(f"数据库后端: {DB_BACKEND}")
    df = load_df()
    if df.empty:
        print("库中无数据! 请先运行: python python/collector/xinfadi.py collect")
        return 1
    ref = df["pub_date"].max()
    print(f"读取 {len(df)} 条价格记录, 最新日期 {ref:%Y-%m-%d}")

    series_map = {}
    for term in CATEGORIES:
        name, how = representative(df, term)
        if not name:
            print(f"  [警告] {term}: 库中无匹配品名, 图表将缺少该品类")
            continue
        s = daily_avg(df, name)
        series_map[name] = s
        print(f"  {term} -> {name}({how}): {len(s)} 个交易日, "
              f"{s.index[0]:%Y-%m-%d} ~ {s.index[-1]:%Y-%m-%d}, 单位 元/{unit_of(df, name)}")

    if not series_map:
        print("没有任何可用品类序列, 退出")
        return 1

    main_cat = "大白菜" if "大白菜" in series_map else next(iter(series_map))

    page = Page(page_title="菜价雷达 · 里程碑0可行性验证Demo", layout=Page.SimplePageLayout)
    page.add(
        chart_90d(series_map, ref),
        chart_3y(series_map[main_cat], ref, main_cat, unit_of(df, main_cat)),
        chart_mom(series_map),
    )
    c4, order, mape = chart_arima(series_map[main_cat], ref, main_cat, unit_of(df, main_cat))
    page.add(c4)
    page.render(str(OUT_HTML))
    if inline_echarts(OUT_HTML):
        print("已内联 echarts 库 → 单文件, 无网络也可双击打开")

    print(f"\n已生成演示页: {OUT_HTML}")
    print(f"ARIMA 预览: 品类={main_cat}, 模型=ARIMA{order}, 测试集MAPE={mape:.2f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
