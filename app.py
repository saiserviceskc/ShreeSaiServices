from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import firebase_admin
from firebase_admin import credentials, firestore
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import json
from dotenv import load_dotenv

# ---------- LOAD ENV ----------
load_dotenv()

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# ---------- FLASK ----------
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# ---------- FIREBASE ----------
firebase_service_account = os.getenv("FIREBASE_SERVICE_ACCOUNT")

if firebase_service_account:
    firebase_service_account = json.loads(firebase_service_account)
    cred = credentials.Certificate(firebase_service_account)
else:
    cred = credentials.Certificate("serviceAccountKey.json")

firebase_admin.initialize_app(cred)

db = firestore.client()

# ---------- ADMIN LOGIN ----------
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

# ---------- EMAIL FUNCTIONS ----------

# CUSTOMER EMAIL (ORDER)
def send_customer_email(email, name, product):
    try:
        msg = MIMEMultipart()
        msg["From"] = ADMIN_EMAIL
        msg["To"] = email
        msg["Subject"] = "Order Confirmation - Shree Sai Services"

        body = f"""
Hello {name},

Your order has been placed successfully.

Product: {product}

Thank you,
Shree Sai Services
"""
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(ADMIN_EMAIL, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()

    except Exception as e:
        print("Customer email failed:", e)


# ADMIN EMAIL (ORDER)
def send_admin_email(order):
    try:
        msg = MIMEMultipart()
        msg["From"] = ADMIN_EMAIL
        msg["To"] = ADMIN_EMAIL
        msg["Subject"] = "New Order Received"

        body = f"""
New Order Received

Product: {order['product_name']}
Customer: {order['customer_name']}
Phone: {order['customer_phone']}
Email: {order['customer_email']}
Address: {order['customer_address']}
"""
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(ADMIN_EMAIL, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()

    except Exception as e:
        print("Admin email failed:", e)


# ADMIN EMAIL (BOOKING)
def send_booking_email(data):
    try:
        msg = MIMEMultipart()
        msg["From"] = ADMIN_EMAIL
        msg["To"] = ADMIN_EMAIL
        msg["Subject"] = "New Service Booking"

        body = f"""
New Booking Received

Name: {data['fullname']}
Phone: {data['phone']}
Email: {data['email']}
Service: {data['service']}
Date: {data['date']}
"""
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(ADMIN_EMAIL, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()

        print("Booking email sent")

    except Exception as e:
        print("Booking email failed:", e)


# ================= ROUTES =================

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/services")
def services():
    return render_template("services.html")


# ---------- BOOKING ----------
@app.route("/booking", methods=["GET", "POST"])
def booking():
    if request.method == "POST":

        data = {
            "fullname": request.form["fullname"],
            "phone": request.form["phone"],
            "email": request.form["email"],
            "service": request.form["service"],
            "date": request.form["date"]
        }

        db.collection("bookings").add(data)

        send_booking_email(data)

        return jsonify({
            "status": "success",
            "message": "Your booking has been submitted successfully!"
        })

    return render_template("booking.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


# ---------- SALES ----------
@app.route("/sales")
def sales():
    products = []

    docs = db.collection("products").stream()
    for doc in docs:
        p = doc.to_dict()
        p["id"] = doc.id
        products.append(p)

    return render_template("sales.html", products=products)


# ---------- BUY PRODUCT ----------
@app.route("/buy/<product_id>", methods=["GET", "POST"])
def buy_product(product_id):

    doc = db.collection("products").document(product_id).get()
    product = doc.to_dict() if doc.exists else None

    if request.method == "POST" and product:

        order = {
            "product_id": product_id,
            "product_name": product["name"],
            "price": product["price"],
            "customer_name": request.form["name"],
            "customer_email": request.form["email"],
            "customer_phone": request.form["phone"],
            "customer_address": request.form["address"],
            "status": "Pending"
        }

        db.collection("orders").add(order)

        send_customer_email(
            order["customer_email"],
            order["customer_name"],
            order["product_name"]
        )

        send_admin_email(order)

        flash("Order placed successfully!", "success")
        return redirect(url_for("order_success"))

    return render_template("buy.html", product=product)


@app.route("/order-success")
def order_success():
    return render_template("order_success.html")


# ---------- ADMIN LOGIN ----------
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if (
            request.form["username"] == ADMIN_USERNAME and
            request.form["password"] == ADMIN_PASSWORD
        ):
            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid credentials", "danger")

    return render_template("admin_login.html")


# ---------- ADMIN DASHBOARD ----------
@app.route("/admin/dashboard")
def admin_dashboard():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    bookings = [doc.to_dict() for doc in db.collection("bookings").stream()]
    orders = [doc.to_dict() for doc in db.collection("orders").stream()]

    return render_template(
        "admin_dashboard.html",
        bookings=bookings,
        orders=orders
    )


# ---------- UPDATE ORDER STATUS ----------
@app.route("/admin/order-status/<order_id>", methods=["POST"])
def update_order_status(order_id):

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    db.collection("orders").document(order_id).update({
        "status": "Done"
    })

    return redirect(url_for("admin_dashboard"))


# ---------- ADMIN LOGOUT ----------
@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


# ---------- RUN ----------
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 5000)),
        debug=os.getenv("FLASK_DEBUG") == "1"
    )
