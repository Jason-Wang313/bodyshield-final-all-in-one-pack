# Related Work Hardening

Status: `primary_source_anchored_nonhardware_scope`

| bucket | primary source | URL | prior focus | BodyShield distinction |
|---|---|---|---|---|
| domain_randomization | Tobin et al. / OpenAI ADR / Muratore review | https://arxiv.org/abs/1703.06907 | Broad randomized training distribution. | BodyShield actively searches for discovered breaking body/control perturbations before repair. |
| cross_embodiment | Open X-Embodiment / RT-X | https://arxiv.org/abs/2310.08864 | Large cross-robot datasets and RT-X models. | BodyShield audits and repairs hidden body assumptions for scoped policies. |
| xmop | XMoP | https://arxiv.org/abs/2409.15585 | Cross-embodiment neural motion planning. | BodyShield is a falsification-to-repair layer rather than a planner trained across embodiments. |
| umi_on_air | UMI-on-Air | https://arxiv.org/abs/2510.02614 | Embodiment-aware guidance for embodiment-agnostic visuomotor policies. | BodyShield measures which hidden body/control assumption breaks a deployed policy. |
| embodisteer | EmbodiSteer | https://arxiv.org/abs/2606.12965 | Joint-space guidance for embodiment-aware deployment. | BodyShield reports breaking perturbations, repair, and held-out tests without claiming foundation generality. |
| counterexample_guided | Symbolic-geometric action abstraction repair | https://arxiv.org/abs/2105.06537 | Repairs symbolic/geometric action abstractions from observations. | BodyShield targets continuous embodiment-control perturbations and oracle feasibility. |
| safe_rl_falsification | Verification-guided falsification for safe RL | https://arxiv.org/abs/2506.03469 | Model checking and risk-guided falsification. | BodyShield is robot embodiment-control falsification plus repair. |
| robust_mpc_cbf | MPC-CBF / reachability literature | https://github.com/HybridRobotics/MPC-CBF | Safety filtering and robust control. | BodyShield identifies actual hidden assumptions and compares robust baselines under budget. |
| human_effect_priors | VRB / ViPRA | https://arxiv.org/abs/2304.08488 | Human-video affordance and video-action priors. | Included only as a stress-test family, not the headline novelty. |

Do not use this audit to claim broad superiority over these systems. Its purpose
is to prevent novelty collapse by making the mechanism boundary explicit.
