package com.agri.priceradar.aspect;

import com.agri.priceradar.dto.LoginRequest;
import com.agri.priceradar.dto.AlertRuleUpdateRequest;
import com.agri.priceradar.entity.OpLog;
import com.agri.priceradar.mapper.SysUserMapper;
import com.agri.priceradar.service.OpLogService;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

@Aspect
@Component
public class OperationAuditAspect {
    private static final Logger log = LoggerFactory.getLogger(OperationAuditAspect.class);
    private final OpLogService service;
    private final SysUserMapper users;

    public OperationAuditAspect(OpLogService service, SysUserMapper users) {
        this.service = service;
        this.users = users;
    }

    @Around("@annotation(audited)")
    public Object audit(ProceedingJoinPoint point, Audited audited) throws Throwable {
        boolean success = false;
        Object result = null;
        try {
            result = point.proceed();
            success = audited.value() != AuditAction.TRIGGER_COLLECT || Boolean.TRUE.equals(result);
            return result;
        } finally {
            // 包括身份解析和摘要构造在内，全部审计步骤都不能改变返回值或原业务异常。
            try {
                record(audited.value(), point.getArgs(), success, result);
            } catch (Exception e) {
                log.warn("操作审计上下文解析失败: {}", e.getClass().getSimpleName());
            }
        }
    }

    private void record(AuditAction action, Object[] args, boolean success, Object returned) {
        OpLog entry = new OpLog();
        entry.setAction(action.name());
        entry.setResult(success ? "SUCCESS" : "FAILED");
        var authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication != null && authentication.isAuthenticated()
                && !"anonymousUser".equals(authentication.getName())) {
            entry.setUserId(Long.valueOf(authentication.getName()));
            var user = users.selectById(entry.getUserId());
            entry.setUsername(user == null ? "未知账号" : user.getUsername());
        }
        switch (action) {
            case LOGIN -> {
                String username = ((LoginRequest) args[0]).username();
                entry.setUsername(username);
                entry.setUserId(null);
                if (success) {
                    var user = users.selectByUsername(username);
                    if (user != null) entry.setUserId(user.getId());
                }
                entry.setTarget("登录认证");
                entry.setDetail(success ? "登录成功" : "登录失败");
            }
            case CHANGE_PASSWORD -> {
                entry.setTarget("账号:" + args[0]);
                entry.setDetail(success ? "密码修改成功" : "密码修改失败");
            }
            case UPDATE_ALERT_RULE -> {
                entry.setTarget("预警规则:" + args[0]);
                var request = (AlertRuleUpdateRequest) args[1];
                // 不记录自由文本 remark 或异常信息，避免夹带凭据。
                entry.setDetail(success ? "阈值=" + request.threshold() + "%，启用=" + request.enabled() : "预警规则修改失败");
            }
            case TRIGGER_COLLECT -> {
                entry.setTarget("增量采集");
                entry.setDetail(success ? "请求已受理；执行结果见 collect_log"
                        : Boolean.FALSE.equals(returned) ? "已有任务运行，本次未受理" : "采集请求受理异常");
            }
        }
        if (RequestContextHolder.getRequestAttributes() instanceof ServletRequestAttributes attrs) {
            // 直接连接地址；不信任客户端可伪造的 X-Forwarded-For。
            entry.setIp(attrs.getRequest().getRemoteAddr());
        }
        service.writeSafely(entry);
    }
}
