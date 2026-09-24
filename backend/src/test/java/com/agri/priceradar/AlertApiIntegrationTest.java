package com.agri.priceradar;

import com.fasterxml.jackson.databind.JsonNode;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import java.nio.charset.StandardCharsets;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * 预警模块集成测试（W2.2）
 * 覆盖: 规则列表、ADMIN 改阈值、DATA_ADMIN 越权 403、预警记录、概览、手动触发采集
 * 前置: 已执行 backend/sql/w22_alert.sql
 */
class AlertApiIntegrationTest extends ApiTestBase {

    private Long firstRuleId() throws Exception {
        String token = adminToken();
        String body = mockMvc.perform(get("/api/alert/rules").header("Authorization", bearer(token)))
                .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);
        JsonNode data = objectMapper.readTree(body).path("data");
        return data.isEmpty() ? null : data.get(0).path("id").asLong();
    }

    @Test
    @DisplayName("预警规则列表返回 5 个品类")
    void rulesShouldReturnFive() throws Exception {
        mockMvc.perform(get("/api/alert/rules").header("Authorization", bearer(adminToken())))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.length()").value(5))
                .andExpect(jsonPath("$.data[0].metric").value("DOD_PCT"));
    }

    @Test
    @DisplayName("ADMIN 可修改阈值, 并可恢复原值")
    void adminCanUpdateThreshold() throws Exception {
        String token = adminToken();
        Long id = firstRuleId();
        org.junit.jupiter.api.Assertions.assertNotNull(id, "请先执行 backend/sql/w22_alert.sql");

        mockMvc.perform(put("/api/alert/rules/" + id)
                        .header("Authorization", bearer(token))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"threshold\":3.5,\"enabled\":1,\"remark\":\"测试阈值\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.threshold").value(3.5));

        // 恢复为 5.0, 避免影响后续演示数据
        mockMvc.perform(put("/api/alert/rules/" + id)
                        .header("Authorization", bearer(token))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"threshold\":5.0,\"enabled\":1,\"remark\":\"默认阈值 5%\"}"))
                .andExpect(jsonPath("$.code").value(200));
    }

    @Test
    @DisplayName("DATA_ADMIN 修改阈值应被拒绝 403（越权用例）")
    void dataAdminCannotUpdateThreshold() throws Exception {
        String token = dataAdminToken();
        Long id = firstRuleId();
        org.junit.jupiter.api.Assertions.assertNotNull(id);

        mockMvc.perform(put("/api/alert/rules/" + id)
                        .header("Authorization", bearer(token))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"threshold\":9.9,\"enabled\":1}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(403));
    }

    @Test
    @DisplayName("阈值非法值应返回 400")
    void invalidThresholdShouldReturn400() throws Exception {
        Long id = firstRuleId();
        mockMvc.perform(put("/api/alert/rules/" + id)
                        .header("Authorization", bearer(adminToken()))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"threshold\":0,\"enabled\":1}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(400));
    }

    @Test
    @DisplayName("不存在的规则 id 返回 404 业务码")
    void unknownRuleShouldReturn404() throws Exception {
        mockMvc.perform(put("/api/alert/rules/999999")
                        .header("Authorization", bearer(adminToken()))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"threshold\":5.0,\"enabled\":1}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(404));
    }

    @Test
    @DisplayName("预警记录分页与概览可用")
    void recordsAndSummaryShouldWork() throws Exception {
        String token = adminToken();
        mockMvc.perform(get("/api/alert/records").param("page", "1").param("size", "5")
                        .header("Authorization", bearer(token)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.total").exists());

        mockMvc.perform(get("/api/alert/summary").header("Authorization", bearer(token)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.length()").value(5));
    }

    @Test
    @DisplayName("未登录访问预警接口返回 401")
    void anonymousShouldReturn401() throws Exception {
        mockMvc.perform(get("/api/alert/rules"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(401));
    }

    @Test
    @DisplayName("手动触发采集受理成功（异步执行, 不等待完成）")
    void triggerCollectShouldBeAccepted() throws Exception {
        mockMvc.perform(post("/api/admin/collect/trigger").header("Authorization", bearer(adminToken())))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.accepted").exists());
    }

    @Test
    @DisplayName("DATA_ADMIN 可查看管理端采集日志")
    void dataAdminCanReadLogs() throws Exception {
        mockMvc.perform(get("/api/admin/collect/logs").param("page", "1").param("size", "5")
                        .header("Authorization", bearer(dataAdminToken())))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200));
    }
}
