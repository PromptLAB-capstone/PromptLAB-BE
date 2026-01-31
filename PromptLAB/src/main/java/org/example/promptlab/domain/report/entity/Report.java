package org.example.promptlab.domain.report.entity;

import io.hypersistence.utils.hibernate.type.json.JsonBinaryType;
import jakarta.persistence.*;
import lombok.*;
import org.example.promptlab.domain.prompt.entity.Prompt;
import org.example.promptlab.global.entity.BaseEntity;
import org.hibernate.annotations.Type;

import java.time.LocalDateTime;
import java.util.Map;

@Entity
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor(access = AccessLevel.PRIVATE)
@Builder
@Getter
@Table(name = "report")
public class Report extends BaseEntity {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "report_name", nullable = true)
    private String name;

    @Type(JsonBinaryType.class)
    @Column(name = "report_data", columnDefinition = "jsonb")
    private Map<String, Object> data;

    @Column(name = "auth_type", nullable = false)
    @Enumerated(EnumType.STRING)
    private ReportType reportType;

    @Column(name = "deleted_at")
    private LocalDateTime deletedAt;

    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "prompt_id", nullable = false)
    private Prompt prompt;
}
