package com.agri.priceradar;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * 价格/预测/管理端接口集成测试（鉴权接入后需携带令牌）
 * 覆盖: 正常返回结构、五品类、预测免责声明、参数校验与未知品类的错误码
 */
class PriceApiIntegrationTest extends ApiTestBase {

    private String token;

    @BeforeEach
    void setUp() throws Exception {
        token = adminToken();
        org.junit.jupiter.api.Assertions.assertNotNull(token, "登录失败, 请先执行 backend/sql/w2_auth.sql 种子脚本");
    }

    @Test
    @DisplayName("GET /api/price/categories 返回 200 与五个品类")
    void categoriesShouldReturnFive() throws Exception {
        mockMvc.perform(get("/api/price/categories").header("Authorization", bearer(token)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.length()").value(5))
                .andExpect(jsonPath("$.data[0].category").exists())
                .andExpect(jsonPath("$.data[0].unit").exists());
    }

    @Test
    @DisplayName("GET /api/price/trend 返回日度均价序列")
    void trendShouldReturnSeries() throws Exception {
        mockMvc.perform(get("/api/price/trend").param("category", "大白菜").param("days", "90")
                        .header("Authorization", bearer(token)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data").isArray())
                .andExpect(jsonPath("$.data[0].tradeDate").exists())
                .andExpect(jsonPath("$.data[0].avgPrice").exists());
    }

    @Test
    @DisplayName("GET /api/price/change 返回环比结构")
    void changeShouldReturnPct() throws Exception {
        mockMvc.perform(get("/api/price/change").param("category", "鸡蛋")
                        .header("Authorization", bearer(token)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.changePct").exists())
                .andExpect(jsonPath("$.data.latestDate").exists());
    }

    @Test
    @DisplayName("GET /api/predict/latest 必须携带模型/MAPE/免责声明与7个预测点")
    void predictShouldCarryModelMapeAndDisclaimer() throws Exception {
        mockMvc.perform(get("/api/predict/latest").param("category", "大白菜")
                        .header("Authorization", bearer(token)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.model").exists())
                .andExpect(jsonPath("$.data.mapeTest").exists())
                .andExpect(jsonPath("$.data.points.length()").value(7))
                .andExpect(jsonPath("$.data.disclaimer").value("预测结果仅供参考, 不构成任何买卖建议"));
    }

    @Test
    @DisplayName("未知品类应返回 400 参数错误")
    void unknownCategoryShouldReturn400() throws Exception {
        mockMvc.perform(get("/api/price/trend").param("category", "胡萝卜").param("days", "90")
                        .header("Authorization", bearer(token)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(400));
    }

    @Test
    @DisplayName("days 越界应返回 400 而非 500")
    void daysOutOfRangeShouldReturn400() throws Exception {
        mockMvc.perform(get("/api/price/trend").param("category", "大白菜").param("days", "5000")
                        .header("Authorization", bearer(token)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(400));
    }

    @Test
    @DisplayName("缺少必要参数应返回 400")
    void missingParamShouldReturn400() throws Exception {
        mockMvc.perform(get("/api/price/change").header("Authorization", bearer(token)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(400));
    }

    @Test
    @DisplayName("管理端任务日志分页结构正确")
    void adminLogsShouldPage() throws Exception {
        mockMvc.perform(get("/api/admin/collect/logs").param("page", "1").param("size", "5")
                        .header("Authorization", bearer(token)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.total").exists())
                .andExpect(jsonPath("$.data.records").isArray());
    }
}
