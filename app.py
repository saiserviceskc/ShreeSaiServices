from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
BREVO_API_KEY = os.getenv("BREVO_API_KEY")

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

firebase_service_account = os.getenv("FIREBASE_SERVICE_ACCOUNT")

if firebase_service_account:
    cred = credentials.Certificate(json.loads(firebase_service_account))
else:
    cred = credentials.Certificate("serviceAccountKey.json")

firebase_admin.initialize_app(cred)
db = firestore.client()

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


def send_email(to_email, subject, html_content):
    try:
        if not BREVO_API_KEY:
            print("Email failed: BREVO_API_KEY missing")
            return

        payload = {
            "sender": {
                "name": "Shree Sai Services",
                "email": ADMIN_EMAIL
            },
            "to": [{"email": to_email}],
            "subject": subject,
            "htmlContent": html_content
        }

        headers = {
            "accept": "application/json",
            "api-key": BREVO_API_KEY,
            "content-type": "application/json"
        }

        response = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            json=payload,
            headers=headers,
            timeout=20
        )
        response.raise_for_status()
        print("Email sent:", subject)

    except Exception as e:
        print("Email failed:", e)


def send_customer_email(email, name, product):
    send_email(
        email,
        "Order Confirmation - Shree Sai Services",
        f"""
        <h2>Order Confirmation</h2>
        <p>Hello {name},</p>
        <p>Your order has been placed successfully.</p>
        <p><strong>Product:</strong> {product}</p>
        <p>Thank you,<br>Shree Sai Services</p>
        """
    )


def send_admin_email(order):
    send_email(
        ADMIN_EMAIL,
        "New Order Received",
        f"""
        <h2>New Order Received</h2>
        <p><strong>Product:</strong> {order['product_name']}</p>
        <p><strong>Customer:</strong> {order['customer_name']}</p>
        <p><strong>Phone:</strong> {order['customer_phone']}</p>
        <p><strong>Email:</strong> {order['customer_email']}</p>
        <p><strong>Address:</strong> {order['customer_address']}</p>
        """
    )


def send_booking_email(data):
    send_email(
        ADMIN_EMAIL,
        "New Service Booking",
        f"""
        <h2>New Booking Received</h2>
        <p><strong>Name:</strong> {data['fullname']}</p>
        <p><strong>Phone:</strong> {data['phone']}</p>
        <p><strong>Email:</strong> {data['email']}</p>
        <p><strong>Service:</strong> {data['service']}</p>
        <p><strong>Date:</strong> {data['date']}</p>
        """
    )


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/services")
def services():
    return render_template("services.html")


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


@app.route("/sales")
def sales():
    products = []

    docs = db.collection("products").stream()
    for doc in docs:
        product = doc.to_dict()
        product["id"] = doc.id
        products.append(product)

    return render_template("sales.html", products=products)


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


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if (
            request.form["username"] == ADMIN_USERNAME and
            request.form["password"] == ADMIN_PASSWORD
        ):
            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))

        flash("Invalid credentials", "danger")

    return render_template("admin_login.html")


@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    bookings = []
    for doc in db.collection("bookings").stream():
        booking = doc.to_dict()
        booking["id"] = doc.id
        bookings.append(booking)

    orders = []
    for doc in db.collection("orders").stream():
        order = doc.to_dict()
        order["id"] = doc.id
        orders.append(order)

    return render_template(
        "admin_dashboard.html",
        bookings=bookings,
        orders=orders
    )


@app.route("/admin/order-status/<order_id>", methods=["POST"])
def update_order_status(order_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    db.collection("orders").document(order_id).update({
        "status": "Done"
    })

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 5000)),
        debug=os.getenv("FLASK_DEBUG") == "1"
    )
