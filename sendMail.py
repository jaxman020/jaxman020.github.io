import smtplib
import autoRank
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os
import datetime


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
        with open("log.txt", "a") as f:
            f.write(f"No file found at {datetime.datetime.now()}\n")
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
        with open("log.txt", "a") as f:
            f.write(f"Email sent successfully at {datetime.datetime.now()}\n")
    except Exception as e:
        with open("log.txt", "a") as f:
            f.write(f"Failed to send email at {datetime.datetime.now()}\n {e}\n")


def do_rank():
    with open("log.txt", "w") as f:
        f.write(f"Script executed at {datetime.datetime.now()}\n")

    filePath = autoRank.main()

    with open("log.txt", "a") as f:
        f.write(f"{filePath} created at {datetime.datetime.now()}\n")

    send_email(filePath)

    with open("log.txt", "a") as f:
        f.write(f"do_rank done at {datetime.datetime.now()}\n")


if __name__ == "__main__":
    do_rank()
