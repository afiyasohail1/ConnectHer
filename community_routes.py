from flask import Blueprint, render_template, redirect, url_for, flash, session, request
from bson.objectid import ObjectId
from datetime import datetime
import os

community_bp = Blueprint('community', __name__)

def get_db():
    from app import mongo
    return mongo.db

@community_bp.route('/communities')
def communities():
    if 'user_id' not in session:
        flash('Please log in first.', 'danger')
        return redirect(url_for('fake_login'))
    db = get_db()
    user_id = session['user_id']
    all_communities = list(db.communities.find())
    memberships = db.memberships.find({'user_id': user_id})
    joined_ids = {str(m['community_id']) for m in memberships}
    for community in all_communities:
        community['member_count'] = db.memberships.count_documents({'community_id': community['_id']})
    return render_template('communities.html', communities=all_communities, joined_ids=joined_ids)

@community_bp.route('/communities/<community_id>/join', methods=['POST'])
def join_community(community_id):
    if 'user_id' not in session:
        flash('Please log in first.', 'danger')
        return redirect(url_for('fake_login'))
    db = get_db()
    user_id = session['user_id']
    community = db.communities.find_one({'_id': ObjectId(community_id)})
    if not community:
        flash('Community not found.', 'danger')
        return redirect(url_for('community.communities'))
    existing = db.memberships.find_one({'user_id': user_id, 'community_id': ObjectId(community_id)})
    if existing:
        flash(f'You are already a member of {community["name"]}.', 'info')
        return redirect(url_for('community.communities'))
    db.memberships.insert_one({'user_id': user_id, 'community_id': ObjectId(community_id), 'joined_at': datetime.utcnow()})
    flash(f'You joined {community["name"]}! 🎉', 'success')
    return redirect(url_for('community.communities'))

@community_bp.route('/communities/<community_id>/leave', methods=['POST'])
def leave_community(community_id):
    if 'user_id' not in session:
        flash('Please log in first.', 'danger')
        return redirect(url_for('fake_login'))
    db = get_db()
    user_id = session['user_id']
    community = db.communities.find_one({'_id': ObjectId(community_id)})
    if not community:
        flash('Community not found.', 'danger')
        return redirect(url_for('community.communities'))
    result = db.memberships.delete_one({'user_id': user_id, 'community_id': ObjectId(community_id)})
    if result.deleted_count == 0:
        flash('You are not a member of this community.', 'info')
    else:
        flash(f'You left {community["name"]}.', 'info')
    return redirect(url_for('community.communities'))

@community_bp.route('/communities/<community_id>/feed')
def community_feed(community_id):
    if 'user_id' not in session:
        flash('Please log in first.', 'danger')
        return redirect(url_for('fake_login'))
    db = get_db()
    user_id = session['user_id']
    membership = db.memberships.find_one({'user_id': user_id, 'community_id': ObjectId(community_id)})
    if not membership:
        flash('Join this community to view its feed.', 'info')
        return redirect(url_for('community.communities'))
    community = db.communities.find_one({'_id': ObjectId(community_id)})
    if not community:
        flash('Community not found.', 'danger')
        return redirect(url_for('community.communities'))
    posts = list(db.posts.find({'community_id': ObjectId(community_id)}).sort('created_at', -1))
    member_count = db.memberships.count_documents({'community_id': ObjectId(community_id)})
    return render_template('community_feed.html', community=community, posts=posts,
                           member_count=member_count, session_user_id=user_id,
                           session_username=session.get('username', 'You'))

@community_bp.route('/communities/<community_id>/post', methods=['POST'])
def create_post(community_id):
    if 'user_id' not in session:
        flash('Please log in first.', 'danger')
        return redirect(url_for('fake_login'))
    db = get_db()
    user_id = session['user_id']
    username = session.get('username', 'Anonymous')
    content = request.form.get('content', '').strip()
    image_url = None
    if not content:
        flash('Post cannot be empty.', 'danger')
        return redirect(url_for('community.community_feed', community_id=community_id))
    image_file = request.files.get('image')
    if image_file and image_file.filename:
        allowed = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        ext = image_file.filename.rsplit('.', 1)[-1].lower()
        if ext not in allowed:
            flash('Invalid image format.', 'danger')
            return redirect(url_for('community.community_feed', community_id=community_id))
        upload_folder = os.path.join('static', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{image_file.filename}"
        image_file.save(os.path.join(upload_folder, filename))
        image_url = f"/static/uploads/{filename}"
    db.posts.insert_one({'community_id': ObjectId(community_id), 'author_id': user_id,
                         'author_name': username, 'content': content, 'image_url': image_url,
                         'likes': 0, 'liked_by': [], 'comments': [], 'created_at': datetime.utcnow()})
    flash('Post shared! 🌸', 'success')
    return redirect(url_for('community.community_feed', community_id=community_id))

@community_bp.route('/posts/<post_id>/edit', methods=['GET', 'POST'])
def edit_post(post_id):
    if 'user_id' not in session:
        flash('Please log in first.', 'danger')
        return redirect(url_for('fake_login'))
    db = get_db()
    user_id = session['user_id']
    post = db.posts.find_one({'_id': ObjectId(post_id)})
    if not post:
        flash('Post not found.', 'danger')
        return redirect(url_for('community.communities'))
    if post['author_id'] != user_id:
        flash('You can only edit your own posts.', 'danger')
        return redirect(url_for('community.community_feed', community_id=str(post['community_id'])))
    if request.method == 'POST':
        new_content = request.form.get('content', '').strip()
        if not new_content:
            flash('Post content cannot be empty.', 'danger')
        else:
            db.posts.update_one({'_id': ObjectId(post_id)}, {'$set': {'content': new_content, 'edited_at': datetime.utcnow()}})
            flash('Post updated! ✏️', 'success')
        return redirect(url_for('community.community_feed', community_id=str(post['community_id'])))
    return render_template('edit_post.html', post=post)

@community_bp.route('/posts/<post_id>/delete', methods=['POST'])
def delete_post(post_id):
    if 'user_id' not in session:
        flash('Please log in first.', 'danger')
        return redirect(url_for('fake_login'))
    db = get_db()
    user_id = session['user_id']
    post = db.posts.find_one({'_id': ObjectId(post_id)})
    if not post:
        flash('Post not found.', 'danger')
        return redirect(url_for('community.communities'))
    if post['author_id'] != user_id:
        flash('You can only delete your own posts.', 'danger')
        return redirect(url_for('community.community_feed', community_id=str(post['community_id'])))
    community_id = str(post['community_id'])
    db.posts.delete_one({'_id': ObjectId(post_id)})
    flash('Post deleted.', 'info')
    return redirect(url_for('community.community_feed', community_id=community_id))

@community_bp.route('/posts/<post_id>/like', methods=['POST'])
def like_post(post_id):
    if 'user_id' not in session:
        flash('Please log in first.', 'danger')
        return redirect(url_for('fake_login'))
    db = get_db()
    user_id = session['user_id']
    post = db.posts.find_one({'_id': ObjectId(post_id)})
    if not post:
        flash('Post not found.', 'danger')
        return redirect(url_for('community.communities'))
    liked_by = post.get('liked_by', [])
    if user_id in liked_by:
        db.posts.update_one({'_id': ObjectId(post_id)}, {'$pull': {'liked_by': user_id}, '$inc': {'likes': -1}})
    else:
        db.posts.update_one({'_id': ObjectId(post_id)}, {'$push': {'liked_by': user_id}, '$inc': {'likes': 1}})
    return redirect(url_for('community.community_feed', community_id=str(post['community_id'])))

@community_bp.route('/posts/<post_id>/comment', methods=['POST'])
def comment_post(post_id):
    if 'user_id' not in session:
        flash('Please log in first.', 'danger')
        return redirect(url_for('fake_login'))
    db = get_db()
    user_id = session['user_id']
    username = session.get('username', 'Anonymous')
    comment_text = request.form.get('comment_text', '').strip()
    post = db.posts.find_one({'_id': ObjectId(post_id)})
    if not post:
        flash('Post not found.', 'danger')
        return redirect(url_for('community.communities'))
    if not comment_text:
        flash('Comment cannot be empty.', 'danger')
        return redirect(url_for('community.community_feed', community_id=str(post['community_id'])))
    comment = {'author_id': user_id, 'author_name': username, 'text': comment_text, 'created_at': datetime.utcnow()}
    db.posts.update_one({'_id': ObjectId(post_id)}, {'$push': {'comments': comment}})
    return redirect(url_for('community.community_feed', community_id=str(post['community_id'])))

@community_bp.route('/posts/<post_id>/report', methods=['POST'])
def report_post(post_id):
    if 'user_id' not in session:
        flash('Please log in first.', 'danger')
        return redirect(url_for('fake_login'))
    db = get_db()
    user_id = session['user_id']
    post = db.posts.find_one({'_id': ObjectId(post_id)})
    if not post:
        flash('Post not found.', 'danger')
        return redirect(url_for('community.communities'))
    existing_report = db.reports.find_one({'post_id': ObjectId(post_id), 'reported_by': user_id})
    if existing_report:
        flash('You have already reported this post.', 'info')
        return redirect(url_for('community.community_feed', community_id=str(post['community_id'])))
    db.reports.insert_one({'post_id': ObjectId(post_id), 'reported_by': user_id,
                           'community_id': post['community_id'], 'reason': 'Reported by user',
                           'status': 'pending', 'created_at': datetime.utcnow()})
    flash('Post reported. Our admin will review it. 🚩', 'info')
    return redirect(url_for('community.community_feed', community_id=str(post['community_id'])))
