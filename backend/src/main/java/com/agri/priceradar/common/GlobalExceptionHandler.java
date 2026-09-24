package com.agri.priceradar.common;

import jakarta.validation.ConstraintViolationException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

/**
 * 全局异常处理 —— 所有异常统一转为 {code, msg, data} 结构
 */
@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    @ExceptionHandler(BizException.class)
    public Result<Void> handleBiz(BizException e) {
        log.warn("业务异常: {}", e.getMessage());
        return Result.fail(e.getResultCode(), e.getMessage());
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public Result<Void> handleValid(MethodArgumentNotValidException e) {
        String msg = e.getBindingResult().getFieldErrors().stream()
                .findFirst()
                .map(f -> f.getField() + ": " + f.getDefaultMessage())
                .orElse(ResultCode.PARAM_ERROR.getMsg());
        return Result.fail(ResultCode.PARAM_ERROR, msg);
    }

    @ExceptionHandler(MissingServletRequestParameterException.class)
    public Result<Void> handleMissingParam(MissingServletRequestParameterException e) {
        return Result.fail(ResultCode.PARAM_ERROR, "缺少必要参数: " + e.getParameterName());
    }

    /** 方法参数校验失败(@Validated + @Min/@Max) —— 必须映射为 400 而非 500 */
    @ExceptionHandler(ConstraintViolationException.class)
    public Result<Void> handleConstraint(ConstraintViolationException e) {
        String msg = e.getConstraintViolations().stream()
                .findFirst()
                .map(v -> v.getPropertyPath() + ": " + v.getMessage())
                .orElse(ResultCode.PARAM_ERROR.getMsg());
        return Result.fail(ResultCode.PARAM_ERROR, msg);
    }

    /** 方法级安全(@PreAuthorize)拒绝 —— 必须映射为 403, 不可被兜底分支吞成 500 */
    @ExceptionHandler(org.springframework.security.access.AccessDeniedException.class)
    public Result<Void> handleAccessDenied(org.springframework.security.access.AccessDeniedException e) {
        log.warn("权限不足: {}", e.getMessage());
        return Result.fail(ResultCode.FORBIDDEN, "无权限访问该资源");
    }

    @ExceptionHandler(Exception.class)
    public Result<Void> handleOther(Exception e) {
        log.error("未捕获异常", e);
        return Result.fail(ResultCode.SERVER_ERROR, "服务器内部错误: " + e.getClass().getSimpleName());
    }
}
