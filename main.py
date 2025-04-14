# Расширенный новостной агент с интерфейсом, парсингом Telegram и фильтрами

import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import os
import smtplib, ssl
from email.message import EmailMessage
from fpdf import FPDF
from docx import Document
from telegram import Bot
import logging
import streamlit as st
from telethon.sync import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest

# === НАСТРОЙКИ ===
KEYWORDS = ["безпека", "вибух", "обстріл"]
DATE_FROM = datetime.now() - timedelta(days=1)
DATE_TO = datetime.now()
NEWS_SOURCES = ["https://www.pravda.com.ua/rss/"]
TELEGRAM_API_ID = 123456  # Заменить
TELEGRAM_API_HASH = 'your_api_hash'
TELEGRAM_CHANNELS = ["https://t.me/uniannet"]
TELEGRAM_CHAT_ID = "@your_channel"
TELEGRAM_TOKEN = "your_bot_token"
EMAIL_TO = "user@example.com"
EMAIL_FROM = "youremail@gmail.com"
EMAIL_PASS = "your_app_password"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465

results = []

# === ФУНКЦИИ ===

def parse_news_sources():
    for url in NEWS_SOURCES:
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.content, features="xml")
            for item in soup.find_all('item'):
                title = item.title.text
                link = item.link.text
                pub_date = item.pubDate.text if item.pubDate else ''
                date = pd.to_datetime(pub_date, errors='coerce')
                description = item.description.text if item.description else ''
                content = f"{title} {description}".lower()
                if DATE_FROM <= date <= DATE_TO and any(kw.lower() in content for kw in KEYWORDS):
                    results.append({
                        'title': title,
                        'link': link,
                        'description': description,
                        'date': date.strftime('%Y-%m-%d'),
                        'source': url
                    })
        except Exception as e:
            logging.error(f"Ошибка парсинга {url}: {e}")

# Парсинг Telegram

def parse_telegram():
    with TelegramClient('session_name', TELEGRAM_API_ID, TELEGRAM_API_HASH) as client:
        for channel in TELEGRAM_CHANNELS:
            try:
                entity = client.get_entity(channel)
                history = client(GetHistoryRequest(peer=entity, limit=100, offset_date=None,
                                                   offset_id=0, max_id=0, min_id=0, add_offset=0, hash=0))
                for message in history.messages:
                    if message.message:
                        text = message.message.lower()
                        msg_date = message.date
                        if DATE_FROM <= msg_date <= DATE_TO and any(kw in text for kw in KEYWORDS):
                            results.append({
                                'title': message.message[:100],
                                'description': message.message,
                                'link': channel,
                                'date': msg_date.strftime('%Y-%m-%d'),
                                'source': channel
                            })
            except Exception as e:
                logging.warning(f"Ошибка Telegram {channel}: {e}")

# Отправка Email

def send_email_report(pdf_path):
    msg = EmailMessage()
    msg['Subject'] = 'Звіт по новинам'
    msg['From'] = EMAIL_FROM
    msg['To'] = EMAIL_TO
    msg.set_content('У додатку - новини за обраний період.')

    with open(pdf_path, 'rb') as f:
        msg.add_attachment(f.read(), maintype='application', subtype='pdf', filename=os.path.basename(pdf_path))

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
        server.login(EMAIL_FROM, EMAIL_PASS)
        server.send_message(msg)

# Telegram отправка

def send_telegram_summary(results):
    bot = Bot(token=TELEGRAM_TOKEN)
    summary = "\n\n".join([f"📰 <b>{r['title']}</b>\n{r['link']}" for r in results])
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=summary, parse_mode='HTML')

# PDF

def export_pdf(results, filename='news_report.pdf'):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for r in results:
        pdf.multi_cell(0, 10, f"{r['date']}\n{r['title']}\n{r['description']}\n{r['link']}\n---")
    pdf.output(filename)

# DOCX

def export_word(results, filename='news_report.docx'):
    doc = Document()
    doc.add_heading("Звіт новин", 0)
    for r in results:
        doc.add_paragraph(f"{r['date']}\n{r['title']}\n{r['description']}\n{r['link']}")
        doc.add_paragraph("---")
    doc.save(filename)

# === Streamlit UI ===

def launch_dashboard():
    st.title("Новинний Агент")
    st.write("Задайте ключові слова, період, джерела і отримайте звіт")

    global KEYWORDS, DATE_FROM, DATE_TO
    kws = st.text_input("Ключові слова (через кому):", ", ".join(KEYWORDS))
    KEYWORDS = [k.strip().lower() for k in kws.split(',') if k.strip()]
    DATE_FROM = st.date_input("Дата з:", DATE_FROM).strftime('%Y-%m-%d')
    DATE_TO = st.date_input("Дата по:", DATE_TO).strftime('%Y-%m-%d')

    if st.button("🔍 Пошук новин"):
        results.clear()
        parse_news_sources()
        parse_telegram()

        if results:
            df = pd.DataFrame(results)
            df = df.sort_values(by="date", ascending=False)
            st.success(f"Знайдено новин: {len(df)}")
            st.dataframe(df)

            if st.button("💾 Завантажити PDF та Word"):
                export_pdf(results)
                export_word(results)
                st.success("Файли створено: news_report.pdf, news_report.docx")

            if st.button("📩 Надіслати Email та Telegram"):
                send_email_report("news_report.pdf")
                send_telegram_summary(results)
                st.success("Звіт відправлено!")
        else:
            st.warning("Новин не знайдено")

# === Запуск ===
if __name__ == '__main__':
    launch_dashboard()
