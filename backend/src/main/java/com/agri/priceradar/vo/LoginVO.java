package com.agri.priceradar.vo;

/**
 * 登录结果
 *
 * @param token         JWT 令牌（前端置于 Authorization: Bearer &lt;token&gt;）
 * @param username      登录名
 * @param nickname      昵称
 * @param role          角色码: ADMIN / DATA_ADMIN
 * @param expireSeconds 令牌有效期（秒）
 */
public record LoginVO(String token, String username, String nickname,
                      String role, long expireSeconds) {
}
