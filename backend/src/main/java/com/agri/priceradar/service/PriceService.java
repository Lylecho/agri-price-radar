package com.agri.priceradar.service;

import com.agri.priceradar.common.BizException;
import com.agri.priceradar.common.CategoryCatalog;
import com.agri.priceradar.common.ResultCode;
import com.agri.priceradar.entity.PriceDaily;
import com.agri.priceradar.mapper.PriceDailyMapper;
import com.agri.priceradar.vo.CategoryStatsVO;
import com.agri.priceradar.vo.CategoryVO;
import com.agri.priceradar.vo.ChangeVO;
import com.agri.priceradar.vo.TrendPointVO;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * 价格查询服务 —— 只读已入库快照（铁律: 不在请求时现场爬取）
 * 单位治理: 所有序列只取该品名「主导单位」的行, 避免箱/筐整件价混入同轴对比
 */
@Service
public class PriceService {

    private final PriceDailyMapper priceMapper;

    public PriceService(PriceDailyMapper priceMapper) {
        this.priceMapper = priceMapper;
    }

    /** 五品类概览: 代表品名 + 主导单位 + 最新日期与均价 */
    public List<CategoryVO> listCategories() {
        List<CategoryVO> list = new ArrayList<>();
        for (Map.Entry<String, String> entry : CategoryCatalog.all().entrySet()) {
            String category = entry.getKey();
            String prodName = entry.getValue();
            String unit = priceMapper.selectDominantUnit(prodName);
            PriceDaily latest = unit == null ? null : priceMapper.selectLatest(prodName, unit);
            list.add(new CategoryVO(category, prodName, unit,
                    latest == null ? null : latest.getPubDate().toString(),
                    latest == null ? null : latest.getAvgPrice()));
        }
        return list;
    }

    /** 日度均价序列; 以库中最新日期为锚点向前取 days 天（数据滞后时图表仍完整） */
    public List<TrendPointVO> trend(String category, int days) {
        String prodName = requireCategory(category);
        String unit = requireUnit(prodName);
        LocalDate endDate = requireEndDate(prodName);
        LocalDate startDate = endDate.minusDays(days - 1L);
        return priceMapper.selectDailyAvg(prodName, unit, startDate);
    }

    /** 日环比: 最新交易日 vs 前一交易日（前端按红涨绿跌渲染） */
    public ChangeVO change(String category) {
        String prodName = requireCategory(category);
        String unit = requireUnit(prodName);
        LocalDate endDate = requireEndDate(prodName);
        List<TrendPointVO> points = priceMapper.selectDailyAvg(prodName, unit, endDate.minusDays(20));
        if (points.size() < 2) {
            throw new BizException(ResultCode.NOT_FOUND, category + " 交易日不足两点, 无法计算环比");
        }
        TrendPointVO last = points.get(points.size() - 1);
        TrendPointVO prev = points.get(points.size() - 2);
        BigDecimal changePct = last.getAvgPrice().subtract(prev.getAvgPrice())
                .divide(prev.getAvgPrice(), 6, RoundingMode.HALF_UP)
                .multiply(BigDecimal.valueOf(100))
                .setScale(2, RoundingMode.HALF_UP);
        return new ChangeVO(category,
                last.getTradeDate().toString(), prev.getTradeDate().toString(),
                last.getAvgPrice().setScale(3, RoundingMode.HALF_UP),
                prev.getAvgPrice().setScale(3, RoundingMode.HALF_UP),
                changePct);
    }

    /** 品类数据量与时间跨度（管理端监控用） */
    public CategoryStatsVO stats(String category) {
        String prodName = requireCategory(category);
        return priceMapper.selectStats(prodName);
    }

    // ---------------- 内部校验 ----------------

    private String requireCategory(String category) {
        String prodName = CategoryCatalog.prodNameOf(category);
        if (prodName == null) {
            throw new BizException(ResultCode.PARAM_ERROR, "未知品类: " + category);
        }
        return prodName;
    }

    private String requireUnit(String prodName) {
        String unit = priceMapper.selectDominantUnit(prodName);
        if (unit == null) {
            throw new BizException(ResultCode.NOT_FOUND, "库中无该品名数据: " + prodName);
        }
        return unit;
    }

    private LocalDate requireEndDate(String prodName) {
        CategoryStatsVO stats = priceMapper.selectStats(prodName);
        if (stats == null || stats.getMaxDate() == null) {
            throw new BizException(ResultCode.NOT_FOUND, "库中无该品名数据: " + prodName);
        }
        return stats.getMaxDate();
    }
}
