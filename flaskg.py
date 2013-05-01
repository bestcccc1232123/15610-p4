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
import sys
import urllib2
import base64
from werkzeug import secure_filename
import time
import requests
import codecs

# configuration
DATABASE = '/tmp/flaskr.db'
DEBUG = True
SECRET_KEY = 'development key'
USERNAME = 'admin'
PASSWORD = 'default'

LEN_RAND_ID = 32


VOTE_INTERVAL = 6000
PATH_IMAGE = 'static/img'
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

    db.execute('insert into event_g '
               '(eid, event_name, master, is_commit) values (?,?,?,?)',
               [e.eid, e.event_name, e.master, e.is_commit])

def commit_event(db, e):
    db.execute('update event_g set is_commit=? where eid=?',
               [1, e.eid])

def rollback_event(db, e):
    db.execute('delete from event_g where eid=?',[e.eid])


def commit_image(db, iid):
    db.execute('update uncommit_image_g set is_commit=? where iid = ?',
               [1, iid])

def rollback_image(db, iid):
    db.execute('delete from uncommit_image_g where iid = ?',
               [iid])


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
        image['is_commit'] = image_db['is_commit']
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
    e.event_name = event_db['eid']
    e.master = event_db['eid']
    e.is_commit = event_db['eid']


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
    
    
    def __init__(self):
        self.events = []
        self.ip = None
        self.port = 0
        self.url = None


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


    def add_event_master(self, event_name):
        e = Event_g(event_name)
        e.set_master(self.url)

        self.events.append(e)
        
        db = get_db()
        save_event(db, e)        
        db.commit()
               
        if self.send_prepare_event(e):
            # all instances successfully returns
            if self.send_commit_event(e):
                e.is_commit = 1;
                db = get_db()
                commit_event(db,e)
                db.commit()
                
            else:
                # should repeat the commit packet
                raise Exception
        else:
            if self.send_rollback_event(e):
                db = get_db()
                rollback_event(db, e)
                db.commit()
            else:
                raise Exception
            
        return e    

    
    # ===================================
    # functions for tpc to setup events
    # ==================================

    def send_prepare_event(self, event):        
        peers_fail = []
        for peer in peers:
            if peer != self.url:
                # post request to other instance
                payload = {'eid': str(event.eid), 
                       'event_name':str(event.event_name),
                       'master':str(event.master)}
                url = 'http://'+peer + '/eventprepare'
                print 'connect '+url
                r = requests.post(url, data=payload)
                if int(r.status_code) == 200:
                    continue
                elif int(r.status_code) == 201:
                    return False
                else:
                    peers_fail.append(peer) # for future retry                
        
        return True

    def recv_prepare_event(self, form):
        e = self.get_event_from_eid(form['eid'])
        if e is None:
            print "receive new event:" + form['eid']
            # new event happens
            e = Event_g(form['event_name'])
            e.eid = form['eid']
            e.master = form['master']
            e.is_commit = 0
            self.events.append(e)
            
            db = get_db()
            save_event(db, e)
            db.commit()
            return True
        else:
            # event already exists, a repeated query detected
            print 'repeat prepare query for ' + eid
            # nothing happens
            return True

    def send_commit_event(self,e):
        peers_fail = []
        for peer in peers:
            if peer != self.url:
                payload = {'eid':e.eid}
                # post request to other instance
                url = 'http://'+peer + '/eventcommit'
                r = requests.post(url, data=payload)
                if int(r.status_code) == 200:
                    continue
                elif int(r.status_code) == 201:
                    return False
                else:
                    peers_fail.append(peer) # for future retry                
        
        return True
        


    def recv_commit_event(self, form):
        e = self.get_event_from_eid(form['eid'])
        if e is None:
            # definitely something wrong
            return False                
        else:
            e.is_commit = 1
            # change the event to be commited 
            db = get_db()
            commit_event(db, e)
            db.commit()
            return True


    def send_rollback_event(self):
        peers_fail = []
        for peer in peers:
            if peer != self.url:
                payload = {'eid':e.eid}
                # post request to other instance
                url = 'http://'+peer + '/eventrollback'
                r = requests.post(url, data=payload)
                if int(r.status_code) == 200:
                    continue
                elif int(r.status_code) == 201:
                    return False
                else:
                    peers_fail.append(peer) # for future retry                
        
        return True

    
    def recv_rollback_event(self, form):
        e = self.get_event_from_eid(form['eid'])
        if e is None:
            # definitely something wrong
            return False                
        else:
            self.events.remove(e)
            # change the event to be commited 
            db = get_db()            
            rollback_event(db, e)
            db.commit()
            return True





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

def save_new_uncommit_image(db, eid, uid, image_name, image_path, iid):
    db.execute('insert into uncommit_image_g (iid, eid, uid, image_name, image_path, is_commit) values (?,?,?,?,?,?)', [iid, eid, uid, image_name, image_path, 0])
    
               
def save_commit_image_for_event(db, eid):
    cur = db.execute('select * from uncommit_image_g where eid = ?', [eid])
    images = cur.fetchall()
    db.execute('delete from uncommit_image_g where eid = ?', [eid])
    for image in images:
        db.execute('insert into commit_image_g (iid, eid, uid, image_name, image_path) values (?,?,?,?,?)', [image['iid'], image['eid'], image['uid'], image['image_name'], image['image_path']])
    

def uncommit_image_exist(iid):
    db = get_db()
    cur = db.execute('select * from uncommit_image_g where iid = ?', [iid])
    images = cur.fetchall()
    if len(images) > 0:
        return True
    else:
        return False

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
        self.master = None
        self.is_commit = 0    # 0 for not committed, 1 for committed
        self.slave_uid = None
        self.is_refused = False
    def set_eid(eid):
        self.eid = eid
    
    def set_master(self,m):
        self.master = m

    
        
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
        
        if self.master != whoami and self.slave_uid is None:
            print self.master
            print whoami
            self.slave_uid = get_random_id()
            if self.send_new_user():
                return
            else:
                raise Exception
        return
        

    def send_new_user(self):
        payload = {'eid': self.eid, 'uid': self.slave_uid}
                
        url = 'http://' + self.master + '/newuser'
        r = requests.post(url, data=payload)
        
        if int(r.status_code) == 200:
            return True
        else:
            return False

    def recv_new_user_slave(self, uid):
        
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
        image['is_commit'] = 0
        image['iid'] = get_random_id()
        self.uncommit_images.append(image)
        
        db = get_db()
        save_new_uncommit_image(db, self.eid, uid, image_name, 
                                image_path, image['iid'])
        db.commit()
        
        if self.send_prepare_image(image):
            # all instances successfully returns
            if self.send_commit_image(image):
                image['is_commit'] = 1;
                db = get_db()
                commit_image(db,image['iid'])
                db.commit()
                print self.uncommit_images
            else:
                # should repeat the commit packet
                raise Exception
        else:
            if self.send_rollback_image(image):
                db = get_db()
                rollback_image(db, image['iid'])
                db.commit()
            else:
                raise Exception

        
        self.reset_timer()


    def send_prepare_image(self,image):
        
        peers_fail = []
#        f = codecs.open(image['image_path'], encoding='utf-8')
#        f = open(image['image_path'], 'rb')
        payload = {'iid':image['iid'], 'uid': image['uid'], 
                   'eid':image['eid']}
        files = {'file': (image['image_name'],open(image['image_path'],'rb'))}
        
        #f.close()
        
        for peer in peers:
            if peer != whoami:                
                url = 'http://' + peer + '/imageprepare'
                r = requests.post(url, data=payload, files=files)
                print r.text
                if int(r.status_code) == 200:
                    continue
                elif int(r.status_code) == 201:
                    return False
                else:
                    peers_fail.append(peer) # for future retry                

        return True

    def recv_prepare_image(self,request):
        
        form = request.form
        if uncommit_image_exist(form['iid']):
            return True
        else:            
            print "receive new image:" + form['iid']
            print request
            # save new uncommit images
            image = dict()
            image['iid'] = form['iid']
            image['eid'] = form['eid']
            image['uid'] = form['uid']

            print "recv_prepare_image reach here"
            f = request.files['file']
            print f.filename
            filename = secure_filename(f.filename)
            pathname = os.path.join(app.config['PATH_IMAGE'], filename); 
            print "recv_prepare_image: pathname=" + pathname
            f.save(pathname)
            

            image['image_path'] = pathname
            image['image_name'] = filename

            image['is_commit'] = 0
            
            
            self.uncommit_images.append(image)
            
            print self.uncommit_images
            
            db = get_db()
            save_new_uncommit_image(db, image['eid'], image['uid'], 
                                    image['image_name'], 
                                    image['image_path'], 
                                    image['iid'])
            db.commit()
            return True
        
        


    def send_commit_image(self, image):
        peers_fail = []
        for peer in peers:
            if peer != whoami:
                payload = {'eid':image['eid'],'iid':image['iid']}
                # post request to other instance
                url = 'http://'+peer + '/imagecommit'
                r = requests.post(url, data=payload)
                if int(r.status_code) == 200:
                    continue
                elif int(r.status_code) == 201:
                    return False
                else:
                    peers_fail.append(peer) # for future retry                
        
        return True



    def recv_commit_image(self,form):
        
        for image in self.uncommit_images:
            print image['iid']
            if image['iid'] == form['iid']:
                image['is_commit'] = 1
                db = get_db()
                commit_image(db, form['iid'])
                db.commit()
                self.reset_timer()
                return True
        else:
            # the image should really be there!
            raise Exception
    

    def send_rollback_image(self, image):
        peers_fail = []
        for peer in peers:
            if peer != whoami:
                payload = {'eid':image['eid'],'iid':image['iid']}
                # post request to other instance
                url = 'http://'+peer + '/imagerollback'
                r = requests.post(url, data=payload)
                if int(r.status_code) == 200:
                    continue
                elif int(r.status_code) == 201:
                    return False
                else:
                    peers_fail.append(peer) # for future retry                
        
        return True
     
    def recv_rollback_image(self, form):
        for image in self.uncommit_images:
            if image['iid'] == form['iid']:
                image['is_commit'] = 0
                self.uncommit_images.remove(image)
                db = get_db()
                rollback_image(db, iid)
                reset_timer()
                db.commit()
                return True
        else:
            # the image should really be there!
            raise Exception
        
    
    def send_prepare_commit(self):
        peers_fail = []
        payload = {'eid':self.eid}

        
        for peer in peers:
            if peer != whoami:                
                url = 'http://' + peer + '/commitprepare'
                r = requests.post(url, data=payload)
                if int(r.status_code) == 200:
                    continue
                elif int(r.status_code) == 201:
                    return False
                else:
                    peers_fail.append(peer) # for future retry                

        return True



    def recv_prepare_commit(self):
        # do nothing
        
        return True


    def send_commit_commit(self, c):
        peers_fail = []
        for peer in peers:
            if peer != whoami:
                payload = {'eid':self.eid, 'commit':c}
                # post request to other instance
                url = 'http://'+peer + '/commitcommit'
                r = requests.post(url, data=payload)
                if int(r.status_code) == 200:
                    continue
                elif int(r.status_code) == 201:
                    return False
                else:
                    peers_fail.append(peer) # for future retry                
        
        return True
    
    def recv_commit_commit(self, form):
        print "recv_commit_commit: commit" + form['commit']
        if int(form['commit']) == 1:
            
            self.clear_vote_state()
            db = get_db()
            self._commit_images(db)
            save_vote_state(db, self.eid, self.vote_states)
            db.commit()
            self.stop_timer()
            self.info = 'Photos have been successfully committed'
        else: # refuse
            if not self.does_timeout():
                self.clear_vote_state()
                self.uncommit_images = []
                db = get_db()
                save_vote_state(db, self.eid, self.vote_states)
                delete_uncommit_images_for_event(db, self.eid)
                db.commit()
                self.stop_timer()
                self.is_refused = False
                self.info = 'One of the users refuse to commit the photos, abort'
                
        return True

    def send_rollback_commit(self):
        peers_fail = []
        for peer in peers:
            if peer != whoami:
                payload = {'eid':image['eid']}
                # post request to other instance
                url = 'http://'+peer + '/rollbackcommit'
                r = requests.post(url, data=payload)
                if int(r.status_code) == 200:
                    continue
                elif int(r.status_code) == 201:
                    return False
                else:
                    peers_fail.append(peer) # for future retry                
        
        return True



    def recv_rollback_commit(self):
        #do nothing
        return True
    
        
    def send_agree_to_master(self):

        payload = {'eid': self.eid, 'uid':self.slave_uid}        
        url = 'http://' + self.master + '/vote'
        r = requests.post(url, data=payload)        
        if int(r.status_code) == 200:
            return True
        else:
            return False

    def send_agree_to_master(self):

        payload = {'eid': self.eid, 'uid':self.slave_uid,'vote':1}        
        url = 'http://' + self.master + '/vote'
        r = requests.post(url, data=payload)
        
        if int(r.status_code) == 200:
            return True
        else:
            return False

    def send_refuse_to_master(self):
        payload = {'eid': self.eid, 'uid':self.slave_uid, 'vote':0}        
        url = 'http://' + self.master + '/vote'
        r = requests.post(url, data=payload)
        
        if int(r.status_code) == 200:
            return True
        else:
            return False
        
    def _commit_images(self, db):
        self.commit_images = self.commit_images + self.uncommit_images
        self.uncommit_images = []
        save_commit_image_for_event(db, self.eid)

        
    def agree(self, uid):
        print "agree:" + "begin"
        if not self.does_timeout():
            print "agree:" + "not timeout"
            print "vote_states"
            print self.vote_states
            for vote in self.vote_states:
                print 'agree: uid = ' + uid 
                if vote['uid'] == uid:
                    print "find vote"
                    vote['accept'] = 1
                    if self.all_accept():
             
                        # if this is a slave_instance, send aggregate 
                        # agree to master
                        if self.slave_uid is not None:
                            print "agree:" + 'prepare to send agree to master'
                            if self.send_agree_to_master():
                                return
                            else:
                                # communication broken, should abort?
                                raise Exception
                        
                        else:
                            pass
                            # two phase commit to commit the images
                    else:
                        db = get_db()
                        update_vote_state(db, self.eid, uid, 1)
                        db.commit()
                        break
            #else:
            #   raise exception no such user
        
    def refuse(self, uid):

        print "refuse:" + "begin"
        if not self.does_timeout():
            if self.slave_uid is not None:
                print "refuse:" + 'prepare to send fuse to master'
                if self.send_refuse_to_master():
                    return
                else:
                    # communication broken, should abort?
                    raise Exception
                        
       
            else:
                self.is_refused = True
                return                
                
            #else:
            #   raise exception no such user            
            
    def does_timeout(self):
        time_now = time.time()
        if self.time_start > 0 and time_now - self.time_start > VOTE_INTERVAL:
            self.info = 'Timeout, abort'
            self.clear_vote_state()
            self.uncommit_images = []
            db = get_db()
            save_vote_state(db, self.eid, self.vote_states)
            delete_uncommit_images_for_event(db, self.eid)
            db.commit()
            print "does Timeout: return True"
            return True
        else:
            print "does_timeout: return False, time_start:" + str(self.time_start) + 'time_now:' + str(time_now)
            return False
    
    def reset_timer(self):
        self.time_start = time.time()

    def stop_timer(self):
        self.time_start = -1 # time_start < 0 when timer is stopped


    # return True if all current user accept
    def all_accept(self):
        for vote in self.vote_states:
            if vote['accept'] != 1:
                return False
        else:
            return True

    def check_commit(self):
        
        if self.slave_uid is None and self.all_accept():
            print "check_commit: prepare to commit commit"
            if self.send_prepare_commit():
                # all instances successfully returns
                if self.send_commit_commit(1):
                    print "all users have accepted"
                    self.clear_vote_state()
                    db = get_db()
                    self._commit_images(db)
                    save_vote_state(db, self.eid, self.vote_states)
                    db.commit()
                    self.stop_timer()
                    self.info = 'Photos have been successfully committed'
                    
                else:
                    # should repeat the commit packet
                    raise Exception
            else:
                if self.send_rollback_commit():
                    
                    pass
                else:
                    raise Exception
        elif self.slave_uid is None and self.is_refused is True:
            print "check commit: prepare to refuse"
            if self.send_prepare_commit():
                # all instances successfully returns
                if self.send_commit_commit(0):
                    self.clear_vote_state()
                    self.uncommit_images = []
                    db = get_db()
                    save_vote_state(db, self.eid, self.vote_states)
                    delete_uncommit_images_for_event(db, self.eid)
                    db.commit()
                    self.is_refused = False
                    self.stop_timer()
                    self.info = 'One of the users refuse to commit the photos, abort'                    
                else:
                    # should repeat the commit packet
                    raise Exception
            else:
                if self.send_rollback_commit():
                    
                    pass
                else:
                    raise Exception


                            

#global variable
evt_mgr = EventManager_g()
peers = ['127.0.0.1:5000', '127.0.0.1:5001']
whoami = None


# it seems allowing anyone to create event will cause DoS attack
@app.route('/', methods = ['GET', 'POST'])
def create_event():
    
    event_url = None
    err_info = None

    display_info = dict()
    if request.method == 'POST':
        e = evt_mgr.get_event_from_name(request.form['event_name'])

        if not e:
            e = evt_mgr.add_event_master(request.form['event_name'])            
            display_info['event_url'] = 'event/' + e.eid
            print event_url
        else:
            display_info['err_info'] = 'Group Name already exists'            
            
    return render_template('index_g.html', info=display_info)


@app.route('/event/<eid>', methods = ['GET', 'POST'])
def display_event(eid):
    print eid
    e = evt_mgr.get_event_from_eid(eid)
    if e is None or e.is_commit != 1:
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
    e.check_commit()
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
        print "/accept: prepare to check_commit"
        e.check_commit()
    return redirect(url_for('display_event', eid = session['eid']))

@app.route('/vote',methods=['POST'])
def handle_vote():
    if request.method == 'POST':
        print "handle_vote:" + request.form['uid'] + 'vote: '+ request.form['vote']
        e = evt_mgr.get_event_from_eid(request.form['eid'])
        if int(request.form['vote']) == 1:
            e.agree(request.form['uid'])
        else:
            e.refuse(request.form['uid'])
    return '',200

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

@app.route('/testrecv', methods=['POST'])
def testrecv():
    print 'testrecv: prepare to return 201 OK'
    print 'request test para: ' + request.form['test']
    return '', 201


@app.route('/testsend', methods = ['GET'])
def testsend():
    print 'testsend: prepare to send request'
    payload = {'test':'HelloWorld!'}
    r = requests.post('http://127.0.0.1:5001/testrecv', data=payload)
    print 'status code: '+ str(r.status_code)
    return ''


@app.route('/eventprepare', methods = ['POST'])
def handle_prepare_event():
    if evt_mgr.recv_prepare_event(request.form):
        return '',200
    else:
        return '',201
    
@app.route('/eventcommit', methods = ['POST'])
def handle_commit_event():
    if evt_mgr.recv_commit_event(request.form):
        return '',200
    else:
        return '',201

@app.route('/eventrollback', methods = ['POST'])
def handle_rollback_event():
    if evt_mgr.recv_rollback_event(request.form):
        return '',200
    else:
        return '',201

@app.route('/newuser', methods = ['POST'])
def handle_new_user():
    e = evt_mgr.get_event_from_eid(request.form['eid'])
    if e is None:
        raise Exception
    else:
        e.recv_new_user_slave(request.form['uid'])
        return '',200

@app.route('/imageprepare', methods = ['POST'])
def handle_prepare_image():
    e = evt_mgr.get_event_from_eid(request.form['eid'])
    print "handle_prepare_image eid:" + request.form['eid'] 
    if e is None:
        raise Exception
    else:
        e.recv_prepare_image(request)
        return '', 200

@app.route('/imagecommit', methods=['POST'])
def handle_commit_image():
    e = evt_mgr.get_event_from_eid(request.form['eid'])
    print "handle_commit_image eid:" + request.form['eid'] 
    print e.uncommit_images
    if e is None:
        raise Exception
    else:
        e.recv_commit_image(request.form)
        return '', 200
    
              
@app.route('/imagerollback', methods=['POST'])
def handle_rollback_image():
    e = evt_mgr.get_event_from_eid(request.form['eid'])
    if e is None:
        raise Exception
    else:
        e.recv_rollback_image(request.form)
        return '', 200
        

@app.route('/commitprepare', methods = ['POST'])
def handle_prepare_commit():
    e = evt_mgr.get_event_from_eid(request.form['eid'])
    print "handle_prepare_commit eid:" + request.form['eid'] 
    if e is None:
        raise Exception
    else:
        e.recv_prepare_commit()
        return '', 200

@app.route('/commitcommit', methods=['POST'])
def handle_commit_commit():
    e = evt_mgr.get_event_from_eid(request.form['eid'])
    print "handle_commit_commit eid:" + request.form['eid'] 
    print e.uncommit_images
    if e is None:
        raise Exception
    else:
        e.recv_commit_commit(request.form)
        return '', 200
    
              
@app.route('/commitrollback', methods=['POST'])
def handle_rollback_commit():
    e = evt_mgr.get_event_from_eid(request.form['eid'])
    if e is None:
        raise Exception
    else:
        e.recv_rollback_commit(request.form)
        return '', 200


def self_config():
    # first parameter helps choose ip:port
    evt_mgr.url = peers[int(sys.argv[1])]

    [my_ip, my_port] = evt_mgr.url.split(':')
    evt_mgr.ip = my_ip
    evt_mgr.port = int(my_port)
    # make sure different instances of apps using different database
    app.config['DATABASE'] = app.config['DATABASE'] + sys.argv[1]
    app.config['PATH_IMAGE'] = app.config['PATH_IMAGE'] + sys.argv[1]

if __name__ == '__main__':
    self_config()    
    whoami = evt_mgr.url
    # if not debug, comment out this init_db()
    init_db()       

    app.run(host='0.0.0.0', port=evt_mgr.port)


