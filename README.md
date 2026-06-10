# Fast Food Delivery API

A production-ready food delivery REST API built with Python and FastAPI, inspired by Uber Eats.
This API powers a complete food delivery platform supporting two roles — restaurant owners and clients — with real-time order tracking, 
Stripe payment processing, and automated email and SMS notifications.

---

## Architecture Highlights

* FastAPI REST API
* PostgreSQL Database
* SQLAlchemy ORM
* Alembic Database Migrations
* JWT Authentication
* Stripe Checkout + Webhooks
* Cloudinary Media Storage
* Resend Email Notifications
* Twilio SMS Notifications
* WebSocket Real-Time Tracking

---

## Tech Stack

| Category         | Technology                    |
| ---------------- | ----------------------------- |
| Language         | Python 3.14                   |
| Framework        | FastAPI                       |
| Database         | PostgreSQL                    |
| ORM              | SQLAlchemy                    |
| Migrations       | Alembic                       |
| Authentication   | JWT (Access + Refresh Tokens) |
| Payments         | Stripe                        |
| Email            | Resend                        |
| SMS              | Twilio                        |
| Image Storage    | Cloudinary                    |
| Real-time        | WebSockets                    |
| Password Hashing | pwdlib (Argon2)               |

---

## Features

### Authentication & Security

* JWT authentication with short-lived access tokens (60 min) and long-lived refresh tokens (30 days)
* Email and phone number verification required before accessing the platform
* Role-based access control — Owner and Client roles with separate permissions
* Account lockout after 3 consecutive failed login attempts (30 minute lockout)
* Password strength validation (uppercase, lowercase, number, special character required)
* Internal BigInteger IDs never exposed — UUID public IDs used in all API responses
* Stripe webhook signature verification — payment status never trusted from client

### Users & Profiles

* User registration with automatic login — no separate login step required
* Profile management — update name, email, phone number, profile picture
* Secure password change with automatic logout from all devices
* Forgot password flow with time-limited reset links (15 minutes)
* Rate limited password reset — maximum 3 attempts per 24 hours

### Restaurants

* Owners can create and manage their own restaurant
* Restaurant image upload via Cloudinary
* Open/closed status toggle
* Clients can browse all open restaurants with average ratings and total review counts
* Average rating calculated dynamically from the ratings table

### Foods

* Owners can manage their full menu — create, update, patch, and delete food items
* Food image upload via Cloudinary
* Availability toggle for sold out or seasonal items
* Clients can browse the full menu of any restaurant
* Only available food items shown to clients

### Orders

* Clients can only have one active pending order at a time
* Only one restaurant per order — enforced at API level
* Total price calculated entirely on the backend — clients never send price data
* Order cancellation allowed only before payment is completed
* Reorder feature — clients can reorder from previous orders with fresh price calculation
* Order history showing last 15 orders with full item details
* Owners can update order status through the delivery pipeline

### Payments

* Stripe Checkout Session integration — clients redirected to hosted Stripe payment page
* Webhook signature verification on every webhook event
* Order status automatically updated to confirmed after successful payment
* Payment status tracked independently — pending, completed, failed, refunded
* Clients cannot pay for the same order twice

### Real-Time Delivery Tracking

* WebSocket connection for live delivery tracking per order
* Driver broadcasts GPS coordinates in real time
* Coordinates instantly pushed to all connected clients tracking that order
* Automatic order status notifications pushed via WebSocket when owner updates status

### Email Notifications (Resend)

* Email verification on registration
* Welcome email after full account verification
* Password reset link
* Password changed security alert
* Order confirmation after payment
* Out for delivery notification
* Order delivered confirmation

### SMS Notifications (Twilio)

* Phone number verification code on registration
* Order confirmation SMS
* Order status update SMS for every status change
* Order delivered SMS

### Ratings

* Clients can only rate a restaurant after receiving a delivered order from them
* One rating per restaurant per client — no duplicate ratings
* Ratings can be updated but not duplicated
* Reviews are optional text alongside the numeric rating
* Ratings scale from 0.5 to 5.0

### Addresses

* Clients can save multiple delivery addresses
* One default address at a time
* Full address management — create, update, patch, delete
* Address ownership verified on every order — clients cannot use another user's address

---

## Database Design

The API uses **10 tables** with proper foreign key relationships:

| Table                 | Purpose                                                               |
| --------------------- | --------------------------------------------------------------------- |
| `users`               | Stores both owners and clients with role differentiation              |
| `addresses`           | Client delivery addresses with default address support                |
| `restaurants`         | Owner restaurant profiles with ratings relationship                   |
| `foods`               | Restaurant menu items with availability tracking                      |
| `orders`              | Client orders linking user, restaurant, and address                   |
| `order_items`         | Individual food items within an order with price snapshot             |
| `ratings`             | Restaurant ratings by verified clients                                |
| `payments`            | Stripe payment records linked to orders                               |
| `refresh_tokens`      | JWT refresh tokens for persistent sessions                            |
| `verification_tokens` | Tokens for email verification, phone verification, and password reset |

---

## Project Structure

```text
app/
├── main.py
├── config.py
├── database.py
├── models.py
├── schemas.py
├── enumz.py
│
├── routers/
│   ├── auth.py
│   ├── users.py
│   ├── verification.py
│   ├── profile.py
│   ├── restaurants.py
│   ├── foods.py
│   ├── orders.py
│   ├── ratings.py
│   ├── addresses.py
│   ├── payments.py
│   └── tracking.py
│
├── utils/
│   ├── hashing.py
│   ├── oauth2.py
│   ├── email.py
│   ├── sms.py
│   └── cloudinary.py
│
alembic/
└── versions/
```

---

## Environment Variables

Create a `.env` file in the root directory based on `.env.example`:

```env
# Database
DATABASE_HOSTNAME=localhost
DATABASE_PORT=5432
DATABASE_NAME=your_db_name
DATABASE_USERNAME=your_db_username
DATABASE_PASSWORD=your_db_password

# JWT
SECRET_KEY=your_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30

# Resend
RESEND_API_KEY=your_resend_api_key
RESEND_FROM_EMAIL=onboarding@resend.dev

# Twilio
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=your_twilio_number

# Stripe
STRIPE_SECRET_KEY=your_stripe_secret_key
STRIPE_PUBLISHABLE_KEY=your_stripe_publishable_key
STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret

# Cloudinary
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_cloudinary_api_key
CLOUDINARY_API_SECRET=your_cloudinary_api_secret

# App
BASE_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000
ENVIRONMENT=development

# Security
MAX_RESET_ATTEMPTS=3
RESET_ATTEMPT_WINDOW_HOURS=24
RESET_TOKEN_EXPIRE_MINUTES=15
```

---

## Installation & Setup

### 1. Clone the repository

```bash
git clone https://github.com/KhonaniBackendDev/fast-food-delivery-api.git
cd fast-food-delivery-api
```

### 2. Create and activate virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Create `.env`

Fill in all required environment variables.

### 5. Run database migrations

```bash
alembic upgrade head
```

### 6. Run the application

```bash
uvicorn app.main:app --reload
```

### 7. Open API Documentation

```text
http://localhost:8000/docs
```

---



## Production Features

* Role-Based Access Control (RBAC)
* UUID Public IDs
* JWT Access & Refresh Tokens
* Account Lockout Protection
* Password Reset Rate Limiting
* Stripe Webhook Verification
* Cloudinary Media Storage
* Email & SMS Notifications
* WebSocket Real-Time Tracking
* Alembic Database Migrations

---

## API Endpoints

### Authentication
| Method | Endpoint | Description | Access |
|---|---|---|---|
| POST | `/users/register` | Register new user | Public |
| POST | `/auth/login` | Login | Public |
| POST | `/auth/logout` | Logout | Authenticated |

### Verification
| Method | Endpoint | Description | Access |
|---|---|---|---|
| POST | `/verify-phone` | Verify phone number with SMS code | Authenticated |
| GET | `/verify-email` | Verify email address via link | Public |
| POST | `/resend-phone-code` | Resend SMS verification code | Authenticated |
| POST | `/resend-verification-email` | Resend verification email | Authenticated |
| POST | `/forgot-password` | Request password reset email | Public |
| POST | `/reset-password` | Reset password with token | Public |

### Profile
| Method | Endpoint | Description | Access |
|---|---|---|---|
| GET | `/profile/me` | Get my profile | Verified |
| PUT | `/profile/me` | Update my profile | Verified |
| PATCH | `/profile/me` | Patch my profile | Verified |
| POST | `/profile/me/change-password` | Change password | Verified |
| POST | `/profile/me/image` | Upload profile image | Verified |

### Restaurants
| Method | Endpoint | Description | Access |
|---|---|---|---|
| POST | `/restaurants` | Create restaurant | Owner |
| GET | `/restaurants/me` | Get my restaurant | Owner |
| PUT | `/restaurants/me` | Update my restaurant | Owner |
| PATCH | `/restaurants/me` | Patch my restaurant | Owner |
| DELETE | `/restaurants/me` | Delete my restaurant | Owner |
| POST | `/restaurants/me/image` | Upload restaurant image | Owner |
| GET | `/restaurants` | Get all open restaurants with ratings | Client |
| GET | `/restaurants/{public_id}` | Get one restaurant | Client |

### Foods
| Method | Endpoint | Description | Access |
|---|---|---|---|
| POST | `/foods` | Create food item | Owner |
| GET | `/foods/me` | Get my restaurant foods | Owner |
| PUT | `/foods/{food_public_id}` | Update food item | Owner |
| PATCH | `/foods/{food_public_id}` | Patch food item | Owner |
| DELETE | `/foods/{food_public_id}` | Delete food item | Owner |
| POST | `/foods/{food_public_id}/image` | Upload food image | Owner |
| GET | `/foods/{restaurant_public_id}` | Get all foods from a restaurant | Client |
| GET | `/foods/{restaurant_public_id}/{food_public_id}` | Get one food item | Client |

### Orders
| Method | Endpoint | Description | Access |
|---|---|---|---|
| POST | `/orders` | Create order | Client |
| GET | `/orders/me` | Get my recent orders | Client |
| GET | `/orders/me/{order_public_id}` | Get one order | Client |
| PATCH | `/orders/me/{order_public_id}/cancel` | Cancel pending order | Client |
| POST | `/orders/reorder/{order_public_id}` | Reorder from history | Client |
| GET | `/orders/restaurant` | Get all incoming orders | Owner |
| PATCH | `/orders/{order_public_id}/status` | Update order status | Owner |

### Ratings
| Method | Endpoint | Description | Access |
|---|---|---|---|
| POST | `/ratings` | Rate a restaurant | Client |
| GET | `/ratings/{restaurant_public_id}` | Get restaurant ratings | Verified |
| PATCH | `/ratings/{rating_public_id}` | Update your rating | Client |
| DELETE | `/ratings/{rating_public_id}` | Delete your rating | Client |

### Addresses
| Method | Endpoint | Description | Access |
|---|---|---|---|
| POST | `/addresses` | Create delivery address | Client |
| GET | `/addresses` | Get all my addresses | Client |
| GET | `/addresses/{address_public_id}` | Get one address | Client |
| PUT | `/addresses/{address_public_id}` | Update address | Client |
| PATCH | `/addresses/{address_public_id}` | Patch address | Client |
| PATCH | `/addresses/{address_public_id}/set-default` | Set default address | Client |
| DELETE | `/addresses/{address_public_id}` | Delete address | Client |

### Payments
| Method | Endpoint | Description | Access |
|---|---|---|---|
| POST | `/payments/checkout/{order_public_id}` | Create Stripe checkout session | Client |
| POST | `/payments/webhook` | Stripe webhook handler | Stripe |
| GET | `/payments/success` | Payment success confirmation | Public |
| GET | `/payments/cancel` | Payment cancelled confirmation | Public |

### Real-time Tracking
| Method | Endpoint | Description | Access |
|---|---|---|---|
| WS | `/tracking/track/{order_public_id}/{token}` | Track order in real time | Client |
| WS | `/tracking/driver/{order_public_id}/{token}` | Send driver location | Authenticated |
| POST | `/tracking/notify/{order_public_id}` | Push status notification | Internal |

---

## Security Highlights

* Passwords hashed using **Argon2** via pwdlib
* JWT tokens signed with **HS256**
* Internal BigInteger IDs never exposed
* Stripe webhook signature verification on every event
* Account lockout after 3 failed login attempts
* Password reset rate limiting
* Delivery address ownership verification
* Role-based access control enforced on every endpoint

---

## Testing the API

Swagger Documentation:

```text
http://localhost:8000/docs
```

Stripe CLI:

```bash
stripe listen --forward-to localhost:8000/payments/webhook
```

Test Card:

```text
4242 4242 4242 4242
```

Any future expiry date and any CVC.


---

## Author

Built by **[KhonaniBackendDev]**


---

## License

MIT License
