# ModernizeAI: Impact & Blast-Radius Matrix

This matrix provides quantitative impact assessments for critical proposed change scenarios across the legacy architecture.

## Scenario: Modifications to `VETS` (DatabaseTable)
- **Target Entity**: `VETS` (DatabaseTable)
- **Risk Classification**: **LOW RISK**
- **Direct & Transitive Blast Radius**: 2 components (2 Upstream, 0 Downstream).

| Impacted Component | Direction | Hop Distance | Relationship | Source Code Citation |
| :--- | :--- | :---: | :--- | :--- |
| `spring-framework-petclinic_App` | Upstream (Caller/Reader) | 1 | `DEPENDS_ON` | `data/_workspaces/spring-framework-petclinic:1` |
| `JdbcVetRepositoryImpl` | Upstream (Caller/Reader) | 1 | `READS_FROM` | `src/main/java/org/springframework/samples/petclinic/repository/jdbc/JdbcVetRepositoryImpl.java:45` |

## Scenario: Modifications to `SPECIALTIES` (DatabaseTable)
- **Target Entity**: `SPECIALTIES` (DatabaseTable)
- **Risk Classification**: **LOW RISK**
- **Direct & Transitive Blast Radius**: 2 components (2 Upstream, 0 Downstream).

| Impacted Component | Direction | Hop Distance | Relationship | Source Code Citation |
| :--- | :--- | :---: | :--- | :--- |
| `spring-framework-petclinic_App` | Upstream (Caller/Reader) | 1 | `DEPENDS_ON` | `data/_workspaces/spring-framework-petclinic:1` |
| `JdbcVetRepositoryImpl` | Upstream (Caller/Reader) | 1 | `READS_FROM` | `src/main/java/org/springframework/samples/petclinic/repository/jdbc/JdbcVetRepositoryImpl.java:45` |

## Scenario: Modifications to `VET_SPECIALTIES` (DatabaseTable)
- **Target Entity**: `VET_SPECIALTIES` (DatabaseTable)
- **Risk Classification**: **LOW RISK**
- **Direct & Transitive Blast Radius**: 2 components (2 Upstream, 0 Downstream).

| Impacted Component | Direction | Hop Distance | Relationship | Source Code Citation |
| :--- | :--- | :---: | :--- | :--- |
| `spring-framework-petclinic_App` | Upstream (Caller/Reader) | 1 | `DEPENDS_ON` | `data/_workspaces/spring-framework-petclinic:1` |
| `JdbcVetRepositoryImpl` | Upstream (Caller/Reader) | 1 | `READS_FROM` | `src/main/java/org/springframework/samples/petclinic/repository/jdbc/JdbcVetRepositoryImpl.java:45` |

## Scenario: Modifications to `TYPES` (DatabaseTable)
- **Target Entity**: `TYPES` (DatabaseTable)
- **Risk Classification**: **LOW RISK**
- **Direct & Transitive Blast Radius**: 3 components (3 Upstream, 0 Downstream).

| Impacted Component | Direction | Hop Distance | Relationship | Source Code Citation |
| :--- | :--- | :---: | :--- | :--- |
| `spring-framework-petclinic_App` | Upstream (Caller/Reader) | 1 | `DEPENDS_ON` | `data/_workspaces/spring-framework-petclinic:1` |
| `JdbcOwnerRepositoryImpl` | Upstream (Caller/Reader) | 1 | `READS_FROM` | `src/main/java/org/springframework/samples/petclinic/repository/jdbc/JdbcOwnerRepositoryImpl.java:48` |
| `JdbcPetRepositoryImpl` | Upstream (Caller/Reader) | 1 | `READS_FROM` | `src/main/java/org/springframework/samples/petclinic/repository/jdbc/JdbcPetRepositoryImpl.java:45` |


---
*Generated dynamically by ModernizeAI Hybrid Agentic Graph-RAG Knowledge Fabric.*
