-- =====================================================================
-- W2 · RBAC 权限三表 + 预置账号（蓝图 §5.4 → 落地）
-- 说明: 仅开发环境使用; 密码为 BCrypt 摘要(明文 admin123 / dataadmin123),
--       首次登录后强制改密(W2.2 实现)。可重复执行(幂等)。
-- 执行: python python/scripts/run_sql.py backend/sql/w2_auth.sql
-- =====================================================================

CREATE TABLE IF NOT EXISTS sys_user (
    id          BIGINT       PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
    username    VARCHAR(32)  NOT NULL COMMENT '登录名',
    password    VARCHAR(100) NOT NULL COMMENT 'BCrypt 摘要',
    nickname    VARCHAR(32)  NULL     COMMENT '昵称',
    status      TINYINT      NOT NULL DEFAULT 1 COMMENT '1启用/0禁用',
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统用户';

CREATE TABLE IF NOT EXISTS sys_role (
    id      BIGINT      PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
    code    VARCHAR(32) NOT NULL COMMENT '角色码: ADMIN / DATA_ADMIN',
    name    VARCHAR(32) NOT NULL COMMENT '角色名',
    remark  VARCHAR(128) NULL COMMENT '说明',
    UNIQUE KEY uk_code (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='角色';

CREATE TABLE IF NOT EXISTS sys_user_role (
    id       BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
    user_id  BIGINT NOT NULL COMMENT '用户ID',
    role_id  BIGINT NOT NULL COMMENT '角色ID',
    UNIQUE KEY uk_user_role (user_id, role_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户角色关联';

-- ---------------- 预置角色 ----------------
INSERT INTO sys_role (code, name, remark) VALUES
    ('ADMIN',      '超级管理员', '全部权限: 用户/角色/品类/阈值/任务管理'),
    ('DATA_ADMIN', '数据管理员', '采集任务触发与日志、数据查询、预测查看')
ON DUPLICATE KEY UPDATE name = VALUES(name), remark = VALUES(remark);

-- ---------------- 预置账号(BCrypt 摘要) ----------------
INSERT INTO sys_user (username, password, nickname, status) VALUES
    ('admin',     '$2b$10$PLVH3Wo0A6SMC9l5Ap/CNeBxdnXbOuKs4XEHT6PV1pbV5j.8guUgy', '超级管理员', 1),
    ('dataadmin', '$2b$10$Jj9gm40vahxNSAerDBnDYuKsoqyLTx0LTMrRU5j13wXiW4yNDG0IG', '数据管理员', 1)
ON DUPLICATE KEY UPDATE nickname = VALUES(nickname), status = VALUES(status);

-- ---------------- 绑定用户-角色 ----------------
INSERT INTO sys_user_role (user_id, role_id)
SELECT u.id, r.id
FROM sys_user u
JOIN sys_role r
  ON (u.username = 'admin' AND r.code = 'ADMIN')
  OR (u.username = 'dataadmin' AND r.code = 'DATA_ADMIN')
ON DUPLICATE KEY UPDATE user_id = VALUES(user_id);
