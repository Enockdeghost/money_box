# MoneyBox - Personal Finance Manager

MoneyBox is a powerful, production-ready personal finance web application built with Flask. It helps you track your income and expenses, create budgets, set savings goals, manage bills, and analyze your financial habits—all in one place.

## Features

- **User Authentication**: Registration, login, email verification, password reset, two-factor authentication (2FA), and passcode lock.
- **Wallet Management**: Create multiple wallets (cash, bank, credit cards, etc.), track balances, transfer money between wallets, and share wallets with others.
- **Transaction Tracking**: Add income and expenses with categories, notes, receipts, tags, and location. Quick-add and recurring transactions supported.
- **Categories**: Predefined categories with icons and colors; create custom categories and subcategories.
- **Budgets**: Set monthly/weekly budgets per category, track progress, and receive alerts.
- **Savings Goals**: Define savings targets, track contributions, and mark goals as completed.
- **Bills & Subscriptions**: Manage recurring bills with due dates and reminders.
- **Debts & Loans**: Track money you owe (debts) and money owed to you (loans) with repayment schedules.
- **Reports & Analytics**: Interactive charts (income vs expense, category breakdown, net worth trend), export data to CSV/Excel/PDF.
- **Multi-Currency Support**: (Optional) Exchange rate integration.
- **Data Sync & Backup**: Manual and automatic backups, import/export data (CSV, Excel, JSON).
- **Security**: Encrypted data, session management, device tracking, fraud alerts (basic).
- **Responsive UI**: Works on desktop, tablet, and mobile devices.

## Tech Stack

- **Backend**: Python 3.9+, Flask, Flask-SQLAlchemy, Flask-Migrate, Flask-Login, Flask-WTF, Flask-Mail
- **Database**: SQLite (development), PostgreSQL (production recommended)
- **Frontend**: HTML5, Tailwind CSS, Alpine.js, Chart.js, Font Awesome
- **Task Queue**: Celery + Redis (for background tasks like recurring transactions, email reminders)
- **Additional Libraries**: `itsdangerous` (tokens), `pyotp` (2FA), `qrcode`, `cryptography`, `pandas`, `openpyxl` (exports)

---

## Installation

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- Git
- (Optional) Redis for background tasks

#