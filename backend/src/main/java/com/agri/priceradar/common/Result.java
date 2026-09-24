package com.agri.priceradar.common;

/**
 * 统一响应结构（蓝图 §6 铁律: {code, msg, data}, code=200 成功）
 */
public record Result<T>(int code, String msg, T data) {

    public static <T> Result<T> ok(T data) {
        return new Result<>(ResultCode.SUCCESS.getCode(), ResultCode.SUCCESS.getMsg(), data);
    }

    public static <T> Result<T> ok() {
        return ok(null);
    }

    public static <T> Result<T> fail(ResultCode rc) {
        return new Result<>(rc.getCode(), rc.getMsg(), null);
    }

    public static <T> Result<T> fail(ResultCode rc, String msg) {
        return new Result<>(rc.getCode(), msg, null);
    }

    public static <T> Result<T> fail(int code, String msg) {
        return new Result<>(code, msg, null);
    }
}
