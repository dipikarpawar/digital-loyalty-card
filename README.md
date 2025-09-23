# digital-loyalty-card
Digital Loyalty Card
====================
This project is a backend API that replaces paper punch cards with a digital, QR-based system. Vendors can sign up, register customers, track visits, and view simple analytics about repeat customers.

It’s built with FastAPI and MongoDB Atlas, using QR codes to link customers with vendors.

Features
========

Vendor accounts
---------------
Signup & login with email and password
JWT authentication for secure access
Customer management
Vendors can register their own customers
Each customer is tied to a vendor

Digital punch cards
-------------------
QR codes generated for each vendor
Customers get a “punch” when they scan the vendor’s code

Analytics
---------
Vendors can see how many repeat customers they had in a given week

Tech Stack
----------
Python (FastAPI)
MongoDB Atlas (database)
PyMongo (MongoDB driver)
JWT + Passlib (authentication)
qrcode (QR code generation)
Pandas (analytics/reporting)

Project Structure
-----------------
- main.py         # API endpoints
- database.py     # MongoDB connection
- auth.py         # JWT and password hashing
- utils.py        # QR code + S3 upload helpers
- .env            # Environment variables
