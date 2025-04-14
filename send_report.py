from main import init_db, launch_dashboard, export_pdf, send_pdf_email
import pandas as pd
import sqlite3

# Настройка email
SENDER = "your_email@gmail.com"
PASSWORD = "your_password"
RECIPIENT = "target@example.com"
PDF_PATH = "news_report.pdf"

# Подгружаем данные
conn = sqlite3.connect("news_aggregator.db")
df = pd.read_sql_query("SELECT * FROM news", conn)
conn.close()

# Генерация и отправка
if not df.empty:
    df['date'] = pd.to_datetime(df['date'])
    df['day'] = df['date'].dt.date
    export_pdf(df)
    send_pdf_email(SENDER, PASSWORD, RECIPIENT, "Звіт новин", "У додатку PDF", PDF_PATH)
