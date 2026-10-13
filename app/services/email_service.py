import os
import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr

from dotenv import load_dotenv


load_dotenv()


SMTP_HOST = os.getenv(
    "SMTP_HOST",
    "smtp.gmail.com"
)

SMTP_PORT = int(
    os.getenv(
        "SMTP_PORT",
        "587"
    )
)

SMTP_USERNAME = os.getenv(
    "SMTP_USERNAME"
)

SMTP_PASSWORD = os.getenv(
    "SMTP_PASSWORD"
)

EMAIL_FROM = os.getenv(
    "EMAIL_FROM",
    SMTP_USERNAME
)

# نام نمایشی فرستنده
EMAIL_FROM_DISPLAY = formataddr(
    (
        str(Header("اپلیکیشن رصد", "utf-8")),
        EMAIL_FROM
    )
)


# ==========================================
# Verification Email
# ==========================================

def send_verification_email(
    recipient_email: str,
    verification_token: str
) -> None:

    # لینک HTTP قابل کلیک در Gmail؛ این مسیر کاربر را به اپ اندروید هدایت می‌کند.
    from urllib.parse import quote

    encoded_token = quote(verification_token, safe="")
    verification_url = (
        "http://remote-respina-free.runflare.com:31496"
        "/api/auth/open-verification-app"
        f"?token={encoded_token}"
    )

    message = MIMEMultipart(
        "alternative"
    )

    message["Subject"] = (
        "تأیید ایمیل حساب رصد"
    )

    message["From"] = EMAIL_FROM_DISPLAY
    message["To"] = recipient_email

    text_content = f"""
سلام،

برای تأیید ایمیل حساب رصد روی لینک زیر کلیک کنید:

{verification_url}

این لینک تا ۳۰ دقیقه معتبر است.

اگر شما این حساب را ایجاد نکرده‌اید، این ایمیل را نادیده بگیرید.

اپلیکیشن رصد
"""

    html_content = f"""
<!DOCTYPE html>
<html lang="fa" dir="rtl">

<head>
    <meta charset="UTF-8">
    <title>تأیید ایمیل - رصد</title>
</head>

<body style="
    font-family: Arial, sans-serif;
    background: #f5f7fb;
    padding: 40px;
">

<div style="
    max-width: 600px;
    margin: auto;
    background: white;
    padding: 30px;
    border-radius: 15px;
">

    <h2 style="
        text-align: center;
        color: #ff7a18;
    ">
        تأیید ایمیل
    </h2>

    <p>سلام،</p>

    <p>
        برای فعال‌سازی حساب خود در
        <strong>اپلیکیشن رصد</strong>
        روی دکمه زیر کلیک کنید:
    </p>

    <div style="
        text-align: center;
        margin: 30px 0;
    ">

        <a href="{verification_url}"
           style="
           background: #ff7a18;
           color: white;
           padding: 14px 25px;
           border-radius: 8px;
           text-decoration: none;
           display: inline-block;
           ">

            تأیید ایمیل

        </a>

    </div>

    <p>
        این لینک تا ۳۰ دقیقه معتبر است.
    </p>

    <p>
        اگر شما این حساب را ایجاد نکرده‌اید،
        این ایمیل را نادیده بگیرید.
    </p>

    <p>
        اپلیکیشن رصد
    </p>

</div>

</body>
</html>
"""

    message.attach(
        MIMEText(
            text_content,
            "plain",
            "utf-8"
        )
    )

    message.attach(
        MIMEText(
            html_content,
            "html",
            "utf-8"
        )
    )

    # ======================================
    # SMTP - Gmail / STARTTLS
    # ======================================

    with smtplib.SMTP(
        SMTP_HOST,
        SMTP_PORT,
        timeout=10
    ) as server:

        server.ehlo()

        server.starttls()

        server.ehlo()

        server.login(
            SMTP_USERNAME,
            SMTP_PASSWORD
        )

        server.sendmail(
            EMAIL_FROM,
            recipient_email,
            message.as_string()
        )


# ==========================================
# Password Reset Email
# ==========================================

def send_password_reset_email(
    recipient_email: str,
    reset_token: str
) -> None:

    frontend_url = os.getenv(
        "FRONTEND_URL",
        "http://localhost:5173"
    )

    reset_url = (
        f"{frontend_url}/reset-password"
        f"?token={reset_token}"
    )

    message = MIMEMultipart(
        "alternative"
    )

    message["Subject"] = (
        "بازیابی رمز عبور حساب رصد"
    )

    message["From"] = EMAIL_FROM_DISPLAY
    message["To"] = recipient_email

    text_content = f"""
سلام،

برای تغییر رمز عبور حساب رصد روی لینک زیر کلیک کنید:

{reset_url}

این لینک تا ۳۰ دقیقه معتبر است.

اگر شما درخواست بازیابی رمز عبور نداده‌اید،
این ایمیل را نادیده بگیرید.

اپلیکیشن رصد
"""

    html_content = f"""
<!DOCTYPE html>
<html lang="fa" dir="rtl">

<head>
    <meta charset="UTF-8">
    <title>بازیابی رمز عبور - رصد</title>
</head>

<body style="
    font-family: Arial, sans-serif;
    background: #f5f7fb;
    padding: 40px;
">

<div style="
    max-width: 600px;
    margin: auto;
    background: white;
    padding: 30px;
    border-radius: 15px;
">

    <h2 style="
        text-align: center;
        color: #ff7a18;
    ">
        بازیابی رمز عبور
    </h2>

    <p>سلام،</p>

    <p>
        برای تغییر رمز عبور حساب خود در
        <strong>اپلیکیشن رصد</strong>
        روی دکمه زیر کلیک کنید:
    </p>

    <div style="
        text-align: center;
        margin: 30px 0;
    ">

        <a href="{reset_url}"
           style="
           background: #ff7a18;
           color: white;
           padding: 14px 25px;
           border-radius: 8px;
           text-decoration: none;
           display: inline-block;
           ">

            تغییر رمز عبور

        </a>

    </div>

    <p>
        این لینک تا ۳۰ دقیقه معتبر است.
    </p>

    <p>
        اگر شما درخواست بازیابی رمز عبور نداده‌اید،
        این ایمیل را نادیده بگیرید.
    </p>

    <p>
        اپلیکیشن رصد
    </p>

</div>

</body>
</html>
"""

    message.attach(
        MIMEText(
            text_content,
            "plain",
            "utf-8"
        )
    )

    message.attach(
        MIMEText(
            html_content,
            "html",
            "utf-8"
        )
    )

    # ======================================
    # SMTP - Gmail / STARTTLS
    # ======================================

    with smtplib.SMTP(
        SMTP_HOST,
        SMTP_PORT,
        timeout=10
    ) as server:

        server.ehlo()

        server.starttls()

        server.ehlo()

        server.login(
            SMTP_USERNAME,
            SMTP_PASSWORD
        )

        server.sendmail(
            EMAIL_FROM,
            recipient_email,
            message.as_string()
        )