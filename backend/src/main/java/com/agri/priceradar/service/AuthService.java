package com.agri.priceradar.service;

import com.agri.priceradar.aspect.Audited;
import com.agri.priceradar.aspect.AuditAction;

import com.agri.priceradar.common.BizException;
import com.agri.priceradar.common.ResultCode;
import com.agri.priceradar.dto.LoginRequest;
import com.agri.priceradar.dto.ChangePasswordRequest;
import com.agri.priceradar.entity.SysUser;
import com.agri.priceradar.mapper.SysUserMapper;
import com.agri.priceradar.security.JwtUtil;
import com.agri.priceradar.vo.LoginVO;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * 认证服务 —— 校验 BCrypt 密码并签发无状态 JWT
 * 安全约定: 用户不存在与密码错误返回同一提示, 不泄露账号是否存在
 */
@Service
public class AuthService {

    private static final Logger log = LoggerFactory.getLogger(AuthService.class);

    private final SysUserMapper sysUserMapper;
    private final PasswordEncoder passwordEncoder;
    private final JwtUtil jwtUtil;

    public AuthService(SysUserMapper sysUserMapper, PasswordEncoder passwordEncoder, JwtUtil jwtUtil) {
        this.sysUserMapper = sysUserMapper;
        this.passwordEncoder = passwordEncoder;
        this.jwtUtil = jwtUtil;
    }

    @Audited(AuditAction.LOGIN)
    public LoginVO login(LoginRequest request) {
        SysUser user = sysUserMapper.selectByUsername(request.username());
        if (user == null || !passwordEncoder.matches(request.password(), user.getPassword())) {
            log.warn("登录认证失败");
            throw new BizException(ResultCode.UNAUTHORIZED, "用户名或密码错误");
        }
        List<String> roles = sysUserMapper.selectRoleCodes(user.getId());
        if (roles.isEmpty()) {
            throw new BizException(ResultCode.FORBIDDEN, "账号未分配角色, 请联系管理员");
        }
        // 双角色场景下 ADMIN 优先
        String role = roles.contains("ADMIN") ? "ADMIN" : roles.get(0);
        String token = jwtUtil.generate(user.getId(), user.getUsername(), role);
        log.info("登录成功: username={}, role={}", user.getUsername(), role);
        return new LoginVO(token, user.getUsername(), user.getNickname(), role,
                jwtUtil.getExpireSeconds(), Integer.valueOf(1).equals(user.getMustChangePwd()));
    }

    /** 当前登录用户信息（前端刷新页面时校验登录态） */
    public LoginVO current(String userId) {
        if (userId == null) {
            throw new BizException(ResultCode.UNAUTHORIZED, "未登录或登录已过期");
        }
        SysUser user = sysUserMapper.selectById(Long.valueOf(userId));
        if (user == null || user.getStatus() == null || user.getStatus() != 1) {
            throw new BizException(ResultCode.UNAUTHORIZED, "账号不存在或已禁用");
        }
        List<String> roles = sysUserMapper.selectRoleCodes(user.getId());
        String role = roles.contains("ADMIN") ? "ADMIN" : (roles.isEmpty() ? null : roles.get(0));
        return new LoginVO(null, user.getUsername(), user.getNickname(), role,
                jwtUtil.getExpireSeconds(), Integer.valueOf(1).equals(user.getMustChangePwd()));
    }

    /** 当前用户改密；密码与限制标记原子更新。 */
    @Audited(AuditAction.CHANGE_PASSWORD)
    public void changePassword(String userId, ChangePasswordRequest request) {
        if (userId == null) throw new BizException(ResultCode.UNAUTHORIZED, "未登录或登录已过期");
        SysUser user = sysUserMapper.selectById(Long.valueOf(userId));
        if (user == null || user.getStatus() == null || user.getStatus() != 1) {
            throw new BizException(ResultCode.UNAUTHORIZED, "账号不存在或已禁用");
        }
        if (!passwordEncoder.matches(request.oldPassword(), user.getPassword())) {
            throw new BizException(ResultCode.PARAM_ERROR, "原密码错误");
        }
        if (request.oldPassword().equals(request.newPassword())) {
            throw new BizException(ResultCode.PARAM_ERROR, "新密码不能与原密码相同");
        }
        if (request.newPassword().getBytes(java.nio.charset.StandardCharsets.UTF_8).length > 72) {
            throw new BizException(ResultCode.PARAM_ERROR, "新密码长度不能超过 72 字节");
        }
        int changed = sysUserMapper.updatePassword(user.getId(), user.getPassword(),
                passwordEncoder.encode(request.newPassword()));
        if (changed != 1) throw new BizException(ResultCode.PARAM_ERROR, "密码已变化，请重新登录后重试");
        log.info("用户已修改密码: username={}", user.getUsername());
    }
}
