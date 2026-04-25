from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_pymongo import PyMongo
from community_routes import community_bp
import random
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId

app = Flask(__name__)

# Secret key (needed for session/login to work)
app.secret_key = 'connecther-secret-key'

# MongoDB connection
#app.config["MONGO_URI"] = "mongodb://localhost:27017/connecther"
app.config["MONGO_URI"] = "mongodb+srv://admin:connect123@cluster0.eg0o1rm.mongodb.net/connecther?retryWrites=true&w=majority"
mongo = PyMongo(app)

# uni_db_uri = "mongodb://nigarishnavaid0_db_user:hello123@cluster0-shard-00-00.3frl0uo.mongodb.net:27017,cluster0-shard-00-01.3frl0uo.mongodb.net:27017,cluster0-shard-00-02.3frl0uo.mongodb.net:27017/ConnectHer?ssl=true&replicaSet=atlas-shard-0&authSource=admin&retryWrites=true&w=majority"
uni_db_uri = "mongodb+srv://nigarishnavaid0_db_user:hello123@cluster0.3frl0uo.mongodb.net/ConnectHer?retryWrites=true&w=majority"
uni_mongo = PyMongo(app, uri=uni_db_uri)

# Register your blueprint
app.register_blueprint(community_bp)


# Configure Flask-Mail (Use your HU email password)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'connecther67@gmail.com'
app.config['MAIL_PASSWORD'] = 'pobs cfif hmbw effd'
mail = Mail(app)

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/admin-auth')
def admin_auth():
    return render_template('admin_auth.html')

@app.route('/admin-dashboard')
def admin_dashboard():
    # In a real app, you'd check for a session/cookie here to ensure the user actually entered the key
    return render_template('admin_dashboard.html')

@app.route('/admin/users')
def admin_users():
    # Fetch all users from the MongoDB database
    all_users = list(mongo.db.users.find())
    return render_template('admin_users.html', users=all_users)

@app.route('/admin/delete-user/<user_id>', methods=['POST'])
def delete_user(user_id):
    try:
        mongo.db.users.delete_one({'_id': ObjectId(user_id)})
        flash('User deleted successfully.', 'success')
    except Exception as e:
        flash(f'Error deleting user: {str(e)}', 'error')
    return redirect(url_for('admin_users'))

    
@app.route('/register-page')
def register_page():
    # This shows the actual form we built earlier
    return render_template('register_form.html') 

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email').strip().lower()
        password = request.form.get('password').strip()

        user = mongo.db.users.find_one({'email': email})

        # Use check_password_hash instead of !=
        if not user or not check_password_hash(user['password'], password):
            flash('Incorrect Password or Email', 'error')
            return redirect(url_for('login'))

        if user.get('status') != 'approved':
            flash('Your account is still pending admin approval.', 'error')
            return redirect(url_for('login'))

        session['user_id'] = str(user['_id'])
        
        # Store the user's actual data in the session
        session['user'] = {
            "name": user.get('username', 'New User'),
            "department": user.get('department', 'Not Set'),
            "interests": user.get('interests', 'None'),
            "about": user.get('about', '')
        }
        # --- FIX ENDS HERE ---

        #return redirect(url_for('dashboard')) # Redirect to dashboard instead of communities to see the change
        return redirect(url_for('community.communities'))
    return render_template('login.html')

@app.route('/register', methods=['POST'])
def register():
    email = request.form.get('email')
    full_name = request.form.get('full_name')
    password = request.form.get('password')

    # 1. Check for HU Email
    if not email.lower().endswith('@st.habib.edu.pk'):
        flash('You must enter your HU Email', 'error')
        return redirect(url_for('register_page'))

    # 2. Check Full Name
    if not full_name or len(full_name.strip()) < 2:
        flash('Please enter your valid Full Name', 'error')
        return redirect(url_for('register_page'))

    official_record = uni_mongo.db.Uni_directory.find_one({'email': email})
    
    if not official_record:
        flash('This Student ID is not recognized by the university system.', 'error')
        return redirect(url_for('register_page'))

    # 3. GENDER CHECK
    if official_record.get('gender') != 'female':
        flash('You are a man!😡', 'error')
        return redirect(url_for('register_page'))
    
    # 3. Check if user is already registered
    existing_user = mongo.db.users.find_one({'email': email})
    if existing_user:
        flash('User is already registered', 'error')
        return redirect(url_for('register_page'))

    # Generate a 6-digit OTP
    otp = str(random.randint(100000, 999999))
    
    # Store everything in session (Hardcoding CNIC as a placeholder)
    session['temp_user'] = {
        'email': email,
        'full_name': full_name,
        'cnic': "0000000000000", # Placeholder so DB stays consistent
        'password': password,
        'otp': otp
    }

    # Send the Email
    msg = Message('Your ConnectHer Verification Code', 
                  sender=app.config['MAIL_USERNAME'], 
                  recipients=[email])
    msg.body = f"Your OTP for ConnectHer registration is: {otp}"
    
    try:
        mail.send(msg)
        return redirect(url_for('verify_otp'))
    except Exception as e:
        print(f"Error sending email: {e}")
        flash("Error sending email. Please check your credentials.", "error")
        return redirect(url_for('register_page'))

from werkzeug.security import generate_password_hash

@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        user_otp = request.form.get('otp')
        temp_user = session.get('temp_user')

        if temp_user and user_otp == temp_user['otp']:
            hashed_password = generate_password_hash(temp_user['password'])
            
            # OTP MATCHES - Insert with placeholder CNIC
            mongo.db.users.insert_one({
                'email': temp_user['email'],
                'full_name': temp_user['full_name'],
                'username': temp_user['full_name'],  # Set username to full name initially
                'cnic': temp_user['cnic'], # This will be the "00000..." string
                'password': hashed_password,
                'status': 'approved'
            })
            
            session.pop('temp_user', None)
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
    hashed_new_password = generate_password_hash(new_password)
    mongo.db.users.update_one(
        {'email': email},
        {'$set': {'password': hashed_new_password}}
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

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    from bson.objectid import ObjectId
    db = mongo.db
    user_id = session['user_id']

    # 1. FETCH ACTUAL USER DATA FROM DB
    # This replaces the hardcoded "Sara Ali" dictionary
    user_data = db.users.find_one({'_id': ObjectId(user_id)})

    if not user_data:
        flash("User not found", "error")
        return redirect(url_for('logout'))

    # Prepare user dict for template (defaults to "Not Set" if empty)
    user = {
        "name": user_data.get('username', 'New Member'),
        "department": user_data.get('department', 'Not Set Yet'),
        "interests": user_data.get('interests', 'None listed'),
        "about": user_data.get('about', 'Tell us about yourself!')
    }

    # 2. DYNAMIC ACTIVITY (Count actual posts/comments from DB)
    # This is no longer hardcoded to 5 and 12
    post_count = db.posts.count_documents({'author_id': user_id})
    
    # Count total comments by the user across all posts
    comment_pipeline = [
        {"$unwind": "$comments"},
        {"$match": {"comments.author_id": user_id}},
        {"$count": "total_comments"}
    ]
    comment_result = list(db.posts.aggregate(comment_pipeline))
    comment_count = comment_result[0]['total_comments'] if comment_result else 0

    activity = {
        "posts": post_count,
        "comments": comment_count
    }

    # 3. LENDING & RECENT (Keep empty for now as per your request)
    lending = [] 
    recent = []

    return render_template(
        'dashboard.html',
        user=user,
        activity=activity,
        lending=lending,
        recent=recent
    )

@app.route('/home')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    from bson.objectid import ObjectId
    db = mongo.db
    user_id = session['user_id']

    # Get communities the user is a member of
    memberships = db.memberships.find({'user_id': user_id})
    community_ids = [m['community_id'] for m in memberships]

    if not community_ids:
        # User hasn't joined any communities yet
        posts = []
    else:
        # Get posts from joined communities, sorted by newest first
        posts = list(db.posts.find({'community_id': {'$in': community_ids}}).sort('created_at', -1))

        # Add community names to posts
        for post in posts:
            community = db.communities.find_one({'_id': post['community_id']})
            post['community_name'] = community['name'] if community else 'Unknown Community'

    return render_template('home.html', posts=posts, session_user_id=user_id)

@app.route('/edit-profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    from bson.objectid import ObjectId
    db = mongo.db
    user_id = session['user_id']

    if request.method == 'POST':
        # Get data from the HTML form
        name = request.form.get('name')
        dept = request.form.get('department')
        interests = request.form.get('interests')
        about = request.form.get('about')

        # Update the specific user document in MongoDB
        db.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {
                'username': name,
                'department': dept,
                'interests': interests,
                'about': about
            }}
        )

        flash("Profile updated successfully!", "success")
        return redirect(url_for('dashboard'))

    # GET: Fetch current data to pre-fill the edit form
    user_data = db.users.find_one({'_id': ObjectId(user_id)})
    
    # Prepare user dict for template
    user = {
        "name": user_data.get('username', ''),
        "department": user_data.get('department', ''),
        "interests": user_data.get('interests', ''),
        "about": user_data.get('about', '')
    }
    
    return render_template('edit_profile.html', user=user)

@app.route('/public-profile/<user_id>')
def public_profile(user_id):
    try:
        user_data = mongo.db.users.find_one({'_id': ObjectId(user_id)})
    except:
        flash("Invalid user ID format.", "error")
        return redirect(url_for('admin_users'))

    if not user_data:
        flash("User not found.", "error")
        return redirect(url_for('admin_users'))

    # Map the actual MongoDB data to the dictionary expected by your template
    # If the user hasn't set up interests, it defaults to empty
    raw_interests = user_data.get('interests', '')
    tags = raw_interests.split(',') if raw_interests else []

    user = {
        "name": user_data.get('full_name', user_data.get('username', 'Unknown Member')),
        "department": user_data.get('department', 'Department not specified'),
        "tags": tags,
        "about": user_data.get('about', 'This user has not written a bio yet.'),
    }

    # Fetching real posts for this user (if you have a posts collection)
    # user_posts = list(mongo.db.posts.find({'author_id': user_id}))
    # For now, using placeholder data since we just need the profile to open
    posts = ["User hasn't posted anything recently."]
    communities = ["Not listed."]
    reviews = ["No reviews yet."]

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