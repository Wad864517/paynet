"""
Day11 - 定时舆情分析系统
每天收盘后（15:30）自动运行并发送报告到邮箱
"""
import schedule
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from datetime import datetime

import news_sentiment as ns


def send_email(report_content, subject=None):
    email_config = {
        'smtp_server': 'smtp.qq.com',
        'smtp_port': 587,
        'sender_email': '289081426@qq.com',
        'sender_password': '',
        'receiver_email': '289081426@qq.com',
    }

    if not email_config['sender_email'] or not email_config['receiver_email']:
        print("⚠️ 邮箱配置未完成，跳过邮件发送")
        return False

    if subject is None:
        subject = f"📰 财经舆情分析报告 - {datetime.now().strftime('%Y-%m-%d')}"

    msg = MIMEMultipart('alternative')
    msg['From'] = Header(email_config['sender_email'], 'utf-8')
    msg['To'] = Header(email_config['receiver_email'], 'utf-8')
    msg['Subject'] = Header(subject, 'utf-8')

    text_content = report_content
    html_content = report_content.replace('\n', '<br>').replace('### ', '<h3>').replace('## ', '<h2>').replace('# ', '<h1>').replace('- ', '<li>').replace('**', '<strong>')

    msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
    msg.attach(MIMEText(html_content, 'html', 'utf-8'))

    try:
        server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'])
        server.starttls()
        server.login(email_config['sender_email'], email_config['sender_password'])
        server.sendmail(email_config['sender_email'], email_config['receiver_email'], msg.as_string())
        server.quit()
        print(f"✅ 邮件已发送到: {email_config['receiver_email']}")
        return True
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        return False


def run_daily_task():
    print(f"\n{'='*50}")
    print(f"⏰ 定时任务启动 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}\n")

    try:
        news = ns.get_financial_news(30)
        print(f"获取到 {len(news)} 条新闻")

        if news:
            result = ns.ai_analyze_sentiment(news)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            filename = f'news_sentiment_{timestamp}.md'

            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"# 财经舆情分析报告\n")
                f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
                f.write(f"新闻数量: {len(news)} 条\n\n")
                f.write(result)

            print(f"\n✅ 报告已保存到: {filename}")

            send_email(result)

            print(f"\n{'='*50}")
            print(f"✅ 定时任务完成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*50}\n")

        else:
            print("❌ 未获取到新闻数据")

    except Exception as e:
        print(f"❌ 定时任务执行失败: {e}")


def main():
    print("📰 定时舆情分析系统启动")
    print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"定时任务: 每周一至周五 15:30 运行\n")

    schedule.every().monday.at("15:30").do(run_daily_task)
    schedule.every().tuesday.at("15:30").do(run_daily_task)
    schedule.every().wednesday.at("15:30").do(run_daily_task)
    schedule.every().thursday.at("15:30").do(run_daily_task)
    schedule.every().friday.at("15:30").do(run_daily_task)

    print("按 Ctrl+C 停止定时任务...")
    print("------------------------\n")

    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        print("\n\n🛑 定时任务已停止")


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--now':
        run_daily_task()
    else:
        main()