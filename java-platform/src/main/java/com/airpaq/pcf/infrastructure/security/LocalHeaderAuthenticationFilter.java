package com.airpaq.pcf.infrastructure.security;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.Arrays;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.filter.OncePerRequestFilter;

public class LocalHeaderAuthenticationFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(
            HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        if (SecurityContextHolder.getContext().getAuthentication() == null) {
            var user = valueOrDefault(request.getHeader("X-User-Id"), "local-user");
            var roles =
                    valueOrDefault(
                            request.getHeader("X-Roles"), "data_submitter,lca_reviewer,admin");
            var authorities =
                    Arrays.stream(roles.split(","))
                            .map(String::trim)
                            .filter(role -> !role.isEmpty())
                            .map(role -> new SimpleGrantedAuthority("ROLE_" + role))
                            .toList();
            SecurityContextHolder.getContext()
                    .setAuthentication(
                            UsernamePasswordAuthenticationToken.authenticated(
                                    user, "N/A", authorities));
        }
        chain.doFilter(request, response);
    }

    private static String valueOrDefault(String value, String fallback) {
        return value == null || value.isBlank() ? fallback : value;
    }
}
