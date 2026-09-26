package com.agri.priceradar;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * 认证与鉴权集成测试（W2.2）
 * 覆盖: 登录成功/密码错误/不存在用户/无令牌/令牌非法/角色访问/当前用户
 */
class AuthApiIntegrationTest extends ApiTestBase {

    private static final String LOGIN = "/api/auth/login";

    @Test
    @DisplayName("admin 正确凭据登录应返回 token 与角色")
    void loginShouldReturnToken() throws Exception {
        mockMvc.perform(post(LOGIN).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"username\":\"admin\",\"password\":\"admin123\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.token").isNotEmpty())
                .andExpect(jsonPath("$.data.role").value("ADMIN"))
                .andExpect(jsonPath("$.data.mustChangePwd").value(true))
                .andExpect(jsonPath("$.data.expireSeconds").isNumber());
    }

    @Test
    @DisplayName("dataadmin 登录应返回 DATA_ADMIN 角色")
    void dataAdminLoginShouldReturnDataAdminRole() throws Exception {
        mockMvc.perform(post(LOGIN).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"username\":\"dataadmin\",\"password\":\"dataadmin123\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.role").value("DATA_ADMIN"))
                .andExpect(jsonPath("$.data.mustChangePwd").value(true));
    }

    @Test
    @DisplayName("密码错误应返回 401 且不区分账号是否存在")
    void wrongPasswordShouldReturn401() throws Exception {
        mockMvc.perform(post(LOGIN).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"username\":\"admin\",\"password\":\"wrong-password\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(401))
                .andExpect(jsonPath("$.msg").value("用户名或密码错误"));
    }

    @Test
    @DisplayName("不存在的用户应返回 401 且提示与密码错误一致")
    void unknownUserShouldReturn401() throws Exception {
        mockMvc.perform(post(LOGIN).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"username\":\"ghost-user\",\"password\":\"whatever\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(401))
                .andExpect(jsonPath("$.msg").value("用户名或密码错误"));
    }

    @Test
    @DisplayName("用户名为空应返回 400 参数错误")
    void blankUsernameShouldReturn400() throws Exception {
        mockMvc.perform(post(LOGIN).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"username\":\"\",\"password\":\"x\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(400));
    }

    @Test
    @DisplayName("无令牌访问业务接口应返回 401")
    void noTokenShouldReturn401() throws Exception {
        mockMvc.perform(get("/api/price/categories"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(401));
    }

    @Test
    @DisplayName("非法令牌访问应返回 401")
    void invalidTokenShouldReturn401() throws Exception {
        mockMvc.perform(get("/api/price/categories").header("Authorization", "Bearer not-a-real-token"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(401));
    }

    @Test
    @DisplayName("携带有效令牌可访问业务接口")
    void validTokenShouldAccessBusinessApi() throws Exception {
        String token = adminToken();
        mockMvc.perform(get("/api/price/categories").header("Authorization", bearer(token)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.length()").value(5));
    }

    @Test
    @DisplayName("DATA_ADMIN 可访问管理端接口")
    void dataAdminShouldAccessAdminApi() throws Exception {
        String token = dataAdminToken();
        mockMvc.perform(get("/api/admin/collect/logs").param("page", "1").param("size", "5")
                        .header("Authorization", bearer(token)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200));
    }

    @Test
    @DisplayName("/api/auth/me 返回当前登录用户")
    void meShouldReturnCurrentUser() throws Exception {
        String token = adminToken();
        mockMvc.perform(get("/api/auth/me").header("Authorization", bearer(token)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.username").value(testAdmin))
                .andExpect(jsonPath("$.data.role").value("ADMIN"));
    }

    @Test
    @DisplayName("首次登录须先改密，改密后业务接口可用且旧密码失效")
    void firstLoginMustChangePassword() throws Exception {
        jdbcTemplate.update("UPDATE sys_user SET must_change_pwd = 1 WHERE username = ?", testAdmin);
        String token = adminToken();
        mockMvc.perform(get("/api/auth/me").header("Authorization", bearer(token)))
                .andExpect(jsonPath("$.data.mustChangePwd").value(true));
        mockMvc.perform(get("/api/price/categories").header("Authorization", bearer(token)))
                .andExpect(jsonPath("$.code").value(403))
                .andExpect(jsonPath("$.msg").value("请先修改初始密码"));
        mockMvc.perform(post("/api/auth/change-password")
                        .header("Authorization", bearer(token))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"oldPassword\":\"admin123\",\"newPassword\":\"new-password-123\"}"))
                .andExpect(jsonPath("$.code").value(200));
        mockMvc.perform(get("/api/price/categories").header("Authorization", bearer(token)))
                .andExpect(jsonPath("$.code").value(200));
        org.junit.jupiter.api.Assertions.assertNull(login(testAdmin, "admin123"));
        org.junit.jupiter.api.Assertions.assertNotNull(login(testAdmin, "new-password-123"));
    }

    @Test
    @DisplayName("原密码错误或新密码相同不能解除首次改密限制")
    void badPasswordChangeShouldStayBlocked() throws Exception {
        jdbcTemplate.update("UPDATE sys_user SET must_change_pwd = 1 WHERE username = ?", testAdmin);
        String token = adminToken();
        mockMvc.perform(post("/api/auth/change-password")
                        .header("Authorization", bearer(token))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"oldPassword\":\"wrong-pass\",\"newPassword\":\"new-password-123\"}"))
                .andExpect(jsonPath("$.code").value(400));
        mockMvc.perform(post("/api/auth/change-password")
                        .header("Authorization", bearer(token))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"oldPassword\":\"admin123\",\"newPassword\":\"admin123\"}"))
                .andExpect(jsonPath("$.code").value(400));
        mockMvc.perform(get("/api/price/categories").header("Authorization", bearer(token)))
                .andExpect(jsonPath("$.code").value(403));
    }
}
