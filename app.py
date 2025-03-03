from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_mail import Mail, Message
from datetime import datetime, time, timedelta
import os
import random
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your_secret_key_here')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///motorparts.db'

# SMTP Gmail Configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')  # Load from environment variable

cache = Cache(app, config={'CACHE_TYPE': 'simple'})
limiter = Limiter(key_func=get_remote_address)  # Create the Limiter instance first
limiter.init_app(app) 


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
    status = db.Column(db.String(20), default='pending')  # Add more statuses like 'approved', 'declined', 'pending_payment', 'payment_rejected'
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    total_amount = db.Column(db.Float, nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    contact_number = db.Column(db.String(20), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    reference_number = db.Column(db.String(50))  # For GCash reference numbers
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
    blog_posts = BlogPost.query.order_by(BlogPost.created_at.desc()).limit(3).all()
    return render_template('landing.html', blog_posts=blog_posts)

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

# Update to the Order model - add this field:
# In the Order class definition, add this line:
# reference_number = db.Column(db.String(50))  # For GCash reference numbers

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        address = request.form.get('address')
        contact_number = request.form.get('contact_number')
        payment_method = request.form.get('payment_method')
        reference_number = request.form.get('reference_number', '')  # Get reference number if present

        # Check if any required field is missing
        if not name or not address or not contact_number or not payment_method:
            flash('Please fill out all required fields.', 'error')
            return redirect(url_for('checkout'))

        # If GCash is selected, ensure reference number is provided
        if payment_method == 'gcash' and not reference_number:
            flash('Please provide the GCash reference number.', 'error')
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
            payment_method=payment_method,
            reference_number=reference_number if payment_method == 'gcash' else None,
            # For GCash payments, set initial status to 'pending_payment'
            status='pending_payment' if payment_method == 'gcash' else 'pending'
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
            # Only reduce stock for non-GCash orders or confirmed GCash payments
            if payment_method != 'gcash':
                cart_item.product.stock -= cart_item.quantity
            db.session.add(order_item)

        # Clear the cart
        CartItem.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()

        # Log activity and send notification
        log_activity(current_user.id, f'Placed order #{order.id}')
        
        # Customize notification based on payment method
        if payment_method == 'gcash':
            send_notification(
                current_user.email, 
                'Order Confirmation - Pending GCash Payment Verification', 
                f'Your order #{order.id} has been placed successfully. We are verifying your GCash payment with reference number {reference_number}. We will process your order once the payment is confirmed.'
            )
        else:
            send_notification(
                current_user.email, 
                'Order Confirmation', 
                f'Your order #{order.id} has been placed successfully.'
            )

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
        period = request.form['period']  # 'morning' or 'afternoon'
        date = datetime.strptime(date_str, '%Y-%m-%d')

        if date < datetime.now():
            flash('Cannot book appointments in the past', 'error')
            return redirect(url_for('appointments'))

        # Generate a reference code
        reference_code = generate_reference_code()

        # Set the time based on the period
        if period == 'morning':
            time_slot = time(8, 0)  # Default to 8:00 AM for morning
        else:
            time_slot = time(13, 0)  # Default to 1:00 PM for afternoon

        appointment_date = datetime.combine(date, time_slot)

        appointment = Appointment(
            user_id=current_user.id,
            customer_name=request.form['name'],
            motorcycle_model=request.form['motorcycle_model'],
            contact_number=request.form['contact_number'],
            date=appointment_date,
            service_type=request.form['service_type'],
            reference_code=reference_code  # Add the reference code
        )

        db.session.add(appointment)
        db.session.commit()

        # Send email with the reference code
        send_notification(
            current_user.email,
            'Appointment Confirmation',
            f'Your appointment for {appointment.service_type} on {appointment_date} has been scheduled. '
            f'Your reference code is: {reference_code}. Please present this code when visiting the site.'
        )

        flash('Appointment booked successfully!', 'success')
        return redirect(url_for('appointments'))
    except ValueError:
        flash('Invalid date format', 'error')
        return redirect(url_for('appointments'))
@app.route('/api/available_slots', methods=['GET'])
@login_required
def available_slots():
    start_str = request.args.get('start')  # For FullCalendar date range
    end_str = request.args.get('end')      # For FullCalendar date range
    date_str = request.args.get('date')    # For single date selection

    if not (start_str and end_str) and not date_str:
        return jsonify({'error': 'Either start/end or date parameter is required'}), 400

    try:
        if start_str and end_str:
            # Handle FullCalendar date range request
            start_date = datetime.fromisoformat(start_str).date()
            end_date = datetime.fromisoformat(end_str).date()

            # Query existing appointments within the date range
            existing_appointments = Appointment.query.filter(
                func.date(Appointment.date) >= start_date,
                func.date(Appointment.date) <= end_date
            ).all()

            # Prepare events for FullCalendar
            events = []
            for appointment in existing_appointments:
                events.append({
                    'title': f'{appointment.customer_name} - {appointment.service_type}',
                    'start': appointment.date.isoformat(),
                    'end': (appointment.date + timedelta(minutes=30)).isoformat(),
                    'color': 'blue'  # Customize the event color
                })

            return jsonify(events)

        elif date_str:
            # Handle single date selection for booking
            date = datetime.strptime(date_str, '%Y-%m-%d').date()

            # Query existing appointments for this date
            existing_appointments = Appointment.query.filter(
                func.date(Appointment.date) == date
            ).all()

            # Count appointments for morning and afternoon
            morning_count = len([app for app in existing_appointments if app.date.time() < time(12, 0)])
            afternoon_count = len([app for app in existing_appointments if app.date.time() >= time(12, 0)])

            # Calculate remaining slots
            morning_remaining = max(0, 25 - morning_count)
            afternoon_remaining = max(0, 25 - afternoon_count)

            return jsonify({
                'morning_remaining': morning_remaining,
                'afternoon_remaining': afternoon_remaining
            })

    except ValueError as e:
        return jsonify({'error': f'Invalid date format: {e}'}), 400
        
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            log_activity(user.id, 'User logged in')
            flash('Login successful!', 'success')

            # Redirect admin users to dashboard, others to shop
            if user.is_admin:
                return redirect(url_for('admin_dashboard'))
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

    # Add the pending GCash orders count to the context
    pending_gcash = Order.query.filter_by(payment_method='gcash', status='pending_payment').count()

    return render_template('admin_dashboard.html',
                         pending_appointments=pending_appointments,
                         products=products,
                         low_stock_products=low_stock_products,
                         recent_logs=recent_logs,
                         recent_orders=recent_orders,
                         recent_appointments=recent_appointments,
                         sales_stats=sales_stats,
                         pending_gcash=pending_gcash)
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

@app.context_processor
def inject_cart_count():
    cart_count = 0
    if current_user.is_authenticated:
        # Get count from user's cart items in the database
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        cart_count = sum(item.quantity for item in cart_items)
    return dict(cart_count=cart_count)

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

@app.route('/blog/<int:post_id>')
def view_blog_post(post_id):
    post = BlogPost.query.get_or_404(post_id)
    return render_template('blog_post.html', post=post)

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


    # Enable CORS for Botpress
CORS(app, resources={
    r"/api/*": {
        "origins": ["https://cdn.botpress.cloud"],
        "methods": ["GET"],
        "allow_headers": ["Content-Type"]
    }
})

@app.route('/api/botpress/products', methods=['GET'])
@limiter.limit("10 per minute")
def botpress_products():
    try:
        search = request.args.get('search', '').lower()
        category = request.args.get('category', '')
        
        query = Product.query.options(db.joinedload(Product.category))
        
        if search:
            query = query.filter(
                db.or_(
                    Product.name.ilike(f'%{search}%'),
                    Product.description.ilike(f'%{search}%'),
                    Product.brand.ilike(f'%{search}%'),
                    Product.motorcycle_model.ilike(f'%{search}%')
                )
            )
        
        if category:
            if not Category.query.filter(Category.name.ilike(f'%{category}%')).first():
                return jsonify({'error': 'Invalid category'}), 400
            query = query.join(Category).filter(Category.name.ilike(f'%{category}%'))
        
        products = query.all()
        
        return jsonify({
            'status': 'success',
            'data': {
                'products': [{
                    'name': p.name,
                    'brand': p.brand,
                    'price': p.price,
                    'stock': p.stock,
                    'category': p.category.name,
                    'motorcycle_model': p.motorcycle_model,
                    'description': p.description
                } for p in products]
            }
        })
    except SQLAlchemyError as e:
        return jsonify({'error': 'Database error', 'details': str(e)}), 500

@app.route('/api/botpress/categories', methods=['GET'])
@cache.cached(timeout=60)
def botpress_categories():
    categories = Category.query.all()
    return jsonify({
        'status': 'success',
        'data': {
            'categories': [c.name for c in categories]
        }
    })

@app.route('/api/botpress/product/<string:name>', methods=['GET'])
def botpress_product_detail(name):
    product = Product.query.filter(Product.name.ilike(f'%{name}%')).first()
    if not product:
        return jsonify({'error': 'Product not found'}), 404
        
    return jsonify({
        'status': 'success',
        'data': {
            'name': product.name,
            'brand': product.brand,
            'price': product.price,
            'stock': product.stock,
            'category': product.category.name,
            'motorcycle_model': product.motorcycle_model,
            'description': product.description
        }
    })

@app.route('/admin/verify_gcash', methods=['GET'])
@login_required
def admin_verify_gcash():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('shop'))
    
    # Get all orders with pending GCash payments
    pending_orders = Order.query.filter_by(
        payment_method='gcash',
        status='pending_payment'
    ).order_by(Order.date_created.desc()).all()
    
    return render_template('admin/verify_gcash.html', pending_orders=pending_orders)

@app.route('/admin/verify_gcash/<int:order_id>', methods=['POST'])
@login_required
def verify_gcash_payment(order_id):
    if not current_user.is_admin:
        flash('You do not have permission to perform this action.', 'error')
        return redirect(url_for('shop'))
    
    order = Order.query.get_or_404(order_id)
    action = request.form.get('action')
    
    if order.payment_method != 'gcash' or order.status != 'pending_payment':
        flash('Invalid order status or payment method.', 'error')
        return redirect(url_for('admin_verify_gcash'))
    
    if action == 'confirm':
        # Update order status
        order.status = 'approved'
        
        # Update product stock (now that payment is confirmed)
        for order_item in order.order_items:
            product = Product.query.get(order_item.product_id)
            if product:
                product.stock -= order_item.quantity
        
        # Log the activity
        log_activity(current_user.id, f'Confirmed GCash payment for order #{order.id}')
        
        # Send confirmation email to customer
        send_notification(
            order.user.email,
            'GCash Payment Confirmed',
            f'Your GCash payment for order #{order.id} has been verified. We will process your order shortly. Thank you for your purchase!'
        )
        
        flash('GCash payment confirmed successfully.', 'success')
    
    elif action == 'reject':
        # Update order status
        order.status = 'payment_rejected'
        
        # Log the activity
        log_activity(current_user.id, f'Rejected GCash payment for order #{order.id}')
        
        # Send rejection email to customer
        send_notification(
            order.user.email,
            'GCash Payment Rejected',
            f'We could not verify your GCash payment for order #{order.id}. Please contact our customer support for assistance.'
        )
        
        flash('GCash payment rejected.', 'success')
    
    db.session.commit()
    return redirect(url_for('admin_verify_gcash'))


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
    app.run(debug=True)