package org.example.promptlab.global.apiPayload.exception;

import lombok.Getter;
import org.example.promptlab.global.apiPayload.code.BaseErrorCode;

@Getter
public class CustomException extends RuntimeException{

    private final BaseErrorCode code;

    public CustomException(BaseErrorCode errorCode) {
        this.code = errorCode;
    }
}
