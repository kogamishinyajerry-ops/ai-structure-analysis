# P1-04a — RAG Corpus Audit

> Generated: 2026-04-18T14:10:08+00:00
> ADR-008 N-2: P1-04 split into 04a (audit) + 04b (build). This report is the audit.

## 1. Headline numbers

- Corpus size: **8** entries (DoD target: 8000, current fill: **0.1%**)
- Top-5 recall on 15 realistic P1 queries: **20.0%**
- PRD §3.1 DoD target: ≥80% top-5 recall on 8000+ entries. Pass: **NO**
- Docs with CalculiX *-keyword syntax: **0.0%** (0/8)

## 2. Corpus structural snapshot

- SQLite path: `/Users/Zhuanz/20260408 AI StructureAnalysis/data/knowledge_base/chroma.sqlite3`
- Collections: 1
  - `fea_knowledge` (dim=384)
- Embeddings: 8
- Doc length: min=49, avg=65.0, max=86 chars

### Sample docs (first 5)

1. 梁单元理论: Euler-Bernoulli梁理论假设横截面保持平面且垂直于中性轴。弯曲应力公式σ = My/I,其中M为弯矩,y为距中性轴距离,I为截面惯性矩。
2. von Mises应力: 用于屈服判据的等效应力,公式为σ_vm = √[(S1-S2)² + (S2-S3)² + (S3-S1)²]/2,其中S1,S2,S3为主应力。
3. 位移边界条件: 在有限元分析中,位移边界条件用于约束模型刚体位移。常见类型包括固定约束、简支约束、对称约束等。
4. 收敛准则: 有限元求解的收敛准则通常包括力准则和位移准则。力准则检查残差力,位移准则检查位移增量。
5. 单元类型选择: 实体单元(C3D8,C3D4)适用于三维应力分析,壳单元(S4,S3)适用于薄壁结构,梁单元(B31,B32)适用于细长构件。

## 3. Content-pattern audit

| Pattern | Matches | % of corpus |
|---|---|---|
| contains_calculix_keyword_star | 0 | 0.0% |
| contains_element_code | 1 | 12.5% |
| contains_error_phrase | 0 | 0.0% |
| contains_fix_phrase | 0 | 0.0% |
| contains_english | 3 | 37.5% |
| contains_chinese | 8 | 100.0% |

## 4. Recall battery — per-query verdicts

| ID | Domain | Query | Answered in top-5 |
|---|---|---|---|
| Q-01 | element_choice | C3D8 element predicts too stiff bending; how to fix shear locking? | ❌ |
| Q-02 | element_choice | Best element type for pure bending cantilever in CalculiX? | ❌ |
| Q-03 | element_syntax | CalculiX T3D2 truss element syntax with axial stress output | ❌ |
| Q-04 | stress_concentration | Peterson stress concentration factor Kt for plate with circular hole | ✅ |
| Q-05 | fault_syntax | CalculiX *ERROR in input file: unknown keyword *CLAOD | ❌ |
| Q-06 | fault_timestep | time increment required is less than the minimum — how to fix? | ❌ |
| Q-07 | fault_convergence | Residual divergence after maximum iterations in non-linear static | ❌ |
| Q-08 | fault_mesh | Negative Jacobian element in CalculiX mesh | ❌ |
| Q-09 | geometry | FreeCAD export to STEP watertight check before meshing | ❌ |
| Q-10 | bc | Cantilever fixed end boundary condition in CalculiX *BOUNDARY syntax | ❌ |
| Q-11 | material | Steel linear elastic E=210 GPa nu=0.3 CalculiX *MATERIAL block | ❌ |
| Q-12 | loads | CalculiX concentrated force CLOAD on node set syntax | ❌ |
| Q-13 | postprocessing | Extract von Mises stress from CalculiX FRD file | ✅ |
| Q-14 | reviewer_policy | How many Newton iterations should converge a linear elastic static job | ✅ |
| Q-15 | surrogate | FNO neural operator vs CalculiX ground truth validation threshold | ❌ |

## 5. Per-domain breakdown

| Domain | Queries | Answered | Recall |
|---|---|---|---|
| bc | 1 | 0 | 0.0% |
| element_choice | 2 | 0 | 0.0% |
| element_syntax | 1 | 0 | 0.0% |
| fault_convergence | 1 | 0 | 0.0% |
| fault_mesh | 1 | 0 | 0.0% |
| fault_syntax | 1 | 0 | 0.0% |
| fault_timestep | 1 | 0 | 0.0% |
| geometry | 1 | 0 | 0.0% |
| loads | 1 | 0 | 0.0% |
| material | 1 | 0 | 0.0% |
| postprocessing | 1 | 1 | 100.0% |
| reviewer_policy | 1 | 1 | 100.0% |
| stress_concentration | 1 | 1 | 100.0% |
| surrogate | 1 | 0 | 0.0% |

## 6. Strategic recommendation for P1-04b

**Verdict: SCRATCH-REBUILD, do not supplement.** The 8-entry corpus is 0.1% of DoD and covers only high-level theory prose; it carries no .inp syntax examples, no error→fix patterns, and no code-context keyword coverage necessary for Reviewer self-heal.

Proposed sources for 04b (≥8000 target):

1. **CalculiX documentation + examples** — `ccx_2.21.pdf` + the 45+ canonical example decks in the CalculiX source tree. Chunk per keyword + per example, yielding roughly 1500 entries.
2. **CalculiX users mailing-list archive** — 20+ years of Q&A threads. Each thread can be distilled to a (question, fix) pair. Realistic yield: 3000-4000 entries.
3. **FEniCS demo gallery** — FEniCS code + variational-form notes. Relevant because ADR-002 declares FEniCS the secondary solver. Yield: 500-800.
4. **Our own runs corpus** — manifest.yaml + fault_class traces from P1-02 hot-smoke onwards, indexed as (inp snippet, ccx message, fault_class, fix) records. This is the ADR-004-native evidence and should grow organically as P1 proceeds.
5. **Stack Overflow / engineering forums** — finite-element tag, CalculiX/ABAQUS-compatible questions. Yield: 500-1500.

Chunking strategy: 300-500 character windows with 50-char overlap. Embed each with multilingual BGE-M3 (768-dim) rather than the current 384-dim MiniLM, because bilingual (EN/ZH) queries are already evident in the P1-03 diagnostic report.

Relevance oracle for 04b regression: reuse this audit's 15-query battery as the minimum bar, and extend to 50 queries before 04b closes.

## 7. Traceability

- PRD v0.2 §3.1 — RAG DoD (≥8000 entries, top-5 ≥80%)
- ADR-008 N-2 — P1-04 split into audit (this) + build
- ADR-004 — fault_class list drove half the query battery
- Golden samples GS-001/002/003 drove the other half

*Generated by scripts/p1_04a_rag_audit.py*
