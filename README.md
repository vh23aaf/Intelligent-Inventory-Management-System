# Intelligent Inventory Decision-Support Web Application

## Project Overview

An intelligent inventory management system for small-scale e-commerce businesses that combines machine learning-based demand forecasting with classical inventory management logic to provide explainable, data-driven recommendations.

**Core Features:**
- ML-based demand forecasting (Linear Regression & Random Forest)
- Reorder point & quantity recommendations
- Overstock/understock risk detection with explanations
- Decision-support dashboard with visualizations

## Technical Stack

- **Backend**: Django 4.2.8
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **ML**: scikit-learn, pandas, numpy
- **Frontend**: Django Templates + Bootstrap 5

## How to Run

### Prerequisites
- Python 3.8+
- pip

### Setup & Run

1. **Create virtual environment and install dependencies:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Create necessary directories:**
   ```bash
   mkdir -p logs media inventory/static/{css,js}
   ```

3. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

4. **Create superuser:**
   ```bash
   python manage.py createsuperuser
   ```

5. **Start development server:**
   ```bash
   python manage.py runserver
   ```

6. **Access the application:**
   - Dashboard: http://localhost:8000
   - Admin: http://localhost:8000/admin

## Database Models

- **Product** - Inventory items with stock, lead time, pricing
- **SalesRecord** - Daily sales transactions
- **DemandForecast** - ML-generated predictions
- **InventoryAlert** - Risk indicators with explanations
- **ModelEvaluation** - Model performance metrics

## Project Structure

```
├── config/              # Django configuration
├── inventory/           # Main app (models, views, forms, admin)
├── ml_engine/          # ML module (future - forecasters, evaluators)
├── manage.py           # Django CLI
└── requirements.txt    # Dependencies
```

## Development Modules

1. ✅ Module 1: Project Setup & Models (COMPLETE)
2. Module 2: Data Entry & Dashboard
3. Module 3: ML Intelligence Layer
4. Module 4: Risk Detection
5. Module 5: Visualization & Dashboard
6. Module 6: Testing & Documentation