from flask import Blueprint, render_template, redirect, url_for, flash, session, request
from bson.objectid import ObjectId
from datetime import datetime
import os

items_bp = Blueprint('items', __name__)

def get_db():
    from app import mongo
    return mongo.db


# ---------------------------------------------------------------------------
# View all items
# Route: GET /items
# ---------------------------------------------------------------------------
@items_bp.route('/items')
def items():
    if 'user_id' not in session:
        flash('Please log in first.', 'danger')
        return redirect(url_for('login'))

    db = get_db()
    user_id = session['user_id']

    # All items
    all_items = list(db.items.find().sort('created_at', -1))

    # My borrow requests
    my_requests = list(db.borrow_requests.find({'requester_id': user_id}).sort('created_at', -1))

    # Attach item info to each request
    for req in my_requests:
        item = db.items.find_one({'_id': req['item_id']})
        if item:
            req['item_name']  = item.get('name', 'Unknown Item')
            req['item_image'] = item.get('image_url')
            req['owner_name'] = item.get('owner_name', 'Unknown')
        else:
            req['item_name']  = 'Item no longer available'
            req['item_image'] = None
            req['owner_name'] = 'Unknown'

    
    # IDs of items the user has already requested
    requested_ids = {
        str(r['item_id']) for r in db.borrow_requests.find({
        'requester_id': user_id,
        'status': {'$in': ['pending', 'approved']}
        })
    }

    return render_template('items.html',
                       items=all_items,
                       my_requests=my_requests,
                       requested_ids=requested_ids,
                       session_user_id=user_id)


# ---------------------------------------------------------------------------
# Post a new item (GET = show form, POST = submit)
# Route: GET+POST /items/post
# ---------------------------------------------------------------------------
@items_bp.route('/items/post', methods=['GET', 'POST'])
def post_item():
    if 'user_id' not in session:
        flash('Please log in first.', 'danger')
        return redirect(url_for('login'))

    db = get_db()
    user_id  = session['user_id']
    username = session.get('username') or session.get('user', {}).get('name', 'Anonymous')

    if request.method == 'POST':
        name        = request.form.get('name', '').strip()
        category    = request.form.get('category', '').strip()
        description = request.form.get('description', '').strip()
        image_url   = None

        if not name or not category or not description:
            flash('All fields are required.', 'danger')
            return redirect(url_for('items.post_item'))

        # Handle optional image
        image_file = request.files.get('image')
        if image_file and image_file.filename:
            allowed = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
            ext = image_file.filename.rsplit('.', 1)[-1].lower()
            if ext not in allowed:
                flash('Invalid image format.', 'danger')
                return redirect(url_for('items.post_item'))
            upload_folder = os.path.join('static', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            filename  = f"item_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{image_file.filename}"
            image_file.save(os.path.join(upload_folder, filename))
            image_url = f"/static/uploads/{filename}"

        db.items.insert_one({
            'name':        name,
            'category':    category,
            'description': description,
            'image_url':   image_url,
            'owner_id':    user_id,
            'owner_name':  username,
            'status':      'available',
            'created_at':  datetime.utcnow()
        })

        flash(f'"{name}" has been listed for sharing! 🌸', 'success')
        return redirect(url_for('items.items'))

    return render_template('post_item.html')


# ---------------------------------------------------------------------------
# Request to borrow an item
# Route: POST /items/<item_id>/request
# ---------------------------------------------------------------------------
@items_bp.route('/items/<item_id>/request', methods=['POST'])
def request_item(item_id):
    if 'user_id' not in session:
        flash('Please log in first.', 'danger')
        return redirect(url_for('login'))

    db = get_db()
    user_id  = session['user_id']
    username = session.get('username') or session.get('user', {}).get('name', 'Anonymous')

    item = db.items.find_one({'_id': ObjectId(item_id)})
    if not item:
        flash('Item not found.', 'danger')
        return redirect(url_for('items.items'))

    # Check if item is available
    if item.get('status') != 'available':
        flash('This item is currently unavailable.', 'danger')
        return redirect(url_for('items.items'))

    # Can't borrow your own item
    if item['owner_id'] == user_id:
        flash("You can't borrow your own item.", 'info')
        return redirect(url_for('items.items'))

    # Check if already requested
    existing = db.borrow_requests.find_one({
        'item_id':      ObjectId(item_id),
        'requester_id': user_id,
        'status':       {'$in': ['pending', 'approved']}
    })
    if existing:
        flash('You have already requested this item.', 'info')
        return redirect(url_for('items.items'))

    db.borrow_requests.insert_one({
        'item_id':        ObjectId(item_id),
        'requester_id':   user_id,
        'requester_name': username,
        'owner_id':       item['owner_id'],
        'status':         'pending',
        'created_at':     datetime.utcnow()
    })

    flash(f'Borrow request sent for "{item["name"]}"! 🌸', 'success')
    return redirect(url_for('items.items'))


# ---------------------------------------------------------------------------
# View borrow requests for an item (lender view)
# Route: GET /items/<item_id>/requests
# ---------------------------------------------------------------------------
@items_bp.route('/items/<item_id>/requests')
def item_requests(item_id):
    if 'user_id' not in session:
        flash('Please log in first.', 'danger')
        return redirect(url_for('login'))

    db = get_db()
    user_id = session['user_id']

    item = db.items.find_one({'_id': ObjectId(item_id)})
    if not item:
        flash('Item not found.', 'danger')
        return redirect(url_for('items.items'))

    # Only the owner can view requests
    if item['owner_id'] != user_id:
        flash('You can only view requests for your own items.', 'danger')
        return redirect(url_for('items.items'))

    requests = list(db.borrow_requests.find(
        {'item_id': ObjectId(item_id)}
    ).sort('created_at', -1))

    return render_template('item_requests.html', item=item, requests=requests)


# ---------------------------------------------------------------------------
# Approve a borrow request
# Route: POST /items/requests/<request_id>/approve
# ---------------------------------------------------------------------------
@items_bp.route('/items/requests/<request_id>/approve', methods=['POST'])
def approve_request(request_id):
    if 'user_id' not in session:
        flash('Please log in first.', 'danger')
        return redirect(url_for('login'))

    db = get_db()
    user_id = session['user_id']

    req = db.borrow_requests.find_one({'_id': ObjectId(request_id)})
    if not req:
        flash('Request not found.', 'danger')
        return redirect(url_for('items.items'))

    # Only owner can approve
    if req['owner_id'] != user_id:
        flash('Only the item owner can approve requests.', 'danger')
        return redirect(url_for('items.items'))

    # Approve this request
    db.borrow_requests.update_one(
        {'_id': ObjectId(request_id)},
        {'$set': {'status': 'approved', 'approved_at': datetime.utcnow()}}
    )

    # Reject all other pending requests for the same item
    db.borrow_requests.update_many(
        {'item_id': req['item_id'], '_id': {'$ne': ObjectId(request_id)}, 'status': 'pending'},
        {'$set': {'status': 'rejected'}}
    )

    # Mark item as borrowed
    db.items.update_one(
        {'_id': req['item_id']},
        {'$set': {'status': 'borrowed', 'borrowed_by': req['requester_id']}}
    )

    flash('Request approved! Item marked as borrowed. ✓', 'success')
    return redirect(url_for('items.item_requests', item_id=str(req['item_id'])))


# ---------------------------------------------------------------------------
# Reject a borrow request
# Route: POST /items/requests/<request_id>/reject
# ---------------------------------------------------------------------------
@items_bp.route('/items/requests/<request_id>/reject', methods=['POST'])
def reject_request(request_id):
    if 'user_id' not in session:
        flash('Please log in first.', 'danger')
        return redirect(url_for('login'))

    db = get_db()
    user_id = session['user_id']

    req = db.borrow_requests.find_one({'_id': ObjectId(request_id)})
    if not req:
        flash('Request not found.', 'danger')
        return redirect(url_for('items.items'))

    if req['owner_id'] != user_id:
        flash('Only the item owner can reject requests.', 'danger')
        return redirect(url_for('items.items'))

    db.borrow_requests.update_one(
        {'_id': ObjectId(request_id)},
        {'$set': {'status': 'rejected'}}
    )

    flash('Request rejected.', 'info')
    return redirect(url_for('items.item_requests', item_id=str(req['item_id'])))


# ---------------------------------------------------------------------------
# Cancel a borrow request (borrower action)
# Route: POST /items/requests/<request_id>/cancel
# ---------------------------------------------------------------------------
@items_bp.route('/items/requests/<request_id>/cancel', methods=['POST'])
def cancel_request(request_id):
    if 'user_id' not in session:
        flash('Please log in first.', 'danger')
        return redirect(url_for('login'))

    db = get_db()
    user_id = session['user_id']

    req = db.borrow_requests.find_one({'_id': ObjectId(request_id)})
    if not req:
        flash('Request not found.', 'danger')
        return redirect(url_for('items.items'))

    if req['requester_id'] != user_id:
        flash('Only the borrower can cancel their request.', 'danger')
        return redirect(url_for('items.items'))

    if req.get('status') != 'pending':
        flash('Only pending requests can be cancelled.', 'info')
        return redirect(url_for('items.items'))

    db.borrow_requests.update_one(
        {'_id': ObjectId(request_id)},
        {'$set': {'status': 'cancelled', 'cancelled_at': datetime.utcnow()}}
    )

    flash('Borrow request cancelled.', 'info')
    return redirect(url_for('items.items'))


# ---------------------------------------------------------------------------
# Mark item as returned (borrower action)
# Route: POST /items/requests/<request_id>/return
# ---------------------------------------------------------------------------
@items_bp.route('/items/requests/<request_id>/return', methods=['POST'])
def return_item(request_id):
    if 'user_id' not in session:
        flash('Please log in first.', 'danger')
        return redirect(url_for('login'))

    db = get_db()
    user_id = session['user_id']

    req = db.borrow_requests.find_one({'_id': ObjectId(request_id)})
    if not req:
        flash('Request not found.', 'danger')
        return redirect(url_for('items.items'))

    if req['requester_id'] != user_id:
        flash('Only the borrower can mark an item as returned.', 'danger')
        return redirect(url_for('items.items'))

    # Update request status
    db.borrow_requests.update_one(
        {'_id': ObjectId(request_id)},
        {'$set': {'status': 'returned', 'returned_at': datetime.utcnow()}}
    )

    # Mark item as available again
    db.items.update_one(
        {'_id': req['item_id']},
        {'$set': {'status': 'available', 'borrowed_by': None}}
    )

    flash('Item marked as returned! Thank you 🌸', 'success')
    return redirect(url_for('items.items'))


# ---------------------------------------------------------------------------
# Delete an item listing (owner only)
# Route: POST /items/<item_id>/delete
# ---------------------------------------------------------------------------
@items_bp.route('/items/<item_id>/delete', methods=['POST'])
def delete_item(item_id):
    if 'user_id' not in session:
        flash('Please log in first.', 'danger')
        return redirect(url_for('login'))

    db = get_db()
    user_id = session['user_id']

    item = db.items.find_one({'_id': ObjectId(item_id)})
    if not item:
        flash('Item not found.', 'danger')
        return redirect(url_for('items.items'))

    if item['owner_id'] != user_id:
        flash('You can only delete your own items.', 'danger')
        return redirect(url_for('items.items'))

    if item.get('status') == 'borrowed':
        flash('Cannot delete an item that is currently borrowed.', 'danger')
        return redirect(url_for('items.items'))

    # Delete item and its requests
    db.items.delete_one({'_id': ObjectId(item_id)})
    db.borrow_requests.delete_many({'item_id': ObjectId(item_id)})

    flash('Item removed from listings.', 'info')
    return redirect(url_for('items.items'))



# ---------------------------------------------------------------------------
# Edit an item listing (owner only)
# Route: GET+POST /items/<item_id>/edit
# ---------------------------------------------------------------------------
@items_bp.route('/items/<item_id>/edit', methods=['GET', 'POST'])
def edit_item(item_id):
    if 'user_id' not in session:
        flash('Please log in first.', 'danger')
        return redirect(url_for('login'))

    db = get_db()
    user_id = session['user_id']

    item = db.items.find_one({'_id': ObjectId(item_id)})
    if not item:
        flash('Item not found.', 'danger')
        return redirect(url_for('items.items'))

    if item['owner_id'] != user_id:
        flash('You can only edit your own items.', 'danger')
        return redirect(url_for('items.items'))

    if request.method == 'POST':
        name        = request.form.get('name', '').strip()
        category    = request.form.get('category', '').strip()
        description = request.form.get('description', '').strip()
        remove_image = request.form.get('remove_image', '0')

        if not name or not category or not description:
            flash('All fields are required.', 'danger')
            return redirect(url_for('items.edit_item', item_id=item_id))

        # Start with existing image
        image_url = item.get('image_url')

        # Remove image if user clicked Remove
        if remove_image == '1':
            image_url = None

        # Handle new image upload
        image_file = request.files.get('image')
        if image_file and image_file.filename:
            allowed = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
            ext = image_file.filename.rsplit('.', 1)[-1].lower()
            if ext not in allowed:
                flash('Invalid image format.', 'danger')
                return redirect(url_for('items.edit_item', item_id=item_id))
            upload_folder = os.path.join('static', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            filename  = f"item_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{image_file.filename}"
            image_file.save(os.path.join(upload_folder, filename))
            image_url = f"/static/uploads/{filename}"

        db.items.update_one(
            {'_id': ObjectId(item_id)},
            {'$set': {
                'name':        name,
                'category':    category,
                'description': description,
                'image_url':   image_url,
                'updated_at':  datetime.utcnow()
            }}
        )

        flash('Item updated successfully! ✏️', 'success')
        return redirect(url_for('items.items'))

    return render_template('edit_item.html', item=item)
