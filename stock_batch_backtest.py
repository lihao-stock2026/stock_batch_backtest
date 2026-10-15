"""
项目名称：均线策略参数寻优（网格搜索）
功能：遍历不同均线参数组合，自动对比回测效果，找出历史回测最优参数
新增优化点：
1. 自动创建data文件夹存放行情缓存
2. 夏普比率增加除零保护，防止标准差为0时报错
3. 统计交易次数，输出到结果中
4. 绘图增加【买入持有基准】对比曲线，直观判断策略优劣
> 风险提示：历史最优参数存在过拟合风险，不代表未来实盘收益，仅用于学习演示。
"""

import tushare as ts
import pandas as pd
import numpy as np
import os
import warnings
import matplotlib.pyplot as plt
warnings.filterwarnings("ignore")

# 计算单组参数的回测指标（输入已经拉好的行情df，短/长均线周期，输出指标）
def calc_backtest(df_raw, short_window, long_window):
    """
    单组均线策略回测函数
    :param df_raw: 原始行情DataFrame
    :param short_window: 短期均线周期
    :param long_window: 长期均线周期
    :return: 回测指标字典（净值、年化、最大回撤、夏普比率、交易次数）
    """
    df = df_raw.copy()
    # 计算均线
    df["ma_short"] = df["close"].rolling(window=short_window).mean()
    df["ma_long"] = df["close"].rolling(window=long_window).mean()
    df = df.dropna(subset=["ma_short","ma_long"]).reset_index(drop=True)

    # 金叉死叉信号
    df["gold_cross"] = (df["ma_short"] > df["ma_long"]) & (df["ma_short"].shift(1) <= df["ma_long"].shift(1))
    df["dead_cross"] = (df["ma_short"] < df["ma_long"]) & (df["ma_short"].shift(1) >= df["ma_long"].shift(1))

    df["signal"] = 0
    position = 0
    for i in range(len(df)):
        if df.loc[i, "gold_cross"]:
            position = 1
        if df.loc[i, "dead_cross"]:
            position = 0
        df.loc[i, "signal"] = position

    # 统计金叉次数 = 交易开仓次数
    trade_count = int(df["gold_cross"].sum())

    # 计算收益
    df["return"] = df["close"].pct_change()
    df = df.dropna(subset=["return"])
    df["strategy_return"] = df["return"] * df["signal"].shift(1)

    # 净值
    strategy_cum = (1 + df["strategy_return"]).cumprod()
    # 最大回撤
    roll_max = strategy_cum.cummax()
    drawdown = strategy_cum / roll_max - 1
    max_dd = drawdown.min()

    # 年化收益、夏普比率，增加除0保护
    trading_days = len(df)
    total_return = strategy_cum.iloc[-1] - 1
    annual_return = (1 + total_return) ** (252 / trading_days) - 1
    risk_free = 0.02
    daily_excess = df["strategy_return"] - risk_free / 252
    daily_std = df["strategy_return"].std()

    if daily_std == 0:
        sharpe = np.nan
    else:
        sharpe = daily_excess.mean() / daily_std * np.sqrt(252)

    return {
        "short_ma": short_window,
        "long_ma": long_window,
        "strategy_net": round(strategy_cum.iloc[-1], 3),
        "annual_return": f"{annual_return:.2%}",
        "max_drawdown": f"{max_dd:.2%}",
        "sharpe_ratio": round(sharpe, 3) if not np.isnan(sharpe) else sharpe,
        "trade_count": trade_count
    }


if __name__ == "__main__":
    print("="*60)
    print("【均线策略参数寻优工具】")
    print("自动遍历多组均线参数，对比历史回测效果")
    print("="*60)

    # 输入基础信息
    ts_code = input("请输入股票代码（例：600519.SH）：").strip()
    start_date = input("回测开始日期(YYYYMMDD)，回车默认20230101：").strip() or "20230101"
    end_date = input("回测结束日期(YYYYMMDD)，回车默认20241231：").strip() or "20241231"

    # 日期合法性校验
    if not (start_date.isdigit() and len(start_date)==8 and end_date.isdigit() and len(end_date)==8):
        print("❌ 日期格式错误！必须是8位数字，例如：20230101")
        exit()
    if start_date > end_date:
        print("❌ 起始日期不能大于结束日期！")
        exit()

    # 自动创建data文件夹存放缓存数据
    data_dir = "data"
    if not os.path.exists(data_dir):
        os.mkdir(data_dir)
    cache_file = os.path.join(data_dir, f"{ts_code.replace('.','_')}_{start_date}_{end_date}_data.csv")

    if os.path.exists(cache_file):
        print(f"\n读取本地缓存数据：{cache_file}")
        df_raw = pd.read_csv(cache_file, encoding="utf-8-sig").reset_index(drop=True)
    else:
        print("\n从Tushare拉取数据...")
        token = os.getenv("TUSHARE_TOKEN")
        if not token:
            token = input('粘贴你的tushare token：')
        ts.set_token(token)
        pro = ts.pro_api()
        df_raw = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
        df_raw.to_csv(cache_file, index=False, encoding="utf-8-sig")

    df_raw["trade_date"] = pd.to_datetime(df_raw["trade_date"])
    df_raw = df_raw.sort_values("trade_date").reset_index(drop=True)

    # 判断是否获取到行情
    if df_raw.empty:
        print("❌ 没有获取到行情数据，请检查股票代码、上市时间、日期区间！")
        exit()

    # ========== 定义要搜索的参数网格（可自行修改范围）==========
    short_windows = [5, 7, 10, 12]   # 短均线候选
    long_windows = [20, 30, 60]       # 长均线候选
    print(f"\n开始遍历参数组合，共 {len(short_windows)*len(long_windows)} 组...")

    # 遍历所有合法参数组合（短均线必须 < 长均线）
    result_list = []
    for s in short_windows:
        for l in long_windows:
            if s >= l:  # 跳过无效组合
                continue
            try:
                res = calc_backtest(df_raw, s, l)
                result_list.append(res)
                print(f"✅ 完成：MA{s}/MA{l}")
            except Exception as e:
                print(f"⚠️ MA{s}/MA{l} 计算失败：{e}")

    # 判断参数结果列表
    if len(result_list) == 0:
        print("❌ 所有参数组合计算失败，请检查数据量是否太少！")
        exit()

    # 汇总结果，按夏普比率排序
    result_df = pd.DataFrame(result_list).sort_values(by="sharpe_ratio", ascending=False).reset_index(drop=True)

    # 保存参数寻优结果表格
    result_df.to_csv("grid_search_result.csv", index=False, encoding="utf-8-sig")
    print("\n✅ 参数对比结果已保存至 grid_search_result.csv")

    print("\n" + "="*60)
    print(f"{ts_code} 参数寻优结果（按夏普比率从高到低排序）")
    print("="*60)
    print(result_df.to_string(index=False))

    # 输出最优参数
    best = result_df.iloc[0]
    print("\n" + "="*60)
    print(f"🏆 历史回测最优参数：MA{best['short_ma']} / MA{best['long_ma']}")
    print(f"对应指标：净值 {best['strategy_net']} | 年化 {best['annual_return']} | 最大回撤 {best['max_drawdown']} | 夏普 {best['sharpe_ratio']} | 交易次数 {best['trade_count']}")
    print("="*60)
    print("⚠️ 重要提示：该结果仅为历史回测最优，存在过拟合风险，不代表未来实盘表现！")

    # ===== 绘图：画出最优参数对应的行情与买卖信号 + 买入持有基准对比 =====
    best_short = int(best["short_ma"])
    best_long = int(best["long_ma"])
    df_plot = df_raw.copy()
    df_plot["ma_short"] = df_plot["close"].rolling(window=best_short).mean()
    df_plot["ma_long"] = df_plot["close"].rolling(window=best_long).mean()
    df_plot = df_plot.dropna(subset=["ma_short","ma_long"]).reset_index(drop=True)

    df_plot["gold_cross"] = (df_plot["ma_short"] > df_plot["ma_long"]) & (df_plot["ma_short"].shift(1) <= df_plot["ma_long"].shift(1))
    df_plot["dead_cross"] = (df_plot["ma_short"] < df_plot["ma_long"]) & (df_plot["ma_short"].shift(1) >= df_plot["ma_long"].shift(1))

    plt.rcParams["font.sans-serif"] = ["SimHei"]
    plt.rcParams["axes.unicode_minus"] = False

    fig, ax = plt.subplots(figsize=(14,6))
    ax.plot(df_plot["trade_date"], df_plot["close"], label="收盘价")
    ax.plot(df_plot["trade_date"], df_plot["ma_short"], label=f"MA{best_short}")
    ax.plot(df_plot["trade_date"], df_plot["ma_long"], label=f"MA{best_long}")

    # 增加买入持有基准曲线
    benchmark_cum = (1 + df_plot["close"].pct_change()).cumprod()
    ax.plot(df_plot["trade_date"], benchmark_cum, label="买入持有基准净值", linestyle="--")

    buy_points = df_plot[df_plot["gold_cross"]]
    sell_points = df_plot[df_plot["dead_cross"]]
    ax.scatter(buy_points["trade_date"], buy_points["close"], marker="^", c="red", s=80, label="买入")
    ax.scatter(sell_points["trade_date"], sell_points["close"], marker="v", c="green", s=80, label="卖出")

    ax.set_title(f"最优参数 MA{best_short}/{best_long} 行情与交易信号")
    ax.legend()
    ax.grid(alpha=0.3)
    img_name = f"{ts_code.replace('.','_')}_best_param_plot.png"
    plt.tight_layout()
    plt.savefig(img_name, dpi=300)
    plt.show()
    print(f"\n✅ 已生成最优参数图像 {img_name}")