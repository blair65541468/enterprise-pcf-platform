package com.airpaq.pcf.calculations.infrastructure.messaging;

import org.springframework.amqp.core.Binding;
import org.springframework.amqp.core.BindingBuilder;
import org.springframework.amqp.core.DirectExchange;
import org.springframework.amqp.core.Queue;
import org.springframework.amqp.core.QueueBuilder;
import org.springframework.amqp.rabbit.config.SimpleRabbitListenerContainerFactory;
import org.springframework.amqp.rabbit.connection.ConnectionFactory;
import org.springframework.amqp.support.converter.JacksonJsonMessageConverter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class RabbitTopology {

    public static final String EXCHANGE = "pcf.calculation";
    public static final String ROUTING_KEY = "calculation.requested";
    public static final String QUEUE = "pcf.calculation.execute.v1";
    public static final String DEAD_EXCHANGE = "pcf.calculation.dlx";
    public static final String DEAD_QUEUE = "pcf.calculation.dead.v1";

    @Bean
    DirectExchange calculationExchange() {
        return new DirectExchange(EXCHANGE, true, false);
    }

    @Bean
    DirectExchange calculationDeadExchange() {
        return new DirectExchange(DEAD_EXCHANGE, true, false);
    }

    @Bean
    Queue calculationQueue() {
        return QueueBuilder.durable(QUEUE)
                .deadLetterExchange(DEAD_EXCHANGE)
                .deadLetterRoutingKey(ROUTING_KEY)
                .build();
    }

    @Bean
    Queue calculationDeadQueue() {
        return QueueBuilder.durable(DEAD_QUEUE).build();
    }

    @Bean
    Binding calculationBinding(Queue calculationQueue, DirectExchange calculationExchange) {
        return BindingBuilder.bind(calculationQueue).to(calculationExchange).with(ROUTING_KEY);
    }

    @Bean
    Binding calculationDeadBinding(
            Queue calculationDeadQueue, DirectExchange calculationDeadExchange) {
        return BindingBuilder.bind(calculationDeadQueue)
                .to(calculationDeadExchange)
                .with(ROUTING_KEY);
    }

    @Bean
    JacksonJsonMessageConverter rabbitMessageConverter() {
        return new JacksonJsonMessageConverter();
    }

    @Bean
    SimpleRabbitListenerContainerFactory rabbitListenerContainerFactory(
            ConnectionFactory connectionFactory, JacksonJsonMessageConverter converter) {
        var factory = new SimpleRabbitListenerContainerFactory();
        factory.setConnectionFactory(connectionFactory);
        factory.setMessageConverter(converter);
        factory.setDefaultRequeueRejected(false);
        factory.setPrefetchCount(1);
        return factory;
    }
}
