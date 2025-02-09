from app import app, db, User, Product
from datetime import datetime

def init_db():
    with app.app_context():
        try:
            db.create_all()
            print("Database created successfully!")
            
            # Create admin user if it doesn't exist
            admin = User.query.filter_by(email='admin@example.com').first()
            if not admin:
                admin = User(
                    email='admin@example.com',
                    password=generate_password_hash('admin123'),
                    is_admin=True
                )
                db.session.add(admin)
                db.session.commit()
                print("Admin user created successfully!")
                
            # Add some sample products if none exist
            if not Product.query.first():
                sample_products = [
                    Product(name='Product 1', description='Description 1', price=19.99, stock=10, image='default.jpg'),
                    Product(name='Product 2', description='Description 2', price=29.99, stock=15, image='default.jpg'),
                    Product(name='Product 3', description='Description 3', price=39.99, stock=20, image='default.jpg')
                ]
                db.session.add_all(sample_products)
                db.session.commit()
                print("Sample products added successfully!")
                
        except Exception as e:
            print(f"Error initializing database: {e}")