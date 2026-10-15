# 股票双均线策略网格参数寻优项目
> 基于 Python + Tushare + Pandas + Matplotlib，实现双均线金叉死叉策略，使用网格搜索批量遍历均线参数进行回测，筛选历史表现最优的均线组合。

⚠️ **风险声明**：本项目仅用于Python数据分析、量化编程学习演示。历史回测存在过拟合问题，回测结果**不能代表未来真实收益**，不构成任何投资建议。

## 技术栈
- Python 3.9+
- tushare：获取A股日线行情数据
- pandas / numpy：数据清洗、指标计算
- matplotlib：可视化绘图
- Git & GitHub：代码版本管理与项目托管

## ✨ 项目功能
1. 自定义股票代码、回测起止日期，自动从Tushare拉取日线数据；本地缓存行情文件，重复运行不再重复请求，节省Tushare积分
2. 网格遍历多组短、长期均线组合，批量自动回测
3. 自动计算评价指标：策略净值、年化收益率、最大回撤、夏普比率、交易次数
4. 输出全部参数的对比表格，保存为`grid_search_result.csv`
5. 可视化绘制：股价、均线、金叉买入标记、死叉卖出标记；同时增加**买入持有基准曲线**，直观对比策略优劣
6. 完善代码保护：输入日期校验、空数据判断、夏普比率除零异常防护

## 📁 项目文件结构
> ✅ 仓库内托管文件（GitHub可见）
- `stock_batch_backtest.py`：主程序，包含数据拉取、网格搜索、策略回测、绘图逻辑
- `.gitignore`：Git忽略规则，不提交缓存数据、图片、虚拟环境

> 📂 本地运行代码后自动生成（不会上传到GitHub）
- `stock_data.csv`：Tushare原始行情缓存文件
- `grid_search_result.csv`：网格寻优，保存每组均线策略评价指标
- `result_plot.png`：回测可视化图表


## 🛠️ 环境安装
```bash
pip install pandas numpy tushare matplotlib