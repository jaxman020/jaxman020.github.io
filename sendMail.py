import smtplib
import autoRank
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os

load_dotenv("autorankbyrs.env")  # 載入 .env 檔案


def send_email(filePath):
    sender = "jaxman020@gmail.com"  # Replace with your email
    recipient = "jaxman020@gmail.com"  # Replace with recipient email
    subject = "Daily Rank from Binance Contracts"

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient

    if filePath:
        with open(filePath, "rb") as file:
            part = MIMEApplication(file.read(), Name=filePath.split("/")[-1])
        part["Content-Disposition"] = (
            f'attachment; filename="{filePath.split("/")[-1]}"'
        )
        msg.attach(part)
    else:
        print("No file found.")
        return

    html_content = """
    <html>
    <body>
        <h1>Daily Rank</h1>
    </body>
    </html>
    """
    content = MIMEText(html_content, "html")
    msg.attach(content)

    app_password = os.environ.get("GMAIL_APP_PASSWORD")

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender, app_password)
            server.sendmail(sender, recipient, msg.as_string())
        print("Email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")


def do_rank():
    filePath = autoRank.main()
    print(filePath)

    send_email(filePath)
    return "do_rank done!"


if __name__ == "__main__":
    do_rank()
