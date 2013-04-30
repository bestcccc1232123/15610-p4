# -*- coding: utf-8 -*-
"""
    Flaskg
    ~~~~~~

    for 15610 project 4
    
    by app.run() it is single threaded, no need to worry about locks
    
    :copyright: (c) 2013 by Chen Chen.
    :license: BSD, see LICENSE for more details.
"""

from __future__ import with_statement
from sqlite3 import dbapi2 as sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash, _app_ctx_stack
import os
import urllib2
import base64
from werkzeug import secure_filename
import time

# configuration
DATABASE = '/tmp/flaskr.db'
DEBUG = True
SECRET_KEY = 'development key'
USERNAME = 'admin'
PASSWORD = 'default'

LEN_RAND_ID = 32


VOTE_INTERVAL = 3
PATH_IMAGE = 'static/img/'
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])

SQL_SCHEMA = 'schema_g.sql'



# create our little application :)

app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('FLASKR_SETTINGS', silent=True)


"""
        Functions for db 
"""

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


def load_event(event_name):
    db = get_db()
    cur = db.execute('select * from event_g where event_name=?',
                     [event_name])
    events = cur.fetchall()
    
    if len(events) == 1:
        return event[0]
    elif len(events) > 1:
        raise Error_g('more than one events')
    else:
        return None

def load_event_from_eid(eid):
    db = get_db()
    cur = db.execute('select * from event_g where eid=?',
                     [eid])
    events = cur.fetchall()
    
    if len(events) == 1:
        return events[0]
    elif len(events) > 1:
        raise Error_g('more than one events')
    else:
        return None

def save_event(db, e):

    db.execute('insert into event_g (eid, event_name) values (?,?)',
               [e.eid, e.event_name])



def load_users_for_event(eid):
    db = get_db()
    cur = db.execute('select * from event_user_rel_g where eid=?',[eid])
    users_db = cur.fetchall()

    users = []
    for user_db in users_db:
        user = dict()
        user['uid'] = user_db['uid']
        users.append(user)

    return users

    
def load_uncommit_images_for_event(eid):
    db = get_db()
    cur = db.execute('select * from uncommit_image_g where eid=?',[eid])
    images_db = cur.fetchall()

    images = []

    for image_db in images_db:
        image = dict()
        image['eid'] = image_db['eid']
        image['uid'] = image_db['uid']
        image['image_name'] = image_db['image_name']
        image['image_path'] = image_db['image_path']
        images.append(image)


    return images

    
def load_commit_images_for_event(eid):
    db = get_db()
    cur = db.execute('select * from commit_image_g where eid=?',[eid])
    images_db = cur.fetchall()
    images = []

    for image_db in images_db:
        image = dict()
        image['eid'] = image_db['eid']
        image['uid'] = image_db['uid']
        image['image_name'] = image_db['image_name']
        image['image_path'] = image_db['image_path']
        images.append(image)

    return images

def load_vote_states_for_event(eid):
    db = get_db()
    cur = db.execute('select * from vote_state_g where eid=?',[eid])
    votes_db = cur.fetchall()

    votes = []
    for vote_db in votes_db:
        vote = dict()
        vote['eid'] = vote_db['eid']
        vote['uid'] = vote_db['uid']
        vote['accept'] = vote_db['accept']
        votes.append(vote)
    return votes
    
    
def restore_event(event_db):
    e = Event_g(event_db['event_name'])
    e.eid = event_db['eid']
    e.uncommit_images = load_uncommit_images_for_event(e.eid)
    e.commit_images = load_commit_images_for_event(e.eid)
    e.users = load_users_for_event(e.eid)
    e.vote_states = load_vote_states_for_event(e.eid)
    return e


def get_random_id():
    return base64.urlsafe_b64encode(os.urandom(LEN_RAND_ID))


class Error_g(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class EventManager_g:
    events = []               # list of class Event_g
    

    def __init__(self):
        self.events = []

    def get_all_events(self):
        return self.events
    
    def get_event_from_name(self, event_name):
        
        for event in self.events:
            if event.event_name == event_name:
                return event
        else:
            # try to load event from database
            event_db = load_event(event_name)
            if event_db is None:
                return None
            else:
                # restore the event from database
                event = restore_event(event_db)
                # save event in memory
                self.events.append(event)
                return event

    def get_event_from_eid(self, eid):
        
        for event in self.events:
            if event.eid == eid:
                return event
        else:
            print "reach here"
            # try to load event from database
            event_db = load_event_from_eid(eid)
            if event_db is None:
                print "find no event"
                return None
            else:
                # restore the event from database
                event = restore_event(event_db)
                # save event in memory
                self.events.append(event)
                return event


    def add_event(self, event_name):
        e = Event_g(event_name)
        self.events.append(e)
        db = get_db()
        save_event(db, e)
        db.commit()

        return e

def save_new_user(db, eid, uid):
    
    # TODO: check whether user already exists
    db.execute('insert into user_g (uid) values (?)', [uid])
    db.execute('insert into event_user_rel_g (uid, eid) values (?,?)',
               [uid, eid])


def save_vote_state(db, eid, vote_states):
    db.execute('delete from vote_state_g where eid=?',
               [ eid ])
    for state in vote_states:
        db.execute('insert into vote_state_g (eid,uid,accept) values (?,?,?)',
                   [ state['eid'], state['uid'], state['accept'] ])


def update_vote_state(db, eid, uid, accept):
    db.execute('update vote_state_g set accept=? where eid=? and uid=?',
               [accept, eid, uid])
    
        
def delete_uncommit_images_for_event(db, eid):
    db.execute('delete from uncommit_image_g where eid = ?',
               [eid])

def save_new_uncommit_image(db, eid, uid, image_name, image_path):
    db.execute('insert into uncommit_image_g (eid, uid, image_name, image_path) values (?,?,?,?)', [eid, uid, image_name, image_path])
    
               
def save_commit_image_for_event(db, eid):
    cur = db.execute('select * from uncommit_image_g where eid = ?', [eid])
    images = cur.fetchall()
    db.execute('delete from uncommit_image_g where eid = ?', [eid])
    for image in images:
        db.execute('insert into commit_image_g (eid, uid, image_name, image_path) values (?,?,?,?)', [image['eid'], image['uid'], image['image_name'], image['image_path']])
    

class Event_g:

    def __init__(self,event_name):
        self.event_name = event_name
        self.uncommit_images = []
        self.commit_images = []
        self.users = []
        self.vote_states = []
        self.eid = get_random_id()
        self.info = None
        self.time_start = -1

    def clear_vote_state(self):
        for vote in self.vote_states:
            vote['accept'] = 0
        
    def add_vote_state(self, uid):
        vote = dict()
        vote['eid'] = self.eid
        vote['uid'] = uid
        vote['accept'] = 0
        self.vote_states.append(vote)
    

    def add_new_user(self, uid):
        user = dict()
        user['uid'] = uid
        self.users.append(user)
        self.clear_vote_state()
        self.add_vote_state(uid)
        # I would like following two within same commit
        db = get_db()        
        save_new_user(db, self.eid, uid)
        save_vote_state(db, self.eid, self.vote_states)
        db.commit()

    def add_new_image(self, uid, image_name, image_path):
        image = dict()
        image['uid'] = uid
        image['eid'] = self.eid
        image['image_name'] = image_name
        image['image_path'] = image_path
        
        self.uncommit_images.append(image)
        
        db = get_db()
        save_new_uncommit_image(db, self.eid, uid, image_name, image_path)
        db.commit()
        
        self.reset_timer()

    def _commit_images(self, db):
        self.commit_images = self.commit_images + self.uncommit_images
        self.uncommit_images = []
        save_commit_image_for_event(db, self.eid)

        
    def agree(self, uid):
        if not self.does_timeout():
            for vote in self.vote_states:
                if vote['uid'] == uid:
                    print "find vote"
                    vote['accept'] = 1
                    if self.all_accept():
                        print "all users have accepted"
                        self.clear_vote_state()
                        db = get_db()
                        self._commit_images(db)
                        save_vote_state(db, self.eid, self.vote_states)
                        db.commit()
                        self.stop_timer()
                        self.info = 'Photos have been successfully committed'
                    else:
                        db = get_db()
                        update_vote_state(db, self.eid, uid, 1)
                        db.commit()
                break
            #else:
            #   raise exception no such user
        
    def refuse(self, uid):
        if not self.does_timeout():
            self.clear_vote_state()
            self.uncommit_images = []
            db = get_db()
            save_vote_state(db, self.eid, self.vote_states)
            delete_uncommit_images_for_event(db, self.eid)
            db.commit()
            self.stop_timer()
            self.info = 'One of the users refuse to commit the photos, abort'
            
            
    def does_timeout(self):
        time_now = time.time()
        if self.time_start > 0 and time_now - self.time_start  > VOTE_INTERVAL:
            self.info = 'Timeout, abort'
            self.clear_vote_state()
            self.uncommit_images = []
            db = get_db()
            save_vote_state(db, self.eid, self.vote_states)
            delete_uncommit_images_for_event(db, self.eid)
            db.commit()
            return True
        else:
            return False
    
    def reset_timer(self):
        self.time_start = time.time()

    def stop_timer(self):
        self.time_start = -1 # time_start < 0 when timer is stopped


    # return True if all current user accept
    def all_accept(self):
        for vote in self.vote_states:
            if vote['accept'] != 1:
                print "return False"
                return False
        else:
            print "return True"
            return True



evt_mgr = EventManager_g()


# it seems allowing anyone to create event will cause DoS attack
@app.route('/', methods = ['GET', 'POST'])
def create_event():
    
    event_url = None
    err_info = None

    display_info = dict()
    if request.method == 'POST':
        e = evt_mgr.get_event_from_name(request.form['event_name'])

        if not e:
            e = evt_mgr.add_event(request.form['event_name'])            
            display_info['event_url'] = 'event/' + e.eid
            print event_url
        else:
            display_info['err_info'] = 'Group Name already exists'            
            
    return render_template('index_g.html', info=display_info)


@app.route('/event/<eid>', methods = ['GET', 'POST'])
def display_event(eid):
    print eid
    e = evt_mgr.get_event_from_eid(eid)
    if e is None:
        return redirect(url_for('create_event'))

    if not session.get('uid_g'):
        print 'this is executed'
        uid = get_random_id()
        session['uid_g'] = uid
        session['eid'] = eid
        e.add_new_user(uid)
    elif not session.get('eid') or session['eid'] != eid:
        # this user must be involved in another event
        print "create new session eid"
        uid = session['uid_g']
        session['eid'] = eid
        e.add_new_user(uid)
    else:
        # returned user
        pass

    print e.eid
    print e.uncommit_images
    msg = e.info
    e.info = None
    return render_template('event_tmpl.html', event=e, msg=msg)




def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


@app.route('/uploadimage', methods = ['POST'])
def upload_image():
    if request.method == 'POST':
        
        e = evt_mgr.get_event_from_eid(session['eid'])
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            pathname = os.path.join(app.config['PATH_IMAGE'], filename); 
            file.save(pathname)
            
            print filename + ':' + pathname

            e.add_new_image(session['uid_g'], filename, pathname)
    return redirect(url_for('display_event', eid = session['eid']))


@app.route('/accept', methods=['POST'])
def accept():
    if request.method == 'POST':
        e = evt_mgr.get_event_from_eid(session['eid'])
        e.agree(session['uid_g'])
    return redirect(url_for('display_event', eid = session['eid']))

@app.route('/refuse', methods=['POST'])
def refuse():
    if request.method == 'POST':
        e = evt_mgr.get_event_from_eid(session['eid'])
        e.refuse(session['uid_g'])
    return redirect(url_for('display_event', eid = session['eid']))



@app.route('/display', methods=['GET'])
def display():
    events = evt_mgr.get_all_events()
    
    return render_template('gallery_g.html', events=events)

@app.route('/debug', methods=['GET'])
def display_debug():
    events = evt_mgr.get_all_events()
    return render_template('debug_g.html', events = events)



if __name__ == '__main__':
    #init_db()
    app.run(host='0.0.0.0')


