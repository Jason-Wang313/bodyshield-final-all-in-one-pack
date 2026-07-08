from bodyshield.sim.validators import validate_trial
from bodyshield.perturbations import Perturbation
from bodyshield.policies import default_policies
from bodyshield.sim import ROBOTS, TASKS, trial_records


def test_sim_validator_accepts_generated_trial_record():
    record = trial_records(default_policies()["nominal"], TASKS[0], ROBOTS[0], Perturbation(), n_trials=1, seed=3)[0]
    assert validate_trial(record) is None
