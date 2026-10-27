import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from joint.joint_program import (
    ConnectionMode,
    JointError,
    JointErrorCode,
    JointProgram,
    MoldContract,
    MoldStage,
    demo_contracts,
)


def test_valid_tmb_checks_two_boundaries_and_whole_configuration():
    joint = JointProgram()
    spec = joint.assemble(demo_contracts(), mode=ConnectionMode.TMB)
    assert spec.valid
    assert len(spec.boundaries) == 2
    assert all(boundary.passed for boundary in spec.boundaries)
    exported = joint.export(spec)
    assert exported["mode"] == "TMB"
    assert exported["valid"] is True


def test_tmb_rejects_missing_middle_to_bottom_field():
    top, middle, bottom = demo_contracts()
    broken_bottom = MoldContract(
        mold_id=bottom.mold_id,
        stage=bottom.stage,
        version=bottom.version,
        inputs=bottom.inputs + ("not_provided",),
        required_inputs=("process_plan", "not_provided"),
        outputs=bottom.outputs,
    )
    spec = JointProgram().assemble((top, middle, broken_bottom))
    assert not spec.valid
    assert any("not_provided" in issue for issue in spec.validation_issues)
    assert spec.boundaries[1].missing == ("not_provided",)


def test_wrong_order_is_reported_not_auto_corrected():
    top, middle, bottom = demo_contracts()
    spec = JointProgram().assemble((middle, top, bottom), mode=ConnectionMode.TMB)
    assert not spec.valid
    assert any("stage order mismatch" in issue for issue in spec.validation_issues)
    assert tuple(m.stage for m in spec.molds) == (MoldStage.MIDDLE, MoldStage.TOP, MoldStage.BOTTOM)


def test_tm_mode_checks_top_middle_only():
    top, middle, _ = demo_contracts()
    spec = JointProgram().assemble((top, middle), mode=ConnectionMode.TM)
    assert spec.valid
    assert len(spec.boundaries) == 1


def test_mb_mode_checks_middle_bottom_only():
    _, middle, bottom = demo_contracts()
    spec = JointProgram().assemble((middle, bottom), mode=ConnectionMode.MB)
    assert spec.valid
    assert len(spec.boundaries) == 1


def test_missing_external_top_input_fails_whole_configuration():
    top, middle, bottom = demo_contracts()
    spec = JointProgram().assemble(
        (top, middle, bottom),
        mode=ConnectionMode.TMB,
        external_inputs=("other_input",),
    )
    assert not spec.valid
    assert any("external inputs missing" in issue for issue in spec.validation_issues)


def test_expected_outputs_are_checked():
    spec = JointProgram().assemble(
        demo_contracts(),
        mode=ConnectionMode.TMB,
        expected_outputs=("result", "trace"),
    )
    assert not spec.valid
    assert any("trace" in issue for issue in spec.validation_issues)


def test_disabled_mold_fails():
    top, middle, bottom = demo_contracts()
    disabled_middle = MoldContract(
        mold_id=middle.mold_id,
        stage=middle.stage,
        version=middle.version,
        inputs=middle.inputs,
        required_inputs=middle.required_inputs,
        outputs=middle.outputs,
        enabled=False,
    )
    spec = JointProgram().assemble((top, disabled_middle, bottom))
    assert not spec.valid
    assert any("disabled" in issue for issue in spec.validation_issues)


def test_contract_rejects_required_input_not_in_inputs():
    with pytest.raises(ValueError, match="subset"):
        MoldContract(
            mold_id="broken",
            stage=MoldStage.TOP,
            version="0.1",
            inputs=("user_input",),
            required_inputs=("missing",),
            outputs=("goal",),
        )


def test_empty_mold_sequence_is_invalid_request():
    with pytest.raises(JointError) as exc:
        JointProgram().assemble(())
    assert exc.value.code == JointErrorCode.INVALID_REQUEST


def test_export_refuses_invalid_assembly():
    top, middle, bottom = demo_contracts()
    broken_bottom = MoldContract(
        mold_id=bottom.mold_id,
        stage=bottom.stage,
        version=bottom.version,
        inputs=bottom.inputs + ("not_provided",),
        required_inputs=("not_provided",),
        outputs=bottom.outputs,
    )
    spec = JointProgram().assemble((top, middle, broken_bottom))
    with pytest.raises(JointError) as exc:
        JointProgram().export(spec)
    assert exc.value.code == JointErrorCode.CONTRACT_VIOLATION
