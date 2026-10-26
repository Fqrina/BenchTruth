# Eval results (solver, deterministic)

```
CASE  ACTUAL   EXPECTED RULES FIRED                  OK
-------------------------------------------------------
C01  OFFER    OFFER    R8                           PASS
C02  OFFER    OFFER    R10                          PASS
C03  OFFER    OFFER    R10,R12,R11                  PASS
C04  FIXED    FIXED    R5                           PASS
C05  FIXED    FIXED    R1                           PASS
C06  FIXED    FIXED    R2                           PASS
C07  FIXED    FIXED    R7                           PASS
C08  REFUSE   REFUSE   R15                          PASS
C09  OFFER    OFFER    R10,R13                      PASS
C10  OFFER    OFFER    R10,R12,R11                  PASS
C11  OFFER    OFFER    R10,R12                      PASS
C12  OFFER    OFFER    R9,R14,R16                   PASS
C13  BUILD    BUILD    -                            PASS
C14  OFFER    OFFER    R9                           PASS
C15  OFFER    OFFER    R9,R12,R11                   PASS
C16  OFFER    OFFER    R9                           PASS
C17  OFFER    OFFER    R10                          PASS
C18  FIXED    FIXED    R3                           PASS
C19  BUILD    BUILD    -                            PASS
C20  WARN     WARN     R16                          PASS

20/20 correct verdicts
```

Rules: `ruleset.md`. Golden specs: `eval/golden_specs.json`.
This number measures the solver only -- no LLM calls are made.
