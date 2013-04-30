/* drop the table if entries exist */
drop table if exists event_g;
drop table if exists user_g;
drop table if exists event_user_rel_g;
drop table if exists uncommit_image_g;
drop table if exists commit_image_g;
drop table if exists vote_state_g;

create table event_g{
       id integer primary key autoincrement,
       eid blob,
       event_name text
};              

create table user_g{
       id integer primary key autoincrement,
       uid blob            
};

create table event_user_rel_g{
       id integer primary key autoincrement,
       uid blob,
       eid blob
};

create table uncommit_image_g (
       id integer primary key autoincrement,
       eid blob,
       uid blob,
       image_name text not null,
       image_path text not null
);

create table commit_image_g (
       id integer primary key autoincrement,
       eid blob,
       uid blob,
       image_name text not null,
       image_path text not null
);

create table vote_state_g (
       id integer primary key autoincrement,
       eid blob,
       uid blob,
       accept integer
);