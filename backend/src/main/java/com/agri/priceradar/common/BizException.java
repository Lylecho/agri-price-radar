package com.agri.priceradar.common;

/**
 * 业务异常 —— 由 GlobalExceptionHandler 统一转换为 Result
 */
public class BizException extends RuntimeException {

    private final ResultCode resultCode;

    public BizException(ResultCode resultCode, String msg) {
        super(msg);
        this.resultCode = resultCode;
    }

    public BizException(ResultCode resultCode) {
        this(resultCode, resultCode.getMsg());
    }

    public ResultCode getResultCode() {
        return resultCode;
    }
}
