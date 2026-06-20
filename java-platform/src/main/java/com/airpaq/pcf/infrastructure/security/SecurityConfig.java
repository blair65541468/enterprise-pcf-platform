package com.airpaq.pcf.infrastructure.security;

import com.airpaq.pcf.infrastructure.config.PcfProperties;
import org.springframework.boot.autoconfigure.condition.ConditionalOnWebApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.oauth2.server.resource.web.authentication.BearerTokenAuthenticationFilter;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
@EnableMethodSecurity
@ConditionalOnWebApplication(type = ConditionalOnWebApplication.Type.SERVLET)
public class SecurityConfig {

    @Bean
    SecurityFilterChain securityFilterChain(HttpSecurity http, PcfProperties properties)
            throws Exception {
        http.csrf(csrf -> csrf.disable())
                .sessionManagement(
                        session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(
                        requests ->
                                requests.requestMatchers(
                                                "/health/**",
                                                "/metrics",
                                                "/docs/**",
                                                "/swagger-ui/**",
                                                "/openapi.json")
                                        .permitAll()
                                        .anyRequest()
                                        .authenticated());

        var issuer = System.getenv("OIDC_ISSUER");
        if (issuer != null && !issuer.isBlank()) {
            http.oauth2ResourceServer(oauth -> oauth.jwt(Customizer.withDefaults()));
        } else if (properties.localAuthEnabled()) {
            http.addFilterBefore(
                    new LocalHeaderAuthenticationFilter(), BearerTokenAuthenticationFilter.class);
        }
        return http.build();
    }
}
