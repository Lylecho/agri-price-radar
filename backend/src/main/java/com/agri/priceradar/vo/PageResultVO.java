package com.agri.priceradar.vo;

import com.baomidou.mybatisplus.core.metadata.IPage;

import java.util.List;

/**
 * 通用分页返回结构
 */
public record PageResultVO<T>(long total, long pages, long current, long size, List<T> records) {

    public static <T> PageResultVO<T> of(IPage<T> page) {
        return new PageResultVO<>(page.getTotal(), page.getPages(), page.getCurrent(),
                page.getSize(), page.getRecords());
    }
}
