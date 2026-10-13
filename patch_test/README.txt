این patch سه بخش را تکمیل می‌کند:

1) CoinGecko historical backfill:
   - 5m برای حدود 1 روز
   - 1h برای 60 روز
   - ساخت 4h و 1d از 1h ذخیره‌شده
   - بدون ساختگی‌کردن volume
   - فقط وقتی تاریخچه کافی نباشد درخواست می‌فرستد

2) MTF service:
   5m / 15m / 30m / 1h / 4h / 1d

3) endpoint:
   GET /api/analysis/multi/BTC?period=30d

برای اعمال:
   cd backend
   bash /path/to/apply_analysis_patch.sh

یا فایل‌ها را دستی در مسیرهای مشخص کپی کنید.

نکته: اگر backend شما همین حالا در حال اجراست، بعد از patch آن را restart کنید.
