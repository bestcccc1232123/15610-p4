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








# configuration
DATABASE = '/tmp/flaskr.db'
DEBUG = True
SECRET_KEY = 'development key'
USERNAME = 'admin'
PASSWORD = 'default'


PATH_IMAGE = 'upload_images/'
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])

SQL_SCHEMA = 'schema_p4.sql'
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'default'



# create our little application :)
app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('FLASKR_SETTINGS', silent=True)


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
    return redirect( url_for('manage_account') )



def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENIONS

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    error = None
    if request.method == 'POST':
        
        # check whether user is correct
        
        #find the user
        db = get_db()
        cur = db.execute('select id,gid from user_p4 where user_name=?', 
                         [request.form['user_name']])
        users = cur.fetchall()
        
        if (len(users) == 1):
            user = users[0]            
           
            # check and save the file
            file = request.files['file']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                pathname = os.path.join(app.config['PATH_IMAGE'], filename); 
                file.save(pathname)
                
                #insert the image for current user
                db.execute('insert into image_p4'
                           ' (gid, uid, image_name, image_path) values '
                           '(?,?,?,?)',
                           [user['id'],user['gid'],filename,pathname])
                db.commit();

    return render_template('upload_image.html',error=error);


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


@app.route('/')
def bs_test():
    return render_template('index_tmp.html')

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
    return render_template('index_tmp.html', error=error)

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
    

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('isadmin', None)
    return render_template('index_tmp.html')


if __name__ == '__main__':
    #init db once
    #init_db()
    app.run()
