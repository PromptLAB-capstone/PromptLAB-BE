package org.example.promptlab.domain.prompt.entity;

import jakarta.persistence.*;
import lombok.*;
import org.example.promptlab.domain.project.entity.Project;
import org.example.promptlab.domain.report.entity.Report;
import org.example.promptlab.global.entity.BaseEntity;

@Entity
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor(access = AccessLevel.PRIVATE)
@Builder
@Getter
@Table(name = "prompt")
public class Prompt extends BaseEntity {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "version", nullable = true)
    private String version;

    @Column(name = "prompt_data", nullable = true)
    private String content;

    @Column(name = "auth_type", nullable = false)
    @Enumerated(EnumType.STRING)
    private Category category;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "project_id", nullable = false)
    private Project project;

    @OneToOne(mappedBy = "prompt", cascade = CascadeType.ALL, orphanRemoval = true, fetch = FetchType.LAZY)
    private Report report;
}
