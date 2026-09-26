package com.agri.priceradar.aspect;

import java.lang.annotation.*;

/** 标记需要记录受理或执行结果的业务方法。 */
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface Audited {
    AuditAction value();
}
