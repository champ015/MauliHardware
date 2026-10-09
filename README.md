# Mauli Hardware - Django + MySQL

## Setup
1. Install MySQL, then: `CREATE DATABASE mauli_hardware CHARACTER SET utf8mb4;`
2. `python -m venv venv && source venv/bin/activate` (Windows: `venv\Scripts\activate`)
3. `pip install -r requirements.txt`  (mysqlclient needs MySQL dev libs; on Windows use a wheel or `pip install pymysql` + `import pymysql; pymysql.install_as_MySQLdb()` in config/__init__.py)
4. Copy `.env.example` to `.env` and fill DB + Razorpay test keys
5. `python manage.py makemigrations store && python manage.py migrate`
6. `python manage.py createsuperuser`
7. `python manage.py runserver` -> site at /, admin at /admin/

## Admin
Categories -> Products (add size/pack variants inline) -> Variants (edit price/stock in list) -> Orders (change status, bulk Mark Shipped/Delivered).

## Razorpay
- Use test keys first. Add webhook URL `https://yourdomain/payment/webhook/` (events: payment.captured, order.paid) and put the secret in RAZORPAY_WEBHOOK_SECRET.
- Payment is verified on the server (signature check) before order becomes PAID. No card data is stored.

## Edit delivery rules in config/settings.py
