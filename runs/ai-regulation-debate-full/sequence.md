## Conversation

_Time-ordered exchange between agents: task dispatches, messages, and completions. CC-to-lead traffic is implicit in the primary arrow._

```mermaid
sequenceDiagram
    participant lead
    participant advocate_for
    participant advocate_against
    Note over lead: writes DONE_CRITERIA.md
    Note over lead: creates task: Turn 01 (FOR)
    Note over lead: creates task: Turn 02 (AGAINST)
    Note over lead: creates task: Turn 03 (FOR)
    Note over lead: creates task: Turn 04 (AGAINST)
    Note over lead: creates task: Turn 05 (FOR)
    Note over lead: creates task: Turn 06 (AGAINST)
    Note over lead: creates task: Turn 07 (FOR)
    Note over lead: creates task: Turn 08 (AGAINST)
    Note over lead: creates task: Turn 09 (FOR)
    Note over lead: creates task: Turn 10 (AGAINST)
    lead->>+advocate_for: dispatch t_001
    lead->>+advocate_against: dispatch t_002
    lead->>+advocate_for: dispatch t_003
    lead->>+advocate_against: dispatch t_004
    lead->>+advocate_for: dispatch t_005
    lead->>+advocate_against: dispatch t_006
    lead->>+advocate_for: dispatch t_007
    lead->>+advocate_against: dispatch t_008
    lead->>+advocate_for: dispatch t_009
    lead->>+advocate_against: dispatch t_010
    advocate_for-->>-lead: t_001 done → debate/turn_01_for.md
    advocate_against-->>-lead: t_002 done → debate/turn_02_against.md
    advocate_for-->>-lead: t_003 done → debate/turn_03_for.md
    advocate_against-->>-lead: t_004 done → debate/turn_04_against.md
    advocate_for-->>-lead: t_005 done → debate/turn_05_for.md
    advocate_against-->>-lead: t_006 done → debate/turn_06_against.md
    advocate_for-->>-lead: t_007 done → debate/turn_07_for.md
    advocate_against-->>-lead: t_008 done → debate/turn_08_against.md
    advocate_for-->>-lead: t_009 done → debate/turn_09_for.md
    advocate_against-->>-lead: t_010 done → debate/turn_10_against.md
    Note over lead: finalize()
```
