from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_pymongo import PyMongo
from community_routes import community_bp
import random
from flask_mail import Mail, Message

app = Flask(__name__)

# Secret key (needed for session/login to work)
app.secret_key = 'connecther-secret-key'

# MongoDB connection
app.config["MONGO_URI"] = "mongodb://localhost:27017/connecther"
mongo = PyMongo(app)

# Register your blueprint
app.register_blueprint(community_bp)

@app.route('/fake-login')
def fake_login():
    from flask import session
    session['user_id'] = 'test_user_123'
    session['username'] = 'Afiya'
    return 'Logged in! Now go to <a href="/communities">/communities</a>'
# Configure Flask-Mail (Use your HU email password)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your-username0@gmail.com'
app.config['MAIL_PASSWORD'] = 'your-app-password'
mail = Mail(app)

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/register-page')
def register_page():
    # This shows the actual form we built earlier
    return render_template('register_form.html') 

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = mongo.db.users.find_one({'email': email})

        if not user:
            flash('User is not registered', 'error')
            return redirect(url_for('login'))

        if user['password'] != password:
            flash('Incorrect Password or Email', 'error')
            return redirect(url_for('login'))

        # Check if the user is approved
        if user.get('status') != 'approved':
            flash('Your account is still pending admin approval.', 'error')
            return redirect(url_for('login'))

        # If all checks pass:
        session['user_id'] = str(user['_id'])
        return redirect(url_for('community.communities'))

    return render_template('login.html')

@app.route('/register', methods=['POST'])
def register():
    email = request.form.get('email')
    cnic = request.form.get('cnic')
    password = request.form.get('password')

    # 1. Check for HU Email
    if not email.lower().endswith('@st.habib.edu.pk'):
        flash('You must enter your HU Email', 'error')
        return redirect(url_for('register_page'))

    # 2. Check CNIC Length
    if len(cnic) != 13:
        flash('CNIC must be 13 digits', 'error')
        return redirect(url_for('register_page'))

    # 3. Check CNIC for numbers only
    if not cnic.isdigit():
        flash('CNIC must contain numbers only', 'error')
        return redirect(url_for('register_page'))
    
    #4. Check if user is already registered
    existing_user = mongo.db.users.find_one({'email': email})
    if existing_user:
        flash('User is already registered', 'error')
        return redirect(url_for('register_page'))

    # Generate a 6-digit OTP
    otp = str(random.randint(100000, 999999))
    
    session['temp_user'] = {
        'email': request.form.get('email'),
        'cnic': request.form.get('cnic'),
        'password': request.form.get('password'),
        'otp': otp
    }

    # IMPORTANT: Ensure 'sender' matches your MAIL_USERNAME
    msg = Message('Your ConnectHer Verification Code', 
                  sender=app.config['MAIL_USERNAME'], 
                  recipients=[session['temp_user']['email']])
    msg.body = f"Your OTP for ConnectHer registration is: {otp}"
    
    try:
        mail.send(msg)
    except Exception as e:
        print(f"Error sending email: {e}")
        flash("Error sending email. Please check your credentials.", "error")
        return redirect(url_for('register_page'))

    # Change this to match the name of your verify-otp function
    return redirect(url_for('verify_otp'))

@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        user_otp = request.form.get('otp')
        temp_user = session.get('temp_user')

        if temp_user and user_otp == temp_user['otp']:
            # OTP MATCHES - Finally add to MongoDB
            mongo.db.users.insert_one({
                'email': temp_user['email'],
                'cnic': temp_user['cnic'],
                'password': temp_user['password'],
                'status': 'approved'
            })
            session.pop('temp_user', None) # Clear temp data
            flash("Your request has been approved. Click 'Continue' to proceed", 'success')
            return redirect(url_for('register_page'))
        else:
            flash('Invalid OTP. Please try again.', 'error')
            return redirect(url_for('verify_otp'))

    return render_template('verify_otp.html')

@app.route('/wipe-users')
def wipe_users():
    mongo.db.users.delete_many({}) # The empty {} means "delete everything"
    return "User database is now empty. <a href='/register-page'>Start Fresh</a>"

@app.route('/forgot-password')
def forgot_password_page():
    return render_template('reset_password.html')

@app.route('/reset-password', methods=['POST'])
def reset_password():
    email = request.form.get('email').lower()
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    # 1. Check if user exists
    user = mongo.db.users.find_one({'email': email})
    if not user:
        flash('User is not registered', 'error') # 디자인 image_e039fa.png
        return redirect(url_for('forgot_password_page'))

    # 2. Check if passwords match (Design 8)
    if new_password != confirm_password:
        flash('Passwords do not match', 'error') # 디자인 image_e36816.png
        return redirect(url_for('forgot_password_page'))

    # 3. Update Password in MongoDB
    mongo.db.users.update_one(
        {'email': email},
        {'$set': {'password': new_password}}
    )

    # 4. Success Verification (Design 7)
    flash('Your password has been updated', 'success') # 디자인 image_e36816.png
    return redirect(url_for('forgot_password_page'))

@app.route('/logout')
def logout():
    # Remove user_id from session
    session.pop('user_id', None)
    # Optional: Clear everything from session
    # session.clear() 
    
    flash('You have been logged out.', 'success')
    return redirect(url_for('landing'))

@app.route('/seed-data')
def seed_data():
    mongo.db.communities.delete_many({})
    mongo.db.communities.insert_many([
        {'name': 'Study Group',          'description': 'Share notes, discuss assignments, and ace exams together!',       'icon': '📚', 'color': '#A680B8', 'status': 'active'},
        {'name': 'Campus Events',        'description': 'Stay updated on university events, fests, and activities.',       'icon': '🎉', 'color': '#C4A0D8', 'status': 'active'},
        {'name': 'Mental Wellness',      'description': 'A safe, judgement-free space to talk and support each other.',    'icon': '💜', 'color': '#8B5FA0', 'status': 'active'},
        {'name': 'Fashion & Style',      'description': 'Outfit inspo, styling tips, and all things fashion!',             'icon': '👗', 'color': '#D4A0C8', 'status': 'active'},
        {'name': 'Food & Recipes',       'description': 'Share your favourite recipes, restaurant finds, and food pics.',  'icon': '🍜', 'color': '#B890C8', 'status': 'active'},
        {'name': 'Career & Internships', 'description': 'Job hunts, CV tips, internship openings and career advice.',      'icon': '💼', 'color': '#9870A8', 'status': 'active'},
        {'name': 'Book Club',            'description': 'Reading recommendations, reviews, and monthly book discussions.', 'icon': '📖', 'color': '#A090C0', 'status': 'active'},
        {'name': 'Sports & Fitness',     'description': 'Workout routines, sports teams, and staying active on campus.',   'icon': '🏃‍♀️', 'color': '#B880B8', 'status': 'active'},
        {'name': 'Arts & Creativity',    'description': 'Painting, photography, crafts — share your creative work here.', 'icon': '🎨', 'color': '#C880A8', 'status': 'active'},
        {'name': 'Tech & Coding',        'description': 'Programming help, hackathons, tech news and project collabs.',    'icon': '💻', 'color': '#8860A0', 'status': 'active'},
    ])
    return 'Communities added! <a href="/communities">Go to Communities</a>'

# DASHBOARD
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/fake-login')
    if 'user' in session:
        user = session['user']
    else:
        user = {
            "name": "Sara Ali",
            "department": "Computer Science",
            "interests": "Coding, Reading",
            "about": "Passionate student who loves tech and communities"
        }

    lending = [
        "Borrowed: Data Structures Book",
        "Returned: Calculator"
    ]

    activity = {
        "posts": 5,
        "comments": 12
    }

    recent = [
        "Posted in Study Group",
        "Commented on a post",
        "Joined Tech Community"
    ]

    return render_template(
        'dashboard.html',
        user=user,
        lending=lending,
        activity=activity,
        recent=recent
    )

@app.route('/edit-profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect('/fake-login')
    if 'user' in session:
        user = session['user']
    else:
        user = {
            "name": "Sara Ali",
            "department": "Computer Science",
            "interests": "Coding, Reading",
            "about": "Passionate student who loves tech and communities"
        }

    if request.method == 'POST':

        name = request.form['name']
        department = request.form['department']
        interests = request.form['interests']
        about = request.form['about']

        # VALIDATION
        if not name or not department:
            error = "Name and Department are required!"
            return render_template('edit_profile.html', user=user, error=error)

        # SAVE
        user = {
            "name": name,
            "department": department,
            "interests": interests,
            "about": about
        }

        session['user'] = user

        return redirect('/dashboard')

    return render_template('edit_profile.html', user=user)

@app.route('/public-profile')
def public_profile():

    user = {
        "name": "Sarah Khalid",
        "department": "Computer Science",
        "tags": ["AI", "Entrepreneurship", "Design"],
        "about": "Passionate about building innovative solutions and connecting with fellow students.",
    }

    posts = [
        "Just finished building my first ML model!",
        "Anyone interested in joining a study group?",
        "Sharing some resources on sustainable design practices."
    ]

    communities = [
        "AI & Machine Learning",
        "Startup Enthusiasts",
        "Women in Tech",
        "Sustainable Living"
    ]

    reviews = [
        "Super reliable! Highly recommend.",
        "Very helpful and responsive.",
        "Great person to connect with."
    ]

    return render_template(
        'public_profile.html',
        user=user,
        posts=posts,
        communities=communities,
        reviews=reviews
    )

# fake login
@app.route('/fake-login')
def fake_login():
    session['user_id'] = 'test_user'
    return redirect('/dashboard')


if __name__ == '__main__':
    app.run(debug=True)