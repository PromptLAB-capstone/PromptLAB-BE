package org.example.promptlab.domain.user.entity;

import jakarta.persistence.*;
import lombok.*;
import org.example.promptlab.domain.project.entity.Project;
import org.example.promptlab.global.entity.BaseEntity;

import java.time.LocalDateTime;
import java.util.List;

@Entity
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor(access = AccessLevel.PRIVATE)
@Builder
@Getter
@Table(name = "users")
public class User extends BaseEntity {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "email", unique = true, nullable = false)
    private String email;

    @Column(name = "name", nullable = false)
    private String name;

    @Column(name = "password", nullable = true)
    private String password;

    @Column(name = "profile_image", nullable = true)
    private String profileImage;

    @Column(name = "auth_type", nullable = false)
    @Enumerated(EnumType.STRING)
    private AuthType authType;

    @Column(name = "deleted_at")
    private LocalDateTime deletedAt;

    @OneToMany(mappedBy = "user", cascade = CascadeType.ALL, orphanRemoval = true, fetch = FetchType.LAZY)
    private List<Project> projects;
}
