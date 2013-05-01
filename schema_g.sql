/* drop the table if entries exist */
drop table if exists event_g;
drop table if exists user_g;
drop table if exists event_user_rel_g;
drop table if exists uncommit_image_g;
drop table if exists commit_image_g;
drop table if exists vote_state_g;


create table event_g (
       id integer primary key autoincrement,
       eid text,
       event_name text,
       master text,
       is_commit integer
);              

create table user_g (
       id integer primary key autoincrement,
       uid text            
);
create table event_user_rel_g (
       id integer primary key autoincrement,
       uid text,
       eid text
);

create table uncommit_image_g (
       id integer primary key autoincrement,
       iid text,
       eid text,
       uid text,       
       image_name text not null,
       image_path text not null,
       is_commit integer
);

create table commit_image_g (
       id integer primary key autoincrement,
       iid text,
       eid text,
       uid text,
       image_name text not null,
       image_path text not null
);

create table vote_state_g (
       id integer primary key autoincrement,
       eid text,
       uid text,
       accept integer
);

