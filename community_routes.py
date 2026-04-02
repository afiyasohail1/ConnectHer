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
    all_communities = list(db.communities.find({'status': 'active'}))
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
    is_community_creator = community.get('created_by') == user_id
    is_site_admin = session.get('is_admin', False)
    return render_template('community_feed.html', community=community, posts=posts,
                           member_count=member_count, session_user_id=user_id,
                           session_username=session.get('username') or session.get('user', {}).get('name', 'You'),
                           is_community_creator=is_community_creator,
                           is_site_admin=is_site_admin
    )
@community_bp.route('/communities/<community_id>/post', methods=['POST'])
def create_post(community_id):
    if 'user_id' not in session:
        flash('Please log in first.', 'danger')
        return redirect(url_for('fake_login'))
    db = get_db()
    user_id = session['user_id']
    username = session.get('username') or session.get('user', {}).get('name', 'Anonymous')
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
    username = session.get('username') or session.get('user', {}).get('name', 'Anonymous')
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


# ---------------------------------------------------------------------------
# Create Community page — GET shows form, POST submits it
# Users: status = 'pending' (needs admin approval)
# Admins: status = 'active' (goes live immediately)
# Route: GET+POST /communities/create
# ---------------------------------------------------------------------------
@community_bp.route('/communities/create', methods=['GET', 'POST'])
def create_community():
    if 'user_id' not in session:
        flash('Please log in first.', 'danger')
        return redirect(url_for('fake_login'))

    db = get_db()
    user_id  = session['user_id']
    is_admin = session.get('is_admin', False)

    if request.method == 'POST':
        name        = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        icon        = request.form.get('icon', '🌸')
        color       = request.form.get('color', '#A680B8')
        image_url   = None

        # Validate required fields
        if not name or not description:
            flash('Name and description are required.', 'danger')
            return redirect(url_for('community.create_community'))

        # Check for duplicate name
        existing = db.communities.find_one({'name': {'$regex': f'^{name}$', '$options': 'i'}})
        if existing:
            flash('A community with that name already exists.', 'danger')
            return redirect(url_for('community.create_community'))

        # Handle optional image upload
        image_file = request.files.get('image')
        if image_file and image_file.filename:
            allowed = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
            ext = image_file.filename.rsplit('.', 1)[-1].lower()
            if ext not in allowed:
                flash('Invalid image format. Use PNG, JPG, GIF or WEBP.', 'danger')
                return redirect(url_for('community.create_community'))
            upload_folder = os.path.join('static', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            filename  = f"community_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{image_file.filename}"
            image_file.save(os.path.join(upload_folder, filename))
            image_url = f"/static/uploads/{filename}"

        # Status depends on who is creating
        status = 'active' 

        db.communities.insert_one({
            'name':            name,
            'description':     description,
            'icon':            icon,
            'color':           color,
            'image_url':       image_url,
            'status':          status,
            'created_by':      user_id,
            'created_by_name': session.get('username', 'Unknown'),
            'created_at':      datetime.utcnow(),
            'member_count':    0
        })

        
        flash(f'Your community "{name}" is now live! 🌸', 'success')
        return redirect(url_for('community.communities'))

    return render_template('create_community.html', is_admin=is_admin)
    


# ---------------------------------------------------------------------------
# Admin: View pending communities
# Route: GET /admin/communities/pending
# ---------------------------------------------------------------------------
@community_bp.route('/admin/communities/pending')
def pending_communities():
    if 'user_id' not in session:
        flash('Please log in first.', 'danger')
        return redirect(url_for('fake_login'))
    if not session.get('is_admin', False):
        flash('Admin access only.', 'danger')
        return redirect(url_for('community.communities'))

    db = get_db()
    pending = list(db.communities.find({'status': 'pending'}).sort('created_at', -1))
    return render_template('pending_communities.html', pending=pending)


# ---------------------------------------------------------------------------
# Admin: Approve a pending community
# Route: POST /admin/communities/<community_id>/approve
# ---------------------------------------------------------------------------
@community_bp.route('/admin/communities/<community_id>/approve', methods=['POST'])
def approve_community(community_id):
    if 'user_id' not in session or not session.get('is_admin', False):
        flash('Admin access only.', 'danger')
        return redirect(url_for('community.communities'))

    db = get_db()
    db.communities.update_one(
        {'_id': ObjectId(community_id)},
        {'$set': {'status': 'active', 'approved_at': datetime.utcnow()}}
    )
    flash('Community approved and is now live! ✓', 'success')
    return redirect(url_for('community.pending_communities'))


# ---------------------------------------------------------------------------
# Admin: Reject a pending community
# Route: POST /admin/communities/<community_id>/reject
# ---------------------------------------------------------------------------
@community_bp.route('/admin/communities/<community_id>/reject', methods=['POST'])
def reject_community(community_id):
    if 'user_id' not in session or not session.get('is_admin', False):
        flash('Admin access only.', 'danger')
        return redirect(url_for('community.communities'))

    db = get_db()
    db.communities.delete_one({'_id': ObjectId(community_id)})
    flash('Community request rejected and removed.', 'info')
    return redirect(url_for('community.pending_communities'))



@community_bp.route('/admin/posts/<post_id>/delete', methods=['POST'])
def admin_delete_post(post_id):
    if 'user_id' not in session:
        flash('Please log in first.', 'danger')
        return redirect(url_for('fake_login'))

    db = get_db()
    user_id = session['user_id']
    post = db.posts.find_one({'_id': ObjectId(post_id)})
    if not post:
        flash('Post not found.', 'danger')
        return redirect(url_for('community.communities'))

    # Only the community creator or site admin can remove posts
    community = db.communities.find_one({'_id': post['community_id']})
    if not community or (community.get('created_by') != user_id and not session.get('is_admin', False)):
        flash('Only the community creator or an admin can remove posts.', 'danger')
        return redirect(url_for('community.community_feed', community_id=str(post['community_id'])))

    community_id = str(post['community_id'])
    db.posts.delete_one({'_id': ObjectId(post_id)})
    flash('Post removed. 🛡️', 'info')
    return redirect(url_for('community.community_feed', community_id=community_id))


# ---------------------------------------------------------------------------
# Community Creator: Remove a user from their community
# Route: POST /admin/communities/<community_id>/remove-user/<user_id>
# ---------------------------------------------------------------------------
@community_bp.route('/admin/communities/<community_id>/remove-user/<user_id>', methods=['POST'])
def admin_remove_user(community_id, user_id):
    if 'user_id' not in session:
        flash('Please log in first.', 'danger')
        return redirect(url_for('fake_login'))

    db = get_db()
    current_user_id = session['user_id']

    # Only the community creator or site admin can remove members
    community = db.communities.find_one({'_id': ObjectId(community_id)})
    if not community or (community.get('created_by') != current_user_id and not session.get('is_admin', False)):
        flash('Only the community creator or an admin can remove members.', 'danger')
        return redirect(url_for('community.community_feed', community_id=community_id))

    result = db.memberships.delete_one({
        'user_id': user_id,
        'community_id': ObjectId(community_id)
    })

    if result.deleted_count == 0:
        flash('User was not a member of this community.', 'info')
    else:
        flash('User removed from community. 🛡️', 'info')

    return redirect(url_for('community.community_feed', community_id=community_id))

