from bodyshield.robot import audit_labels, verifier


def test_verifier_and_label_audit_are_blocked_without_hardware_data():
    assert verifier.main([]) == 2
    assert audit_labels.main([]) == 2

