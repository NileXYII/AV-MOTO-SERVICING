from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_mail import Mail, Message
from datetime import datetime, timedelta
import os
import random
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your_secret_key_here')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///motorparts.db'
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', 'avmotoservicing@gmail.com')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', 'rozz agwd iosq rwux')

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
mail = Mail(app)

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_staff = db.Column(db.Boolean, default=False)
    address = db.Column(db.String(200))
    contact_number = db.Column(db.String(20))
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    appointments = db.relationship('Appointment', backref='user', lazy=True)
    orders = db.relationship('Order', backref='user', lazy=True)
    activity_logs = db.relationship('ActivityLog', backref='user', lazy=True)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    products = db.relationship('Product', backref='category', lazy=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    brand = db.Column(db.String(50))
    size = db.Column(db.String(50))
    color = db.Column(db.String(50))
    motorcycle_model = db.Column(db.String(100))
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    image = db.Column(db.String(200))
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    cart_items = db.relationship('CartItem', backref='product', lazy=True)

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # Add more statuses like 'approved', 'declined'
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    total_amount = db.Column(db.Float, nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    contact_number = db.Column(db.String(20), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    order_items = db.relationship('OrderItem', backref='order', lazy=True)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    product = db.relationship('Product')

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    motorcycle_model = db.Column(db.String(100), nullable=False)
    contact_number = db.Column(db.String(20), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    service_type = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='pending')
    notes = db.Column(db.Text)
    reference_code = db.Column(db.String(6), unique=True)  

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    duration = db.Column(db.Integer)  # Duration in minutes

class BlogPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(200))
    video_url = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    author = db.relationship('User', backref='blog_posts')

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    details = db.Column(db.Text)

# Helper Functions
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def log_activity(user_id, action, details=None):
    log = ActivityLog(user_id=user_id, action=action, details=details)
    db.session.add(log)
    db.session.commit()

def send_notification(email, subject, body):
    try:
        msg = Message(subject, sender=app.config['MAIL_USERNAME'], recipients=[email])
        msg.body = body
        mail.send(msg)
    except Exception as e:
        app.logger.error(f"Failed to send email: {e}")

def get_sales_statistics():
    today = datetime.utcnow().date()
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)

    daily_sales = db.session.query(func.sum(Order.total_amount)).\
        filter(func.date(Order.date_created) == today).scalar() or 0

    monthly_sales = db.session.query(func.sum(Order.total_amount)).\
        filter(func.date(Order.date_created) >= month_start).scalar() or 0

    yearly_sales = db.session.query(func.sum(Order.total_amount)).\
        filter(func.date(Order.date_created) >= year_start).scalar() or 0

    return {
        'daily': daily_sales,
        'monthly': monthly_sales,
        'yearly': yearly_sales
    }

# Routes
@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/shop')
def shop():
    category_id = request.args.get('category', type=int)
    search = request.args.get('search', '')
    
    query = Product.query
    if category_id:
        query = query.filter_by(category_id=category_id)
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))
    
    products = query.all()
    categories = Category.query.all()
    return render_template('shop.html', products=products, categories=categories)

@app.route('/product/<int:id>')
def product_detail(id):
    product = Product.query.get_or_404(id)
    return render_template('product_detail.html', product=product)

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    quantity = int(request.form.get('quantity', 1))
    product = Product.query.get_or_404(product_id)
    
    if product.stock < quantity:
        flash('Not enough stock available', 'error')
        return redirect(url_for('shop'))
    
    cart_item = CartItem.query.filter_by(
        user_id=current_user.id, 
        product_id=product_id
    ).first()
    
    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = CartItem(user_id=current_user.id, product_id=product_id, quantity=quantity)
        db.session.add(cart_item)
    
    db.session.commit()
    flash('Item added to cart!', 'success')
    return redirect(url_for('shop'))
@app.route('/cart')
@login_required
def cart():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    subtotal = sum(item.product.price * item.quantity for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, subtotal=subtotal)

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    if request.method == 'POST':
        # Debugging: Print the form data to check if 'name' is present
        print(request.form)  # Add this line to debug

        # Get form data
        name = request.form.get('name')  # Use .get() to avoid KeyError
        address = request.form.get('address')
        contact_number = request.form.get('contact_number')
        payment_method = request.form.get('payment_method')

        # Check if any required field is missing
        if not name or not address or not contact_number or not payment_method:
            flash('Please fill out all required fields.', 'error')
            return redirect(url_for('checkout'))

        # Calculate total amount
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        total_amount = sum(item.product.price * item.quantity for item in cart_items)

        # Create a new order
        order = Order(
            user_id=current_user.id,
            total_amount=total_amount,
            customer_name=name,
            address=address,
            contact_number=contact_number,
            payment_method=payment_method
        )
        db.session.add(order)
        db.session.commit()

        # Create order items and update product stock
        for cart_item in cart_items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=cart_item.product_id,
                quantity=cart_item.quantity,
                price=cart_item.product.price
            )
            cart_item.product.stock -= cart_item.quantity
            db.session.add(order_item)

        # Clear the cart
        CartItem.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()

        # Log activity and send notification
        log_activity(current_user.id, f'Placed order #{order.id}')
        send_notification(current_user.email, 'Order Confirmation', 
                         f'Your order #{order.id} has been placed successfully.')

        # Redirect to order confirmation page
        return redirect(url_for('order_confirmation', order_id=order.id))

    # For GET requests, render the checkout form
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    subtotal = sum(item.product.price * item.quantity for item in cart_items)
    return render_template('checkout.html', cart_items=cart_items, subtotal=subtotal)

@app.route('/appointments')
@login_required
def appointments():
    user_appointments = Appointment.query.filter_by(user_id=current_user.id).all()
    services = Service.query.all()
    now = datetime.now()  # Get the current date and time
    return render_template('appointments.html', 
                         appointments=user_appointments,
                         services=services,
                         now=now)  # Pass 'now' to the template

@app.route('/book_appointment', methods=['POST'])
@login_required
def book_appointment():
    try:
        date_str = request.form['date']
        date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')

        if date < datetime.now():
            flash('Cannot book appointments in the past', 'error')
            return redirect(url_for('appointments'))

        # Generate a reference code
        reference_code = generate_reference_code()

        appointment = Appointment(
            user_id=current_user.id,
            customer_name=request.form['name'],
            motorcycle_model=request.form['motorcycle_model'],
            contact_number=request.form['contact_number'],
            date=date,
            service_type=request.form['service_type'],
            reference_code=reference_code  # Add the reference code
        )

        db.session.add(appointment)
        db.session.commit()

        # Send email with the reference code
        send_notification(
            current_user.email,
            'Appointment Confirmation',
            f'Your appointment for {appointment.service_type} on {date} has been scheduled. '
            f'Your reference code is: {reference_code}. Please present this code when visiting the site.'
        )

        flash('Appointment booked successfully!', 'success')
        return redirect(url_for('appointments'))
    except ValueError:
        flash('Invalid date format', 'error')
        return redirect(url_for('appointments'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            log_activity(user.id, 'User logged in')
            flash('Login successful!', 'success')
            return redirect(url_for('shop'))
        flash('Invalid username or password', 'error')
    return render_template('login.html')
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        if User.query.filter_by(username=request.form['username']).first():
            flash('Username already exists', 'error')
            return redirect(url_for('signup'))
        
        if User.query.filter_by(email=request.form['email']).first():
            flash('Email already exists', 'error')
            return redirect(url_for('signup'))
        
        user = User(
            username=request.form['username'],
            email=request.form['email'],
            password=generate_password_hash(request.form['password']),
            address=request.form['address'],
            contact_number=request.form['contact_number']
        )
        db.session.add(user)
        db.session.commit()
        
        log_activity(user.id, 'New user account created')
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    log_activity(current_user.id, 'User logged out')
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('landing'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('shop'))

    # Handle search by reference code
    search_query = request.args.get('search')
    if search_query:
        recent_appointments = Appointment.query.filter(Appointment.reference_code.contains(search_query)).all()
    else:
        recent_appointments = Appointment.query.order_by(Appointment.date.desc()).limit(10).all()

    # Get other data for the dashboard
    pending_appointments = Appointment.query.filter_by(status='pending').all()
    products = Product.query.all()
    low_stock_products = Product.query.filter(Product.stock < 10).all()
    recent_logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(10).all()
    recent_orders = Order.query.order_by(Order.date_created.desc()).limit(10).all()
    sales_stats = get_sales_statistics()

    return render_template('admin_dashboard.html',
                         pending_appointments=pending_appointments,
                         products=products,
                         low_stock_products=low_stock_products,
                         recent_logs=recent_logs,
                         recent_orders=recent_orders,
                         recent_appointments=recent_appointments,
                         sales_stats=sales_stats)

@app.route('/admin/products')
@login_required
def admin_products():
    if not current_user.is_admin and not current_user.is_staff:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('shop'))
    
    products = Product.query.all()
    categories = Category.query.all()
    return render_template('admin/products.html', products=products, categories=categories)

@app.route('/admin/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    if not current_user.is_admin and not current_user.is_staff:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('shop'))
    
    if request.method == 'POST':
        product = Product(
            category_id=request.form['category_id'],
            name=request.form['name'],
            brand=request.form['brand'],
            size=request.form['size'],
            color=request.form.get('color'),
            motorcycle_model=request.form.get('motorcycle_model'),
            description=request.form['description'],
            price=float(request.form['price']),
            stock=int(request.form['stock']),
            image=request.form.get('image', '')
        )
        db.session.add(product)
        db.session.commit()
        
        log_activity(current_user.id, f'Added new product: {product.name}')
        flash('Product added successfully!', 'success')
        return redirect(url_for('admin_products'))
    
    categories = Category.query.all()
    return render_template('admin/add_product.html', categories=categories)

@app.route('/admin/staff')
@login_required
def manage_staff():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('shop'))
    
    staff_accounts = User.query.filter_by(is_staff=True).all()
    return render_template('admin/staff.html', staff_accounts=staff_accounts)

@app.route('/admin/add_staff', methods=['GET', 'POST'])
@login_required
def add_staff():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('shop'))
    
    if request.method == 'POST':
        staff = User(
            username=request.form['username'],
            email=request.form['email'],
            password=generate_password_hash(request.form['password']),
            address=request.form['address'],
            contact_number=request.form['contact_number'],
            is_staff=True
        )
        db.session.add(staff)
        db.session.commit()
        
        log_activity(current_user.id, f'Added new staff account: {staff.username}')
        flash('Staff account created successfully!', 'success')
        return redirect(url_for('manage_staff'))
    
    return render_template('admin/add_staff.html')

@app.route('/admin/categories')
@login_required
def manage_categories():
    if not current_user.is_admin and not current_user.is_staff:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('shop'))
    
    categories = Category.query.all()
    return render_template('admin/categories.html', categories=categories)

@app.route('/admin/add_category', methods=['GET', 'POST'])
@login_required
def add_category():
    if not current_user.is_admin and not current_user.is_staff:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('shop'))
    
    if request.method == 'POST':
        category = Category(
            name=request.form['name'],
            description=request.form.get('description')
        )
        db.session.add(category)
        db.session.commit()
        
        log_activity(current_user.id, f'Added new category: {category.name}')
        flash('Category added successfully!', 'success')
        return redirect(url_for('manage_categories'))
    
    return render_template('admin/add_category.html')

@app.route('/admin/blog')
@login_required
def manage_blog():
    if not current_user.is_admin and not current_user.is_staff:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('shop'))
    
    posts = BlogPost.query.order_by(BlogPost.created_at.desc()).all()
    return render_template('admin/blog.html', posts=posts)

@app.route('/admin/add_blog_post', methods=['GET', 'POST'])
@login_required
def add_blog_post():
    if not current_user.is_admin and not current_user.is_staff:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('shop'))
    
    if request.method == 'POST':
        post = BlogPost(
            title=request.form['title'],
            content=request.form['content'],
            image_url=request.form.get('image_url'),
            video_url=request.form.get('video_url'),
            user_id=current_user.id
        )
        db.session.add(post)
        db.session.commit()
        
        log_activity(current_user.id, f'Added new blog post: {post.title}')
        flash('Blog post added successfully!', 'success')
        return redirect(url_for('manage_blog'))
    
    return render_template('admin/add_blog_post.html')

@app.route('/admin/services')
@login_required
def manage_services():
    if not current_user.is_admin and not current_user.is_staff:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('shop'))
    
    services = Service.query.all()
    return render_template('admin/services.html', services=services)

@app.route('/admin/add_service', methods=['GET', 'POST'])
@login_required
def add_service():
    if not current_user.is_admin and not current_user.is_staff:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('shop'))
    
    if request.method == 'POST':
        service = Service(
            name=request.form['name'],
            description=request.form['description'],
            price=float(request.form['price']),
            duration=int(request.form['duration'])
        )
        db.session.add(service)
        db.session.commit()
        
        log_activity(current_user.id, f'Added new service: {service.name}')
        flash('Service added successfully!', 'success')
        return redirect(url_for('manage_services'))
    
    return render_template('admin/add_service.html')

@app.route('/profile')
@login_required
def profile():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.date_created.desc()).all()
    appointments = Appointment.query.filter_by(user_id=current_user.id).order_by(Appointment.date.desc()).all()
    return render_template('profile.html', orders=orders, appointments=appointments)

@app.route('/admin/edit_product/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_product(id):
    if not current_user.is_admin and not current_user.is_staff:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('shop'))

    product = Product.query.get_or_404(id)
    categories = Category.query.all()

    if request.method == 'POST':
        product.category_id = request.form['category_id']
        product.name = request.form['name']
        product.brand = request.form['brand']
        product.size = request.form['size']
        product.color = request.form.get('color')
        product.motorcycle_model = request.form.get('motorcycle_model')
        product.description = request.form['description']
        product.price = float(request.form['price'])
        product.stock = int(request.form['stock'])
        product.image = request.form.get('image', '')

        db.session.commit()
        log_activity(current_user.id, f'Edited product: {product.name}')
        flash('Product updated successfully!', 'success')
        return redirect(url_for('admin_products'))

    return render_template('admin/edit_product.html', product=product, categories=categories)

@app.route('/admin/delete_product/<int:id>', methods=['POST'])
@login_required
def delete_product(id):
    if not current_user.is_admin and not current_user.is_staff:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('shop'))

    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()

    log_activity(current_user.id, f'Deleted product: {product.name}')
    flash('Product deleted successfully!', 'success')
    return redirect(url_for('admin_products'))

@app.route('/order_confirmation/<int:order_id>')
@login_required
def order_confirmation(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('order_confirmation.html', order=order)


@app.route('/admin/edit_service/<int:service_id>', methods=['GET', 'POST'])
@login_required
def edit_service(service_id):
    if not current_user.is_admin and not current_user.is_staff:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('shop'))

    service = Service.query.get_or_404(service_id)

    if request.method == 'POST':
        service.name = request.form['name']
        service.description = request.form['description']
        service.price = float(request.form['price'])
        service.duration = int(request.form['duration'])

        db.session.commit()
        log_activity(current_user.id, f'Edited service: {service.name}')
        flash('Service updated successfully!', 'success')
        return redirect(url_for('manage_services'))

    return render_template('admin/edit_service.html', service=service)

@app.route('/admin/delete_service/<int:service_id>', methods=['POST'])
@login_required
def delete_service(service_id):
    if not current_user.is_admin and not current_user.is_staff:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('shop'))

    service = Service.query.get_or_404(service_id)
    db.session.delete(service)
    db.session.commit()

    log_activity(current_user.id, f'Deleted service: {service.name}')
    flash('Service deleted successfully!', 'success')
    return redirect(url_for('manage_services'))


@app.route('/admin/approve_order/<int:order_id>', methods=['POST'])
@login_required
def approve_order(order_id):
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('shop'))

    order = Order.query.get_or_404(order_id)
    order.status = 'approved'
    db.session.commit()

    # Send email notification
    send_notification(
        order.user.email,
        'Order Approved',
        f'Your order #{order.id} has been approved. Thank you for shopping with us!'
    )

    flash('Order approved successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/decline_order/<int:order_id>', methods=['POST'])
@login_required
def decline_order(order_id):
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('shop'))

    order = Order.query.get_or_404(order_id)
    order.status = 'declined'
    db.session.commit()

    # Send email notification
    send_notification(
        order.user.email,
        'Order Declined',
        f'Your order #{order.id} has been declined. Please contact us for more information.'
    )

    flash('Order declined successfully!', 'success')
    return redirect(url_for('admin_dashboard'))


    


def generate_reference_code():
    # Generate a random 6-digit number
    code = random.randint(100000, 999999)
    # Ensure the code is unique
    while Appointment.query.filter_by(reference_code=str(code)).first():
        code = random.randint(100000, 999999)
    return str(code)

def init_db():
    with app.app_context():
        db.drop_all()
        
        # Create all tables
        db.create_all()
        
        # Create admin user
        admin_user = User(
            username='admin',
            email='admin@example.com',
            password=generate_password_hash('adminpassword'),
            is_admin=True,
            is_staff=True  # Make admin a staff member as well
        )
        db.session.add(admin_user)
        
        # Create default categories
        default_categories = ['Suspension', 'Tires', 'Accessories', 'Oils', 'Others']
        for category_name in default_categories:
            category = Category(name=category_name)
            db.session.add(category)
        
        # Commit all changes
        db.session.commit()
        print("Database initialized successfully!")

if __name__ == '__main__':
    init_db()  # Initialize database first
    app.run(debug=True)