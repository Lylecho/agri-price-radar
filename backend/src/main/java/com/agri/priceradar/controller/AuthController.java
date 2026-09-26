package com.agri.priceradar.controller;

import com.agri.priceradar.common.Result;
import com.agri.priceradar.dto.LoginRequest;
import com.agri.priceradar.dto.ChangePasswordRequest;
import com.agri.priceradar.service.AuthService;
import com.agri.priceradar.vo.LoginVO;
import jakarta.validation.Valid;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 认证接口（蓝图 §6）
 */
@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final AuthService authService;

    public AuthController(AuthService authService) {
        this.authService = authService;
    }

    /** 登录: 返回 JWT 与角色 */
    @PostMapping("/login")
    public Result<LoginVO> login(@Valid @RequestBody LoginRequest request) {
        return Result.ok(authService.login(request));
    }

    /** 当前登录用户（前端刷新时校验登录态） */
    @GetMapping("/me")
    public Result<LoginVO> me(Authentication authentication) {
        String userId = authentication == null ? null : authentication.getName();
        return Result.ok(authService.current(userId));
    }

    /** 首次登录及日常改密均使用此接口。 */
    @PostMapping("/change-password")
    public Result<Void> changePassword(Authentication authentication,
                                       @Valid @RequestBody ChangePasswordRequest request) {
        authService.changePassword(authentication == null ? null : authentication.getName(), request);
        return Result.ok(null);
    }
}
