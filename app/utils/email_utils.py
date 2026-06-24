"""Email notification utilities."""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app


def send_email(to_email, subject, html_body):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = current_app.config["SMTP_USER"]
        msg["To"] = to_email
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(current_app.config["SMTP_HOST"], current_app.config["SMTP_PORT"]) as server:
            server.starttls()
            server.login(current_app.config["SMTP_USER"], current_app.config["SMTP_PASSWORD"])
            server.sendmail(current_app.config["SMTP_USER"], to_email, msg.as_string())
        return True
    except Exception:
        return False


def send_verification_email(email, token):
    frontend_url = current_app.config["FRONTEND_URL"]
    link = f"{frontend_url}/verify-email?token={token}"
    html = f"""
    <h2>Bright Future English</h2>
    <p>Please verify your email by clicking the link below:</p>
    <a href="{link}">Verify Email</a>
    """
    return send_email(email, "Verify Your Email - Bright Future English", html)


def send_password_reset_email(email, token):
    frontend_url = current_app.config["FRONTEND_URL"]
    link = f"{frontend_url}/reset-password?token={token}"
    html = f"""
    <h2>Bright Future English</h2>
    <p>Reset your password by clicking the link below:</p>
    <a href="{link}">Reset Password</a>
    """
    return send_email(email, "Reset Password - Bright Future English", html)


def send_notification_email(email, title, message):
    html = f"<h2>{title}</h2><p>{message}</p><p>- Bright Future English</p>"
    return send_email(email, title, html)
