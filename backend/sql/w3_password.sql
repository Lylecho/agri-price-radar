-- W3 首次登录强制改密（已获用户确认）
-- 仅执行一次：python python/scripts/run_sql.py backend/sql/w3_password.sql
ALTER TABLE sys_user
    ADD COLUMN must_change_pwd TINYINT NOT NULL DEFAULT 0 COMMENT '1需首次改密/0正常';

-- 仅标记仍使用预置密码摘要的开发账号，已自行改密的账号不受影响。
UPDATE sys_user
SET must_change_pwd = 1
WHERE (username = 'admin' AND password = '$2b$10$PLVH3Wo0A6SMC9l5Ap/CNeBxdnXbOuKs4XEHT6PV1pbV5j.8guUgy')
   OR (username = 'dataadmin' AND password = '$2b$10$Jj9gm40vahxNSAerDBnDYuKsoqyLTx0LTMrRU5j13wXiW4yNDG0IG');
