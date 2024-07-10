import smtplib
import os
from email.message import EmailMessage

def send_email(subject, body, to, attachment_path):
    user = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to
    msg.set_content(body)

    # Add attachment
    if attachment_path:
        with open(attachment_path, "rb") as file:
            file_data = file.read()
            file_name = os.path.basename(attachment_path)
        msg.add_attachment(file_data, maintype="application", subtype="octet-stream", filename=file_name)

    # Send email
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(user, password)
        smtp.send_message(msg)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Send email with attachment")
    parser.add_argument("--attachment", type=str, required=True, help="Path to the attachment file")
    args = parser.parse_args()

    send_email(
        subject="Binance Contracts RS",
        body="Please find the attached file with the Binance contracts RS data.",
        to="jaxman020@gmail.com",
        attachment_path=args.attachment
    )
