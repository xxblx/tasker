
import inspect


class CreateQueries:
    @staticmethod
    def sorted_key(x):
        return x

    @classmethod
    def get_create_queries(cls):
        cls_data = inspect.getmembers(cls, lambda x: not inspect.isroutine(x))
        for attr_name, value in sorted(cls_data, key=cls.sorted_key):
            if not attr_name.startswith('__') and not attr_name.startswith('_'):
                yield value


class CreateSchemaQueries(CreateQueries):
    schema = 'CREATE SCHEMA tasker'


class CreateFunctionQueries(CreateQueries):
    gen_project_id = """
CREATE OR REPLACE FUNCTION tasker.gen_project_id() RETURNS BIGINT AS $$
DECLARE
    start_epoch BIGINT := 1607731200000;
    cur_time BIGINT;
    seq_id INT;
    result BIGINT;
BEGIN
    SELECT FLOOR(EXTRACT(EPOCH FROM CURRENT_TIMESTAMP) * 1000) INTO cur_time;
    SELECT nextval('tasker.project_id_seq') % 1024 INTO seq_id;
    result := (cur_time - start_epoch) << 10;
    result := result | (seq_id);
    RETURN result;
END;
    $$ LANGUAGE plpgsql strict immutable;
"""
    task_update_edited = """
CREATE OR REPLACE FUNCTION tasker.task_update_edited() RETURNS TRIGGER AS $$
BEGIN
    NEW.edited = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
    $$ language plpgsql strict;
"""


class CreateTriggerQueries(CreateQueries):
    task_update = """
CREATE TRIGGER task_update BEFORE UPDATE on tasker.tasks
FOR EACH ROW EXECUTE PROCEDURE tasker.task_update_edited()
"""


class CreateSequenceQueries(CreateQueries):
    project_id = 'CREATE SEQUENCE tasker.project_id_seq'
    # folder_id = 'CREATE SEQUENCE tasker.folder_id_seq'
    # task_id = 'CREATE SEQUENCE tasker.task_id_seq'
    # comment_id = 'CREATE SEQUENCE tasker.comment_id_seq'
    # project_folder, project_task
    _new_sequence = 'CREATE SEQUENCE tasker.{seq} as INT'


class CreateTableQueries(CreateQueries):
    @staticmethod
    def sorted_key(x):
        # yield users, projects, folders, tasks at first
        _priority_dict = {'users': 1, 'projects': 2, 'folders': 3, 'tasks': 4}
        if x[0] in _priority_dict:
            return _priority_dict[x[0]]
        return 5

    users = """
CREATE TABLE IF NOT EXISTS tasker.users(
    user_id INT GENERATED ALWAYS AS IDENTITY,
    username TEXT,
    password BYTEA,
    role_global SMALLINT default 1,
    display_name TEXT DEFAULT NULL,
    UNIQUE(username),
    PRIMARY KEY(user_id)
)
"""

    tokens = """
CREATE TABLE IF NOT EXISTS tasker.tokens(
    token_id INT GENERATED ALWAYS AS IDENTITY,
    token_select TEXT,
    token_verify BYTEA,
    token_renew TEXT,
    expires_in TIMESTAMP,
    user_id INT,
    UNIQUE(token_select),
    PRIMARY KEY(token_id),
    CONSTRAINT fk_token_user
        FOREIGN KEY(user_id)
            REFERENCES tasker.users(user_id)
            ON DELETE CASCADE
)
"""

    projects = """
CREATE TABLE IF NOT EXISTS tasker.projects(
    project_id INT GENERATED ALWAYS AS IDENTITY,
    project_pub_id BIGINT NOT NULL DEFAULT tasker.gen_project_id(),
    title TEXT,
    description TEXT DEFAULT NULL,
    UNIQUE(project_pub_id),
    PRIMARY KEY(project_id)
)
"""

    projects_users = """
CREATE TABLE IF NOT EXISTS tasker.projects_users(
    project_id INT,
    user_id INT,
    role SMALLINT,
    CONSTRAINT fk_projects_users_project
        FOREIGN KEY(project_id)
            REFERENCES tasker.projects(project_id)
            ON DELETE CASCADE,
    CONSTRAINT fk_projects_users_user
        FOREIGN KEY(user_id)
            REFERENCES tasker.users(user_id)
            ON DELETE CASCADE
)
"""

    folders = """
CREATE TABLE IF NOT EXISTS tasker.folders(
    folder_id INT GENERATED ALWAYS AS IDENTITY,
    folder_pub_id INT,
    title TEXT,
    project_id INT,
    PRIMARY KEY(folder_id),
    CONSTRAINT fk_folder_project
        FOREIGN KEY(project_id)
            REFERENCES tasker.projects(project_id)
            ON DELETE CASCADE
)
"""

    tasks = """
CREATE TABLE IF NOT EXISTS tasker.tasks(
    task_id INT GENERATED ALWAYS AS IDENTITY,
    task_pub_id INT,
    title TEXT,
    description TEXT DEFAULT NULL,
    datetime_from TIMESTAMP DEFAULT NULL,
    datetime_due TIMESTAMP DEFAULT NULL,
    user_id INT,
    project_id INT,
    folder_id INT,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    edited TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(task_id),
    CONSTRAINT fk_task_user
        FOREIGN KEY(user_id)
            REFERENCES tasker.users(user_id)
            ON DELETE SET NULL,
    CONSTRAINT fk_task_project
        FOREIGN KEY(project_id)
            REFERENCES tasker.projects(project_id)
            ON DELETE CASCADE,
    CONSTRAINT fk_task_folder
        FOREIGN KEY(folder_id)
            REFERENCES tasker.folders(folder_id)
            ON DELETE CASCADE
)
"""

    followers = """
CREATE TABLE IF NOT EXISTS tasker.followers(
    task_id INT,
    user_id INT,
    CONSTRAINT fk_follower_task
        FOREIGN KEY(task_id)
            REFERENCES tasker.tasks(task_id)
            ON DELETE CASCADE,
    CONSTRAINT fk_follower_user
        FOREIGN KEY(user_id)
            REFERENCES tasker.users(user_id)
            ON DELETE CASCADE
) 
"""

    comments = """
CREATE TABLE IF NOT EXISTS tasker.comments(
    comment_id INT GENERATED ALWAYS AS IDENTITY,
    comment_pub_id INT,
    task_id INT,
    user_id INT,
    body TEXT,
    created TIMESTAMP,
    edited TIMESTAMP,
    PRIMARY KEY(comment_id),
    CONSTRAINT fk_comment_task
        FOREIGN KEY(task_id)
            REFERENCES tasker.tasks(task_id)
            ON DELETE CASCADE,
    CONSTRAINT fk_comment_user
        FOREIGN KEY(user_id)
            REFERENCES tasker.users(user_id)
            ON DELETE SET NULL
)
"""

    bookmarks = """
CREATE TABLE IF NOT EXISTS tasker.bookmarks(
    bookmark_id INT GENERATED ALWAYS AS IDENTITY,
    bookmark_pub_id INT,
    title TEXT,
    description TEXT DEFAULT NULL,
    url TEXT,
    user_id INT,
    project_id INT,
    folder_id INT,
    created TIMESTAMP,
    edited TIMESTAMP,
    CONSTRAINT fk_bookmark_user
        FOREIGN KEY(user_id)
            REFERENCES tasker.users(user_id)
            ON DELETE SET NULL,
    CONSTRAINT fk_bookmark_project
        FOREIGN KEY(project_id)
            REFERENCES tasker.projects(project_id)
            ON DELETE CASCADE,
    CONSTRAINT fk_bookmark_folder
        FOREIGN KEY(folder_id)
            REFERENCES tasker.folders(folder_id)
            ON DELETE CASCADE
)
"""
