package com.agri.priceradar.mapper;

import com.agri.priceradar.entity.PriceDaily;
import com.agri.priceradar.vo.CategoryStatsVO;
import com.agri.priceradar.vo.TrendPointVO;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.time.LocalDate;
import java.util.List;

/**
 * 采集明细 Mapper —— 所有 SQL 一律 #{} 参数化（铁律: 禁止字符串拼接）
 */
@Mapper
public interface PriceDailyMapper extends BaseMapper<PriceDaily> {

    /** 该品名的主导计价单位（单位治理: 同轴对比只取主导单位的行） */
    @Select("SELECT unit_info FROM price_daily WHERE prod_name = #{prodName} AND unit_info <> '' " +
            "GROUP BY unit_info ORDER BY COUNT(*) DESC LIMIT 1")
    String selectDominantUnit(@Param("prodName") String prodName);

    /** 日度均价序列（按发布日期聚合, 已过滤主导单位; 保留3位小数避免接口输出冗余精度） */
    @Select("SELECT pub_date AS tradeDate, ROUND(AVG(avg_price), 3) AS avgPrice FROM price_daily " +
            "WHERE prod_name = #{prodName} AND unit_info = #{unit} AND pub_date >= #{startDate} " +
            "GROUP BY pub_date ORDER BY pub_date")
    List<TrendPointVO> selectDailyAvg(@Param("prodName") String prodName,
                                      @Param("unit") String unit,
                                      @Param("startDate") LocalDate startDate);

    /** 最新一条记录（同品名同单位内取最新日期） */
    @Select("SELECT * FROM price_daily WHERE prod_name = #{prodName} AND unit_info = #{unit} " +
            "ORDER BY pub_date DESC, id DESC LIMIT 1")
    PriceDaily selectLatest(@Param("prodName") String prodName, @Param("unit") String unit);

    /** 数据量与时间跨度统计 */
    @Select("SELECT COUNT(*) AS cnt, MIN(pub_date) AS minDate, MAX(pub_date) AS maxDate " +
            "FROM price_daily WHERE prod_name = #{prodName}")
    CategoryStatsVO selectStats(@Param("prodName") String prodName);
}
