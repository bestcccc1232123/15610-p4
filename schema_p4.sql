/* drop the table if entries exist */
drop table if exists group_p4;
drop table if exists user_p4;
drop table if exists image_p4;
drop table if exists image_public_p4;

create table group_p4 (
  id integer primary key autoincrement,
  group_name text,
  group_comment text
);

create table user_p4 (
       id integer primary key autoincrement,
       gid integer,
       user_name text not null,
       user_pwd text not null
);

create table image_p4 (
       id integer primary key autoincrement,
       gid integer,
       uid integer,
       image_name text not null,
       image_path text not null
);

create table image_public_p4 (
       id integer primary key autoincrement,
       gid integer,
       uid integer,
       image_name text not null,
       image_path text not null
);


create table vote_state_p4 (
       id integer primary key autoincrement,
       gid integer,
       uid integer,
       accept integer
);