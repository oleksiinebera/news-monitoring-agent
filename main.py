import streamlit as st
import datetime
import os
import asyncio
import concurrent.futures
import smtplib
from email.message import EmailMessage

# Third-party libraries
from dotenv import load_dotenv # For local development.env file
from telegram import Bot, Update
from telegram.error import TelegramError, NetworkError, BadRequest, TimedOut, Unauthorized, ChatMigrated, RetryAfter
from fpdf import FPDF # Or from fpdf import FPDF as FPDF2 if using fpdf2
from docx import Document

# Local imports (assuming parser.py exists)
from parser import parse_all

# --- Configuration & Initialization ---
load_dotenv() # Load environment variables from.env file if it exists

# Securely load Telegram Token
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = None # Initialize bot as None

if not TELEGRAM_BOT_TOKEN:
    st.error("❗ Critical Error: Telegram Bot Token (TELEGRAM_BOT_TOKEN) is not configured.")
    # Optionally disable Telegram features or stop
    # st.stop()
else:
    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
    except Exception as e:
        st.error(f"❗ Failed to initialize Telegram Bot: {e}")
        bot = None # Ensure bot is None if initialization fails

# --- Streamlit UI ---
st.set_page_config(page_title="News Monitoring Agent", layout="wide")
st.title("📰 News Monitoring Agent")

# --- Helper Functions ---
def generate_pdf_report(results, filename="report.pdf"):
    """Generates a PDF report from news results."""
    pdf = FPDF()
    pdf.add_page()
    # Ensure DejaVuSans.ttf is in the script's directory or font/ subdirectory
    try:
        # Add font - Ensure the TTF file is accessible
        pdf.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
        pdf.set_font("DejaVu", size=12)
    except RuntimeError as e:
        st.error(f"❗ PDF Error: Could not load font 'DejaVuSans.ttf'. Ensure the file exists. Error: {e}")
        # Fallback to standard font (limited character support)
        pdf.set_font("Helvetica", size=12) # Or handle error differently
        st.warning("⚠️ PDF using standard font due to error. Unicode characters may not display correctly.")

    pdf.cell(200, 10, txt="News Report", ln=True, align='C')
    pdf.ln(5)
    for res in results:
        # Ensure data is string and handle potential None values
        title = str(res.get('title', 'N/A'))
        date_str = str(res.get('date', 'N/A'))
        summary = str(res.get('summary', 'N/A'))
        url = str(res.get('url', 'N/A'))

        pdf.set_font("DejaVu", 'B', size=11) # Use loaded font for title
        pdf.multi_cell(0, 6, f"{date_str} — {title}")
        pdf.set_font("DejaVu", size=10) # Use loaded font for summary/URL
        pdf.multi_cell(0, 5, summary)
        pdf.set_font("DejaVu", 'I', size=9)
        pdf.multi_cell(0, 5, f"URL: {url}")
        pdf.ln(3) # Add spacing between entries
    try:
        pdf.output(filename)
        return True
    except Exception as e:
        st.error(f"❗ Failed to save PDF report: {e}")
        return False

def generate_docx_report(results, filename="report.docx"):
    """Generates a DOCX report from news results."""
    try:
        doc = Document()
        doc.add_heading("News Report", level=0)
        for res in results:
            # Ensure data is string and handle potential None values
            title = str(res.get('title', 'N/A'))
            date_str = str(res.get('date', 'N/A'))
            summary = str(res.get('summary', 'N/A'))
            url = str(res.get('url', 'N/A'))

            doc.add_heading(title, level=2)
            doc.add_paragraph(f"Date: {date_str}")
            doc.add_paragraph(summary)
            doc.add_paragraph(f"URL: {url}")
            doc.add_paragraph() # Add spacing
        doc.save(filename)
        return True
    except Exception as e:
        st.error(f"❗ Failed to save DOCX report: {e}")
        return False

async def send_to_telegram(chat_id_to_send, pdf_path="report.pdf", docx_path="report.docx"):
    """Asynchronously sends reports to Telegram with specific error handling."""
    if not bot:
        st.error("❗ Telegram bot is not initialized. Cannot send message.")
        # Log this error server-side as well
        print("Error: Attempted to send Telegram message but bot is not initialized.")
        return
    if not chat_id_to_send:
        st.error("❗ Ошибка: Telegram Chat ID не указан.")
        # Log this error server-side
        print("Error: Attempted to send Telegram message but chat_id is missing.")
        return

    try:
        await bot.send_message(chat_id=chat_id_to_send, text="🗞 Ваш отчёт по новостям готов! 📄")
        sent_files_count = 0

        # Send PDF using context manager
        if os.path.exists(pdf_path):
            try:
                with open(pdf_path, "rb") as pdf_file:
                    await bot.send_document(chat_id=chat_id_to_send, document=pdf_file, filename=os.path.basename(pdf_path))
                sent_files_count += 1
            except FileNotFoundError:
                 st.warning(f"❗ Файл PDF '{pdf_path}' не найден во время отправки.")
            except Exception as e:
                 st.error(f"❗ Ошибка при отправке PDF: {e}")
        else:
            st.info(f"ℹ️ Файл отчёта PDF не найден ({pdf_path}), пропуск отправки.")

        # Send DOCX using context manager
        if os.path.exists(docx_path):
            try:
                with open(docx_path, "rb") as docx_file:
                    await bot.send_document(chat_id=chat_id_to_send, document=docx_file, filename=os.path.basename(docx_path))
                sent_files_count += 1
            except FileNotFoundError:
                 st.warning(f"❗ Файл DOCX '{docx_path}' не найден во время отправки.")
            except Exception as e:
                 st.error(f"❗ Ошибка при отправке DOCX: {e}")
        else:
            st.info(f"ℹ️ Файл отчёта DOCX не найден ({docx_path}), пропуск отправки.")

        if sent_files_count > 0:
            # Use st.toast for less intrusive success message after background task
            # This requires careful state management if you want the toast in the UI later.
            # For simplicity, we log success here. The UI showed "Sending..." initially.
            print(f"✅ Отчёты успешно отправлены в Telegram чат {chat_id_to_send}")
            # Consider logging success to a file or monitoring system instead of just printing.
        else:
            print(f"ℹ️ Файлы отчетов не найдены, в Telegram ничего не отправлено для чата {chat_id_to_send}.")
            await bot.send_message(chat_id=chat_id_to_send, text="ℹ️ Файлы отчетов не были найдены или созданы.")


    # Specific Telegram Error Handling
    except Unauthorized:
        st.error("❗ Ошибка авторизации Telegram: Неверный токен бота.")
        print("Error: Telegram Unauthorized - Check Bot Token.")
    except BadRequest as e:
        st.error(f"❗ Ошибка запроса Telegram: {e}. Проверьте Chat ID или доступ бота к чату.")
        print(f"Error: Telegram BadRequest - {e}")
    except ChatMigrated as e:
        st.warning(f"❗ Чат Telegram перемещен. Новый ID: {e.new_chat_id}. Обновите ID.")
        print(f"Warning: Telegram ChatMigrated to {e.new_chat_id}")
    except TimedOut:
        st.error("❗ Ошибка Telegram: Превышено время ожидания ответа.")
        print("Error: Telegram TimedOut.")
    except NetworkError as e:
        st.error(f"❗ Сетевая ошибка Telegram: {e}. Проверьте подключение.")
        print(f"Error: Telegram NetworkError - {e}")
    except RetryAfter as e:
        st.warning(f"❗ Telegram требует подождать {e.retry_after} сек. (слишком много запросов).")
        print(f"Warning: Telegram RetryAfter {e.retry_after} seconds.")
    except TelegramError as e:
        st.error(f"❗ Общая ошибка Telegram: {e}")
        print(f"Error: TelegramError - {e}")
    except Exception as e:
        st.error(f"❗ Непредвиденная ошибка при отправке в Telegram: {e}")
        print(f"Error: Unexpected error during Telegram send - {e}")


# --- Streamlit Form and Logic ---
with st.form("search_form"):
    keyword = st.text_input("🔍 Ключевые слова для поиска", "Україна")
    start_date = st.date_input("📅 Начальная дата", datetime.date.today() - datetime.timedelta(days=1))
    end_date = st.date_input("📅 Конечная дата", datetime.date.today())
    email_to = st.text_input("📧 Email для отправки отчёта (опционально)", "")
    # Recommended: Get Chat ID via input or stored configuration
    telegram_chat_id = st.text_input("🆔 Ваш Telegram Chat ID (для отчёта, если используется Telegram)", "")

    submitted = st.form_submit_button("🚀 Запустить мониторинг и создать отчёт")

if submitted:
    if start_date > end_date:
        st.error("❗ Ошибка: Начальная дата не может быть позже конечной даты.")
    else:
        st.info(f"⏳ Запущен поиск новостей по запросу: '{keyword}' за период с {start_date} по {end_date}...")

        try:
            # Perform parsing
            results = parse_all(keyword, start_date, end_date) # Assuming parse_all accepts dates

            if not results:
                st.warning("⚠️ Новости по вашему запросу не найдены.")
            else:
                st.success(f"✅ Найдено новостей: {len(results)}")
                st.write("---")
                st.write("### Предпросмотр найденных новостей:")
                # Display results preview (limit for performance)
                for i, res in enumerate(results[:5]): # Show first 5
                     st.markdown(f"**{res.get('title', 'N/A')}** — {res.get('date', 'N/A')}")
                     st.markdown(f"> {res.get('summary', 'N/A')}")
                     st.markdown(f"[Читать далее]({res.get('url', '#')})")
                     st.markdown("---")
                if len(results) > 5:
                    st.markdown(f"*... и еще {len(results) - 5} новостей в полном отчете.*")

                # Generate reports
                pdf_generated = generate_pdf_report(results, "report.pdf")
                docx_generated = generate_docx_report(results, "report.docx")

                if pdf_generated or docx_generated:
                    st.success("✅ Отчёты PDF и/или DOCX успешно созданы.")

                    # Provide download links
                    if pdf_generated and os.path.exists("report.pdf"):
                         with open("report.pdf", "rb") as pdf_file:
                              st.download_button(label="📥 Скачать PDF отчёт", data=pdf_file, file_name="report.pdf", mime="application/pdf")
                    if docx_generated and os.path.exists("report.docx"):
                         with open("report.docx", "rb") as docx_file:
                              st.download_button(label="📥 Скачать DOCX отчёт", data=docx_file, file_name="report.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

                    # Send via Telegram (if configured and enabled)
                    if bot and telegram_chat_id:
                        st.info("⏳ Отправка отчётов через Telegram в фоновом режиме...")
                        # Run the async function in a separate thread to avoid blocking UI
                        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                        # Pass necessary arguments
                        future = executor.submit(asyncio.run, send_to_telegram(telegram_chat_id, "report.pdf", "report.docx"))
                        # Note: UI won't wait for this to finish. Success/Error messages from send_to_telegram
                        # will appear in the console log of the Streamlit server process.
                        # For UI feedback on completion, more complex state management is needed.
                    elif telegram_chat_id and not bot:
                         st.warning("⚠️ Telegram бот не инициализирован, отправка невозможна.")
                    else:
                         st.info("ℹ️ Telegram Chat ID не указан, отправка в Telegram пропущена.")

                    # Send via Email (Optional - Add proper error handling)
                    if email_to:
                        st.info(f"⏳ Отправка отчётов на Email: {email_to}...")
                        # Add email sending logic here (ensure it's robust)
                        # Example (requires configuration):
                        # send_email_report(email_to, ["report.pdf", "report.docx"])
                        st.success(f"✅ Отчёты отправлены на Email: {email_to} (требуется реализация функции отправки).")

                else:
                    st.error("❗ Не удалось создать файлы отчётов.")

        except Exception as e:
            st.error(f"❗ Произошла ошибка во время поиска или генерации отчёта: {e}")
            # Log the full traceback for debugging
            import traceback
            print(f"Error during processing: {traceback.format_exc()}")
