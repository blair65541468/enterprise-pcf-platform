package com.airpaq.pcf.infrastructure.web;

public class DomainException extends RuntimeException {

    private final int status;
    private final Object detail;

    public DomainException(int status, Object detail) {
        super(String.valueOf(detail));
        this.status = status;
        this.detail = detail;
    }

    public int status() {
        return status;
    }

    public Object detail() {
        return detail;
    }

    public static DomainException notFound(String message) {
        return new DomainException(404, message);
    }

    public static DomainException conflict(String message) {
        return new DomainException(409, message);
    }

    public static DomainException unprocessable(Object detail) {
        return new DomainException(422, detail);
    }
}
