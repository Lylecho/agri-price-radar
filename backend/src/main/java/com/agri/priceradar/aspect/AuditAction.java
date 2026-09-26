package com.agri.priceradar.aspect;

/** 固定动作白名单，禁止从请求传入动作名称。 */
public enum AuditAction {
    LOGIN, CHANGE_PASSWORD, UPDATE_ALERT_RULE, TRIGGER_COLLECT
}
