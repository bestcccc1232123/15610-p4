# -*- coding: utf-8 -*-
"""
    Flaskr
    ~~~~~~

    A microblog example application written as Flask tutorial with
    Flask and sqlite3.

    :copyright: (c) 2010 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
from __future__ import with_statement
from sqlite3 import dbapi2 as sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash, _app_ctx_stack
import os
from werkzeug import secure_filename
import time







# configuration
DATABASE = '/tmp/flaskr.db'
DEBUG = True
SECRET_KEY = 'development key'
USERNAME = 'admin'
PASSWORD = 'default'

VOTE_INTERVAL = 600
PATH_IMAGE = 'static/img/'
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])

SQL_SCHEMA = 'schema_p4.sql'
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'default'



# create our little application :)
commit_history_list = []
app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('FLASKR_SETTINGS', silent=True)


# user class for two phase commit
class Commit_User:
    uid = 0
    vote = False

    def __init__(self, user_id):
        self.uid = user_id;
        self.vote = False

    def user_verify(self):
        self.vote = True

    def user_clear(self):
        self.vote = False
    

# group class for two phase commit
class Commit_Group:
    gid = -1;
    user_list = []
    time_start = 0


    def __init__(self, group_id):
        self.gid = group_id;
        self.user_list = []
    
    def reset_vote(self):
        size = len(self.user_list)
        
        for i in range(0, size):
            self.user_list[i].user_clear()

        self.time_start = time.time()
        clear_vote_state(self.gid)

    def user_exist(self, user_id):
        
        for user in self.user_list:
            if user.uid == user_id:
                return True
        return False

    def add_new_user(self, user_id):
        if not self.user_exist(user_id):
            c = Commit_User(user_id);
            
            self.user_list.append(c)
        
            # clear all the users' commit history

            
    def add_new_image(self):
        self.reset_vote()

    def load_state(self, user_id):
        
        size = len(self.user_list)
        print "user_commit: (%d) users" % size
        for i in range(0, size):
            if self.user_list[i].uid == user_id:
                print "user_verify"
                self.user_list[i].user_verify()
                break
        else:
            return
        
    def user_commit(self, user_id):
        cur_time = time.time()
        
        if cur_time - self.time_start > VOTE_INTERVAL:
            self.cancel_vote()
        else:
            size = len(self.user_list)
            print "user_commit: (%d) users" % size
            for i in range(0, size):
                if self.user_list[i].uid == user_id:
                    print "user_verify"
                    self.user_list[i].user_verify()
                    save_vote_state(self.gid, user_id)
                    break
            else:
                return

            if self.is_all_commit():
                print "publish images"
                publish_images_for_group(self.gid)
                clear_vote_state(self.gid)
            # we will keep it in memory
            
    def cancel_vote(self):

        size = len(self.user_list)
        
        for i in range(0, size):
            self.user_list[i].user_clear()
        remove_private_images_for_group(self.gid)
        clear_vote_state(self.gid)
        



    def is_all_commit(self):
        size = len(self.user_list)
        
        for i in range(0, size):
            if self.user_list[i].vote == False:
                return False
        
        return True








def init_db():
    """Creates the database tables."""
    with app.app_context():
        db = get_db()
        with app.open_resource(SQL_SCHEMA) as f:
            db.cursor().executescript(f.read())
        db.commit()


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    top = _app_ctx_stack.top
    if not hasattr(top, 'sqlite_db'):
        sqlite_db = sqlite3.connect(app.config['DATABASE'])
        sqlite_db.row_factory = sqlite3.Row
        top.sqlite_db = sqlite_db

    return top.sqlite_db


@app.teardown_appcontext
def close_db_connection(exception):
    """Closes the database again at the end of the request."""
    top = _app_ctx_stack.top
    if hasattr(top, 'sqlite_db'):
        top.sqlite_db.close()


@app.route('/add', methods=['POST'])
def add_entry():
    if not session.get('logged_in'):
        abort(401)
    db = get_db()
    db.execute('insert into entries (title, text) values (?, ?)',
                 [request.form['title'], request.form['text']])
    db.commit()
    flash('New entry was successfully posted')
    return redirect(url_for('show_entries'))


@app.route('/userrefuse', methods=['POST'])
def user_refuse():
    c = get_commit_group(session['gid'])
    c.cancel_vote()
    return redirect(url_for('user_page'))


@app.route('/useragree', methods=['POST'])
def user_agree():
    
    c = get_commit_group(session['gid'])
    
    c.user_commit(session['uid'])
    return redirect(url_for('user_page'))

    

@app.route('/addgroup', methods=['GET', 'POST'])
def add_group():
    error = None
    if request.method == 'POST':
        print 'new group: ' + request.form['group_name'];
        print 'new group: ' + request.form['group_comment'];

        db = get_db()
        db.execute('insert into group_p4 (group_name, group_comment) '
                   'values (?,?)', 
                   [request.form['group_name'], request.form['group_comment']])
        db.commit()
                
        # no need to add group commit in memory, will be added later when used

    return redirect(url_for('manage_account'))


@app.route('/adduser', methods=['GET', 'POST'])
def add_user():
    error = None
    if request.method == 'POST':
        print 'new user: ' + request.form['user_name'];
        print 'new user pwd: ' + request.form['user_pwd'];
        print 'group for user:' + request.form['group_name'];

        #find the group 
        db = get_db()
        cur = db.execute('select id from group_p4 where group_name=?', 
                         [request.form['group_name']])
        groups = cur.fetchall()
        

        # insert the user 

        if (len(groups) == 1):
            for group in groups:
                db.execute('insert into user_p4 (gid, user_name, user_pwd) '
                           'values (?,?,?)',                   
                           [group['id'], request.form['user_name'], 
                            request.form['user_pwd']])
                db.commit()
                print 'group id:' + str(group['id']);                               
                c = get_commit_group(group['id'])
                users = get_user(request.form['user_name'])
                if len(users) == 1:
                    user = users[0]
                    c.add_new_user(user['id'])
        
    return redirect( url_for('manage_account') )



def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


def get_all_groups():
    db = get_db()
    cur = db.execute('select * from group_p4 order by id')
    groups = cur.fetchall()    
    return groups
    

    
def get_all_users():
    db = get_db()
    cur = db.execute('select * from user_p4 order by id')
    users = cur.fetchall()    
    return users
    
def get_user(user_name):
    db = get_db()
    cur = db.execute('select * from user_p4 where user_name=?',[user_name])
    users = cur.fetchall() 
    return users

def get_users_by_group(group_id):
    db = get_db()
    cur = db.execute('select * from user_p4 where gid=?', [group_id])
    users = cur.fetchall()
    return users

def get_private_images_for_group(gid):
    db = get_db()
    cur = db.execute('select * from image_p4 where gid=?', [gid])
    images = cur.fetchall()
    return images


def get_public_images_for_group(gid):
    db = get_db()
    cur = db.execute('select * from image_public_p4 where gid=?', [gid])
    images = cur.fetchall()

    return images



@app.route('/')
def bs_test():
    

    imagesList = dict()
    groups = get_all_groups()
    for group in groups:
        images = get_public_images_for_group(group['id'])
        if len(images) > 0:
            print "images exist"
        imagesList[group['group_name']]=images

    return render_template('index_tmp.html', groups=groups, 
                           imagesList=imagesList)


@app.route('/manageaccount')
def manage_account():
    if not session['isadmin']:
        return redirect(url_for('bs_test'))
    else:
        error = None
#        if request.method == 'POST':
            

        users = get_all_users()
        groups = get_all_groups()
        
        return render_template('manage_account.html', users = users,
                               groups = groups)


@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    error = None

    if not session['logged_in']:
        return redirect('/')
    elif session['isadmin']:
        return redirect('/')
    else:    
        if request.method == 'POST':            

            #find the user
            db = get_db()
            cur = db.execute('select id,gid from user_p4 where user_name=?', 
                         [session['username']])
            users = cur.fetchall()
            
            if (len(users) == 1):
                user = users[0]            

                # check and save the file into temporary private database
                file = request.files['file']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    pathname = os.path.join(app.config['PATH_IMAGE'], filename); 
                    file.save(pathname)
                    
                    print filename + ':' + pathname
                    #insert the image for current user
                    db.execute('insert into image_p4'
                               ' (gid, uid, image_name, image_path) values '
                               '(?,?,?,?)',
                           [user['gid'],user['id'],filename,pathname])
                    db.commit();
                    
                    # reset the commit history
                    c = get_commit_group(session['gid'])
                    c.add_new_image()
                    print "reach here !!"                
                return redirect(url_for('user_page'))


@app.route('/userpage')
def user_page():
    if not session['logged_in']:
        return redirect('/')
    elif session['isadmin']:
        return redirect('/')
    else:
        print "session gid:" + str(session['gid'])
        images = get_private_images_for_group(session['gid'])
        
        print str(os.urandom(24))
        return render_template('user_page.html', images = images)
    


""" for two phase commit """



    
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != app.config['USERNAME'] \
                or request.form['password'] != app.config['PASSWORD']:
            users = get_user(request.form['username'])
            if len(users) == 1:
                user = users[0]
                if user['user_pwd'] == request.form['password']:
                    session['logged_in'] = True
                    session['username'] = request.form['username']
                    session['password'] = request.form['password']
                    session['gid'] = user['gid']
                    session['uid'] = user['id']
                    if request.form['username'] == 'admin':
                        session['isadmin'] = True
                    else:
                        session['isadmin'] = False                    
        else:
            session['logged_in'] = True
            session['username'] = request.form['username']
            session['password'] = request.form['password']
            if request.form['username'] == 'admin':
                session['isadmin'] = True
            else:
                session['isadmin'] = False            
            return redirect(url_for('bs_test'))
        
    return redirect(url_for('bs_test'))

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('isadmin', None)
    return redirect(url_for('bs_test'))


# init commit history list based on current database
def init_commit_history():
    groups = get_all_groups()
    
    # for each group, add new bookkeeping for group
    for group in groups:
        images = get_private_images_for_group(group['id'])
        
        if len(images) != 0:
            c = Commit_Group(group['id'])
            users = get_users_by_group(group['id'])
            # for each user in the group, add user
            for user in users:
                u = c.add_new_user(user['id'])
            commit_history_list.append(c)
            

def load_vote_state(gid, uid):
    db = get_db()
    cur = db.execute('select * from vote_state_p4 where gid=? and uid=?',
               [gid, uid])
    votes = cur.fetchall()
    if len(votes) == 1:
        vote = votes[0]
        
        if vote['accept'] == 1:
            return True;
        else:
            return False;

    # no vote state, by default False
    return False


def save_vote_state(gid, uid):
    db = get_db()
    cur = db.execute('select * from vote_state_p4 where gid=? and uid=?',
               [gid, uid])
    votes = cur.fetchall()

    if len(votes) == 1:
        db.execute('update vote_state_p4 set accept=? where gid=? and uid=?',
                   [1, gid, uid])
        db.commit()
    else:
        #if the table is empty
        db.execute('insert into vote_state_p4 (gid, uid, accept) values (?,?,?)',
                   [1, gid, uid])
        db.commit()

def clear_vote_state(gid):
    db = get_db()
    db.execute('delete from vote_state_p4 where gid=?',[gid])
    db.commit()

# get Commit_Group class for a group
def get_commit_group(group_id):
    
    for c in commit_history_list:
        if c.gid == group_id:
            return c
    else:
        print "new group is added: gid="+str(group_id)
        c = Commit_Group(group_id)
        users = get_users_by_group(group_id)
        print "get_commit_group: %d users" % len(users)
        # for each user in the group, add user
        for user in users:
            u = c.add_new_user(user['id'])
            if load_vote_state(group_id, user['id']) == 1:
                # set vote state
                c.load_state(user['id'])
        commit_history_list.append(c)
        
        return c        

def remove_private_images_for_group(group_id):
    db = get_db()
    db.execute('delete from image_p4 where gid=?',[group_id])
    db.commit()


# move images belonging to a group from private db to public db
def publish_images_for_group(group_id):
    
    images = get_private_images_for_group(group_id)        

    db = get_db()
    for image in images:
        db.execute('insert into image_public_p4'
                   ' (gid, uid, image_name, image_path) values '
                   '(?,?,?,?)',
                   [image['gid'], image['uid'],image['image_name'],
                    image['image_path']])

    db.execute('delete from image_p4 where gid=?',[group_id])
    db.commit()

    
    


if __name__ == '__main__':
    #init db once
    #init_db()
    #    init_commit_history()
    app.run(host='0.0.0.0')
