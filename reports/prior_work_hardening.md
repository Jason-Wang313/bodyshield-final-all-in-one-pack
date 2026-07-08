# Prior Work Hardening

Status: `verified_scope_locked`

## A. Domain Randomization And Dynamics Randomization

Tobin et al. introduced visual domain randomization for sim-to-real object localization and grasping \cite{tobin2017domainrandomization}. Peng et al. randomized simulator dynamics for robotic control transfer \cite{peng2018dynamicsrandomization}. OpenAI Dactyl and Rubik's Cube results are important domain-randomization and automatic-domain-randomization anchors \cite{openai2018dexterous,openai2019rubiks}. BodyShield must not be sold as "the" alternative to domain randomization. The distinction is narrower: domain randomization samples broad training distributions, while BodyShield searches for the smallest embodiment-control perturbations that break the current policy, repairs against discovered failures, and evaluates held-out shifts under matched budgets.

## B. Embodiment-Aware Policy Guidance

UMI-on-Air uses embodiment-aware guidance to steer embodiment-agnostic visuomotor policies toward feasible deployment modes \cite{gupta2025umionair}. EmbodiSteer performs training-free joint-space guidance for zero-shot cross-embodiment deployment \cite{wang2026embodisteer}. These methods guide execution for a target body. BodyShield is framed as falsify hidden body/control assumptions, repair against discovered failure modes, and validate held-out perturbation families and physical-modification proxies. It does not claim to solve cross-embodiment transfer.

## C. Counterexample-Guided Repair, Falsification, And Safe RL

Counterexample-guided RL and verification-guided falsification use formal or risk-guided search to expose unsafe policy behavior \cite{karunakaran2020counterexampleguided,le2025verificationguided}. BodyShield borrows the falsification-to-repair stance but restricts the search space to embodiment-control perturbations: latency, controller rate, calibration, sensing shift, gripper authority, payload, contact/friction proxies, and compound physical shifts.

## D. Robust MPC, CBF, Reachability, System Identification, And Retuning

MPC-CBF methods enforce safety or feasibility constraints in model-predictive controllers \cite{zeng2021mpccbf}. Online-correction sim-to-real work such as TRANSIC learns from deployment corrections to close sim-to-real gaps \cite{jiang2024transic}. BodyShield is not a replacement for robust control, CBFs, reachability, or system identification. It is a falsification-to-repair layer that identifies which hidden embodiment-control assumption a learned policy uses and compares repair to robust/sysID/domain-randomized baselines under matched budgets.

## E. Benchmark Or Stress-Test Papers

BodyShield is not acceptable as a diagnostic-only benchmark. The main evidence must be before/after repair: BodyBreak finds failures, BodyShield repairs, and held-out perturbation families improve without winning solely by conservative slowdown or refusal.
