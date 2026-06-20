FROM maven:3.9.11-eclipse-temurin-21 AS build
WORKDIR /workspace
COPY pom.xml ./
RUN mvn -q -DskipTests dependency:go-offline
COPY src ./src
RUN mvn -q -DskipTests package

FROM eclipse-temurin:21.0.7_6-jre-ubi9-minimal
RUN microdnf install -y shadow-utils && microdnf clean all \
    && groupadd --system pcf && useradd --system --gid pcf --home-dir /app pcf
WORKDIR /app
COPY --from=build /workspace/target/pcf-platform-*.jar app.jar
USER pcf
EXPOSE 8080
ENTRYPOINT ["java", "-XX:MaxRAMPercentage=75", "-jar", "/app/app.jar"]
