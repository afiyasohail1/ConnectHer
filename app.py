from flask import Flask
from flask_pymongo import PyMongo
from community_routes import community_bp

app = Flask(__name__)

# Secret key (needed for session/login to work)
app.secret_key = 'connecther-secret-key'

# MongoDB connection
app.config["MONGO_URI"] = "mongodb+srv://afiyaasohail_db_user:abc123Notify@cluster0.2wvn9h5.mongodb.net/connecther?appName=Cluster0"
mongo = PyMongo(app)

# Register your blueprint
app.register_blueprint(community_bp)

@app.route('/fake-login')
def fake_login():
    from flask import session
    session['user_id'] = 'test_user_123'
    session['username'] = 'Afiya'
    return 'Logged in! Now go to <a href="/communities">/communities</a>'

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

if __name__ == '__main__':
    app.run(debug=True)