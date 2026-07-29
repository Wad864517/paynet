import akshare as ak
import pandas as pd
import time
import random
import logging
import os
from datetime import datetime, timedelta
from data_manager import save_to_csv, get_date_folder

# ===== 日志配置 =====
def setup_logger():
    """配置日志：同时输出到控制台和文件"""
    log_dir = os.path.join("data", datetime.now().strftime("%Y%m%d"))
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"money_tracker_{datetime.now().strftime('%H%M%S')}.log")

    logger = logging.getLogger("money_tracker")
    logger.setLevel(logging.DEBUG)
    logger.handlers = []  # 清除旧handler

    # 文件handler（DEBUG级别，记录所有细节）
    fh = logging.FileHandler(log_file, encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', '%H:%M:%S'))

    # 控制台handler（INFO级别，只显示重要信息）
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter('%(message)s'))

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger, log_file

log, log_file_path = setup_logger()

def fetch_with_retry(func, *args, **kwargs):
    """带智能重试的数据获取，详细记录每次尝试"""
    func_name = func.__name__ if hasattr(func, '__name__') else str(func)
    log.debug(f"开始调用 {func_name}，参数: args={args}, kwargs={kwargs}")

    for attempt in range(5):
        try:
            log.debug(f"[{func_name}] 第{attempt+1}次尝试...")
            start_time = time.time()
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time

            if result is None:
                raise ValueError("返回数据为None")
            if hasattr(result, 'empty') and result.empty:
                raise ValueError("返回数据为空DataFrame")

            log.debug(f"[{func_name}] 成功！耗时{elapsed:.2f}s，数据量={len(result)}行")
            return result

        except Exception as e:
            if attempt < 4:
                delay = 2 * (1.5 ** attempt) + random.uniform(0, 1)
                log.warning(f"[{func_name}] 第{attempt+1}次失败({e})，{delay:.1f}秒后重试...")
                time.sleep(delay)
            else:
                log.error(f"[{func_name}] 5次重试全部失败，最后错误: {e}")
                raise

def track_north_flow():
    """追踪北向资金（外资）动向"""
    log.info("\n" + "="*50)
    log.info("📊 北向资金追踪（外资动向）")
    log.info("="*50)

    try:
        log.debug("步骤1: 获取北向资金当日汇总数据...")
        north_summary = fetch_with_retry(ak.stock_hsgt_fund_flow_summary_em)
        log.debug(f"汇总数据列名: {north_summary.columns.tolist()}")
        log.debug(f"汇总数据:\n{north_summary.to_string()}")

        north_sh = north_summary[north_summary['板块'] == '沪股通']
        north_sz = north_summary[north_summary['板块'] == '深股通']

        sh_net = north_sh.iloc[0]['成交净买额'] if not north_sh.empty else 0
        sz_net = north_sz.iloc[0]['成交净买额'] if not north_sz.empty else 0
        total_net = sh_net + sz_net

        trade_date = north_summary.iloc[0]['交易日'] if not north_summary.empty else 'N/A'
        log.info(f"\n📅 当日北向资金数据 ({trade_date}):")
        log.info(f"  📈 沪股通净买入: {sh_net:+.2f} 亿")
        log.info(f"  📈 深股通净买入: {sz_net:+.2f} 亿")
        log.info(f"  📊 北向资金合计: {total_net:+.2f} 亿")

        if total_net > 50:
            log.info("  🟢 北向资金大幅流入，外资态度积极")
        elif total_net > 0:
            log.info("  🟡 北向资金小幅流入，外资态度中性偏多")
        elif total_net > -50:
            log.info("  🟡 北向资金小幅流出，外资态度中性偏空")
        else:
            log.info("  🔴 北向资金大幅流出，注意风险")

        log.debug("保存北向资金汇总数据到CSV...")
        save_to_csv(north_summary, "north_flow_summary.csv")

        log.debug("步骤2: 获取北向资金历史数据...")
        north_hist = fetch_with_retry(ak.stock_hsgt_hist_em, symbol="北向资金")
        valid_hist = north_hist[north_hist['当日成交净买额'].notna()]
        log.debug(f"历史数据共{len(north_hist)}行，有效数据{len(valid_hist)}行")

        recent = valid_hist.tail(10)
        if not recent.empty:
            log.info(f"\n📅 历史北向资金数据（近10个有数据交易日）:")
            for _, row in recent.iterrows():
                val = row['当日成交净买额']
                emoji = "📈" if val > 0 else "📉"
                log.info(f"  {str(row['日期'])}  {emoji} {val:+.2f} 亿")

            # 统计分析
            total_5d = recent['当日成交净买额'].tail(5).sum()
            total_10d = recent['当日成交净买额'].sum()
            log.debug(f"近5日合计: {total_5d:+.2f}亿，近10日合计: {total_10d:+.2f}亿")

        log.debug("保存北向资金历史数据到CSV...")
        save_to_csv(north_hist, "north_flow_hist.csv")

    except Exception as e:
        log.error(f"❌ 北向资金数据获取失败: {e}", exc_info=True)

def track_sector_flow():
    """追踪板块资金流向"""
    log.info("\n" + "="*50)
    log.info("📊 板块资金流向（今日资金去哪了）")
    log.info("="*50)

    try:
        log.debug("获取行业板块资金流向数据...")
        sector = fetch_with_retry(
            ak.stock_sector_fund_flow_rank,
            indicator="今日",
            sector_type="行业资金流"
        )
        log.debug(f"板块数据列名: {sector.columns.tolist()}")
        log.debug(f"共{len(sector)}个行业板块")

        # 流入TOP10
        log.info("\n🟢 今日资金流入TOP10行业:")
        for i, row in sector.head(10).iterrows():
            name = row.get('名称', row.iloc[1] if len(row) > 1 else 'N/A')
            net = row.get('今日净流入', row.iloc[2] if len(row) > 2 else 0)
            log.info(f"  {i+1}. {name}: {net}")

        # 流出TOP5
        log.info("\n🔴 今日资金流出TOP5行业:")
        for i, row in sector.tail(5).iterrows():
            name = row.get('名称', row.iloc[1] if len(row) > 1 else 'N/A')
            net = row.get('今日净流入', row.iloc[2] if len(row) > 2 else 0)
            log.info(f"  {name}: {net}")

        log.debug("保存板块资金流向数据到CSV...")
        save_to_csv(sector, "sector_flow.csv")

    except Exception as e:
        log.error(f"❌ 板块资金流向获取失败: {e}", exc_info=True)

def track_lhb():
    """追踪龙虎榜数据"""
    log.info("\n" + "="*50)
    log.info("📊 龙虎榜数据（机构+游资动向）")
    log.info("="*50)

    try:
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")
        log.debug(f"查询龙虎榜数据: {start_date} ~ {end_date}")

        lhb = fetch_with_retry(
            ak.stock_lhb_jgmmtj_em,
            start_date=start_date,
            end_date=end_date
        )
        log.debug(f"龙虎榜数据列名: {lhb.columns.tolist()}")
        log.debug(f"共{len(lhb)}条龙虎榜记录")

        if len(lhb) > 0:
            log.info(f"\n近一周机构龙虎榜数据（共{len(lhb)}条）:")

            # 显示前15条
            for i, (_, row) in enumerate(lhb.head(15).iterrows(), 1):
                code = row.get('代码', '')
                name = row.get('名称', '')
                net = row.get('机构买入净额', 0)
                reason = row.get('上榜原因', '')
                date = row.get('上榜日期', '')
                log.info(f"  {i}. [{date}] {code} {name} | 机构净买入: {net:>15,.0f} | {reason}")

            # 机构重点关注
            log.info(f"\n🏦 机构重点关注个股:")
            if '机构买入净额' in lhb.columns:
                top = lhb.nlargest(5, '机构买入净额')
                log.debug("机构净买入TOP5:")
                for _, row in top.iterrows():
                    code = row.get('代码', '')
                    name = row.get('名称', '')
                    net = row.get('机构买入净额', 0)
                    log.info(f"  {code} {name}: 机构净买入 {net:,.0f}")
                    log.debug(f"    详细: 买入总额={row.get('机构买入总额', 0):,.0f}, 卖出总额={row.get('机构卖出总额', 0):,.0f}")

            log.debug("保存龙虎榜数据到CSV...")
            save_to_csv(lhb, "lhb_data.csv")
        else:
            log.warning("近一周无龙虎榜数据（可能接口维护中）")

    except Exception as e:
        log.error(f"❌ 龙虎榜数据获取失败: {e}", exc_info=True)

def print_summary():
    """输出运行汇总"""
    log.info("\n" + "="*50)
    log.info("📋 资金追踪汇总")
    log.info("="*50)
    log.info(f"  📁 数据目录: {get_date_folder()}")
    log.info(f"  📝 日志文件: {log_file_path}")
    log.info(f"  🕐 完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    log.info(f"🕐 运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info(f"📁 数据保存目录: {get_date_folder()}")
    log.debug("="*50)
    log.debug("开始大资金追踪...")
    log.debug("="*50)

    track_north_flow()
    track_sector_flow()
    track_lhb()

    print_summary()
    log.info(f"\n✅ 资金追踪完成！")
