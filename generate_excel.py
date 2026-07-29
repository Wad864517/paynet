import pandas as pd
import numpy as np
from datetime import datetime

def generate_analysis_excel(stocks):
    """将股票分析结果生成Excel表格"""
    results = []
    
    for code in stocks:
        csv_file = f"analysis_{code}.csv"
        try:
            df = pd.read_csv(csv_file)
            
            if len(df) == 0:
                continue
                
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            signals = []
            
            if prev['MA5'] <= prev['MA20'] and latest['MA5'] > latest['MA20']:
                signals.append("MA5金叉")
            elif prev['MA5'] >= prev['MA20'] and latest['MA5'] < latest['MA20']:
                signals.append("MA5死叉")
                
            if prev['DIF'] <= prev['DEA'] and latest['DIF'] > latest['DEA']:
                signals.append("MACD金叉")
            elif prev['DIF'] >= prev['DEA'] and latest['DIF'] < latest['DEA']:
                signals.append("MACD死叉")
                
            if latest['J'] < 20:
                signals.append(f"KDJ超卖(J={latest['J']:.1f})")
            elif latest['J'] > 80:
                signals.append(f"KDJ超买(J={latest['J']:.1f})")
                
            if latest['RSI'] < 30:
                signals.append(f"RSI超卖({latest['RSI']:.1f})")
            elif latest['RSI'] > 70:
                signals.append(f"RSI超买({latest['RSI']:.1f})")
                
            if latest['量比'] > 2 and latest['收盘'] > latest['MA20']:
                signals.append(f"放量突破(量比={latest['量比']:.1f})")
                
            if latest['MA5'] > latest['MA10'] > latest['MA20'] > latest['MA60']:
                signals.append("多头排列")
            elif latest['MA5'] < latest['MA10'] < latest['MA20'] < latest['MA60']:
                signals.append("空头排列")
                
            buy_count = sum(1 for s in signals if "金叉" in s or "突破" in s or "多头" in s)
            sell_count = sum(1 for s in signals if "死叉" in s or "空头" in s)
            watch_count = sum(1 for s in signals if "超卖" in s or "超买" in s)
            
            if buy_count >= 2 and sell_count == 0:
                suggestion = "偏多，可以考虑建仓"
            elif sell_count >= 2 and buy_count == 0:
                suggestion = "偏空，建议回避或减仓"
            else:
                suggestion = "信号混合，建议观望或轻仓试探"
                
            results.append({
                '股票代码': code,
                '最新交易日': latest['日期'],
                '收盘价': round(latest['收盘'], 2),
                '涨跌幅(%)': round(latest['涨跌幅'], 2),
                '成交量': int(latest['成交量']),
                '量比': round(latest['量比'], 2),
                'MA5': round(latest['MA5'], 2),
                'MA10': round(latest['MA10'], 2),
                'MA20': round(latest['MA20'], 2),
                'MA60': round(latest['MA60'], 2),
                'DIF': round(latest['DIF'], 3),
                'DEA': round(latest['DEA'], 3),
                'MACD': round(latest['MACD'], 3),
                'K': round(latest['K'], 1),
                'D': round(latest['D'], 1),
                'J': round(latest['J'], 1),
                'RSI': round(latest['RSI'], 1),
                '信号列表': '; '.join(signals) if signals else '无',
                '买入信号数': buy_count,
                '卖出信号数': sell_count,
                '观望信号数': watch_count,
                '操作建议': suggestion
            })
            
        except FileNotFoundError:
            print(f"⚠️ 未找到文件: {csv_file}")
        except Exception as e:
            print(f"❌ 处理 {code} 失败: {e}")
    
    if not results:
        print("❌ 没有找到任何分析数据")
        return
    
    result_df = pd.DataFrame(results)
    
    excel_file = f"stock_analysis_{datetime.now().strftime('%Y%m%d')}.xlsx"
    
    with pd.ExcelWriter(excel_file, engine='xlsxwriter') as writer:
        result_df.to_excel(writer, index=False, sheet_name='股票分析报告')
        
        workbook = writer.book
        worksheet = writer.sheets['股票分析报告']
        
        header_fill = workbook.add_format({'bg_color': '#4472C4', 'font_color': 'white', 'bold': True})
        buy_fill = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'})
        sell_fill = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
        watch_fill = workbook.add_format({'bg_color': '#FFEB9C', 'font_color': '#9C6500'})
        
        for col_num, value in enumerate(result_df.columns.values):
            worksheet.write(0, col_num, value, header_fill)
        
        for row_num in range(len(result_df)):
            suggestion = result_df.iloc[row_num]['操作建议']
            col_num = result_df.columns.get_loc('操作建议')
            if '偏多' in suggestion:
                worksheet.write(row_num + 1, col_num, suggestion, buy_fill)
            elif '偏空' in suggestion:
                worksheet.write(row_num + 1, col_num, suggestion, sell_fill)
            else:
                worksheet.write(row_num + 1, col_num, suggestion, watch_fill)
        
        for col_num, col_name in enumerate(result_df.columns):
            max_len = max(result_df[col_name].astype(str).apply(len).max(), len(str(col_name)))
            worksheet.set_column(col_num, col_num, min(max_len + 2, 20))
    
    print(f"\n✅ Excel报告已生成: {excel_file}")
    print(f"   共分析 {len(results)} 只股票")
    
    return result_df

if __name__ == "__main__":
    stocks = ["600519", "300750", "002594"]
    df = generate_analysis_excel(stocks)
    
    print("\n📊 分析结果预览:")
    print(df[['股票代码', '收盘价', '涨跌幅(%)', '信号列表', '操作建议']].to_string(index=False))