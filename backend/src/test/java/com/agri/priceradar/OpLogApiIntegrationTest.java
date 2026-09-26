package com.agri.priceradar;

import com.agri.priceradar.entity.OpLog;
import com.agri.priceradar.mapper.OpLogMapper;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.mock.mockito.SpyBean;
import org.springframework.http.MediaType;
import java.util.Map;
import java.nio.charset.StandardCharsets;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doThrow;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/** 使用独立账号和无网络子进程，验证审计、隔离、授权与筛选。 */
class OpLogApiIntegrationTest extends ApiTestBase {
    @SpyBean
    private OpLogMapper opLogMapper;

    @Test
    void adminCanReadAndFilter() throws Exception {
        String token = adminToken();
        mockMvc.perform(get("/api/admin/oplog").header("Authorization", bearer(token))
                        .param("username", testAdmin).param("action", "LOGIN"))
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.total").value(1))
                .andExpect(jsonPath("$.data.records[0].result").value("SUCCESS"));
        mockMvc.perform(get("/api/admin/oplog").header("Authorization", bearer(token))
                        .param("username", "' OR 1=1 --"))
                .andExpect(jsonPath("$.data.total").value(0));
    }

    @Test
    void dataAdminCannotReadAudit() throws Exception {
        mockMvc.perform(get("/api/admin/oplog").header("Authorization", bearer(dataAdminToken())))
                .andExpect(jsonPath("$.code").value(403));
    }

    @Test
    void anonymousCannotReadAudit() throws Exception {
        mockMvc.perform(get("/api/admin/oplog")).andExpect(jsonPath("$.code").value(401));
    }

    @Test
    void triggerWritesAcceptanceAudit() throws Exception {
        String response = mockMvc.perform(post("/api/admin/collect/trigger").header("Authorization", bearer(adminToken())))
                .andExpect(jsonPath("$.code").value(200)).andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);
        boolean accepted = objectMapper.readTree(response).path("data").path("accepted").asBoolean();
        var rows = jdbcTemplate.queryForList("SELECT result, detail FROM op_log WHERE username = ? AND action = ?", testAdmin, "TRIGGER_COLLECT");
        assertEquals(1, rows.size());
        assertEquals(accepted ? "SUCCESS" : "FAILED", rows.get(0).get("result"));
    }

    @Test
    void fourActionsHaveSafeDetails() throws Exception {
        String token = adminToken();
        var rule = jdbcTemplate.queryForMap("SELECT id, threshold, enabled, remark FROM alert_rule ORDER BY id LIMIT 1");
        try {
            mockMvc.perform(put("/api/alert/rules/" + rule.get("id")).header("Authorization", bearer(token))
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(objectMapper.writeValueAsString(Map.of("threshold", 6, "enabled", 1, "remark", testPassword))))
                    .andExpect(jsonPath("$.code").value(200));
            mockMvc.perform(post("/api/admin/collect/trigger").header("Authorization", bearer(token)))
                    .andExpect(jsonPath("$.code").value(200));
            mockMvc.perform(post("/api/auth/change-password").header("Authorization", bearer(token))
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(objectMapper.writeValueAsString(Map.of("oldPassword", testPassword, "newPassword", newPassword))))
                    .andExpect(jsonPath("$.code").value(200));
            var rows = jdbcTemplate.queryForList("SELECT action, detail, ip, user_id FROM op_log WHERE username = ?", testAdmin);
            assertEquals(4, rows.size());
            assertEquals(4, rows.stream().map(r -> r.get("action")).distinct().count());
            for (var row : rows) {
                assertNotNull(row.get("user_id"));
                assertEquals("127.0.0.1", row.get("ip"));
                assertFalse(row.get("detail").toString().contains(testPassword));
                assertFalse(row.get("detail").toString().contains(newPassword));
            }
        } finally {
            jdbcTemplate.update("UPDATE alert_rule SET threshold = ?, enabled = ?, remark = ? WHERE id = ?",
                    rule.get("threshold"), rule.get("enabled"), rule.get("remark"), rule.get("id"));
        }
    }

    @Test
    void oversizedFailedLoginIsTruncated() throws Exception {
        String username = testAdmin + "😀".repeat(40);
        mockMvc.perform(post("/api/auth/login").contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(Map.of("username", username, "password", testPassword))))
                .andExpect(jsonPath("$.code").value(400));
        String expected = username.substring(0, username.offsetByCodePoints(0, 32));
        var row = jdbcTemplate.queryForMap("SELECT username, result, user_id FROM op_log WHERE username = ? ORDER BY id DESC LIMIT 1", expected);
        assertEquals(32, row.get("username").toString().codePointCount(0, row.get("username").toString().length()));
        assertEquals("FAILED", row.get("result"));
        assertNull(row.get("user_id"));
    }

    @Test
    void auditDatabaseFailureDoesNotFailLogin() throws Exception {
        doThrow(new IllegalStateException("test insertion failure")).when(opLogMapper).insert(any(OpLog.class));
        assertNotNull(adminToken());
    }

    @Test
    void invalidPaginationAndActionAreRejected() throws Exception {
        String token = adminToken();
        mockMvc.perform(get("/api/admin/oplog").header("Authorization", bearer(token)).param("size", "101"))
                .andExpect(jsonPath("$.code").value(400));
        mockMvc.perform(get("/api/admin/oplog").header("Authorization", bearer(token)).param("action", "UNKNOWN"))
                .andExpect(jsonPath("$.code").value(400));
    }
}
