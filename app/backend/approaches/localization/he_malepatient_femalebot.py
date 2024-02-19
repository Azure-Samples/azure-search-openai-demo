from approaches.localization.he import choose_annoying_reason_with_distress, exit_after_distress_increased_and_fail_to_connect_to_current, exit_after_distress_increased_and_succeed_to_connect_to_current, exit_after_distress_increased_twice, exit_after_improvement, exit_after_improvement_and_fail_to_connect_to_current, exit_after_improvement_and_succeed_to_connect_to_current, exit_after_no_clear_improvement_and_fail_to_connect_to_current, exit_after_no_clear_improvement_and_succeed_to_connect_to_current, exit_no_clear_improvement, get_video_message, is_connected_to_current_after_improvement, is_connected_to_current_after_no_improvement, should_continue_after_improvement
from approaches.localization.he_malepatient import heMalePatient

heMalePatientFemaleBot = {
    "id": "heMalePatientFemaleBot",
    "parent": heMalePatient["id"],
    "chooseAnnoyingReasonWithMediumDistress": [{"role": "explanationText", "content": choose_annoying_reason_with_distress(is_patient_male=True, is_bot_male=False, is_distress_high=False)}],
    "chooseAnnoyingReasonWithHighDistress": [{"role": "explanationText", "content": choose_annoying_reason_with_distress(is_patient_male=True, is_bot_male=False, is_distress_high=True)}],
    "videoUrl": lambda request_context: get_video_message(request_context, is_patient_male=True, is_bot_male=False),
    "exitAfterDistressIncreasedTwice": exit_after_distress_increased_twice(is_bot_male=False),
    "exitAfterImprovement": exit_after_improvement(is_patient_male=True, is_bot_male=False),
    "exitNoClearImprovement": exit_no_clear_improvement(is_patient_male=True, is_bot_male=False),
    "shouldContinueAfterImprovement": should_continue_after_improvement(is_patient_male=True, is_bot_male=False),
    "isConnectedToCurrentAfterNoImprovement": is_connected_to_current_after_no_improvement(is_patient_male=True, is_bot_male=False),
    "isConnectedToCurrentAfterImprovement": is_connected_to_current_after_improvement(is_patient_male=True, is_bot_male=False),
    "exitAfterDistressIncreasedAndFailToConnectToCurrent": exit_after_distress_increased_and_fail_to_connect_to_current(is_patient_male=True, is_bot_male=False),
    "exitAfterDistressIncreasedAndSucceedToConnectToCurrent": exit_after_distress_increased_and_succeed_to_connect_to_current(is_patient_male=True, is_bot_male=False),
    "exitAfterImprovementAndFailToConnectToCurrent": exit_after_improvement_and_fail_to_connect_to_current(is_patient_male=True, is_bot_male=False),
    "exitAfterImprovementAndSucceedToConnectToCurrent": exit_after_improvement_and_succeed_to_connect_to_current(is_patient_male=True, is_bot_male=False),
    "exitAfterNoClearImprovementAndFailToConnectToCurrent":  exit_after_no_clear_improvement_and_fail_to_connect_to_current(is_patient_male=True, is_bot_male=False),
    "exitAfterNoClearImprovementAndSucceedToConnectToCurrent": exit_after_no_clear_improvement_and_succeed_to_connect_to_current(is_patient_male=True, is_bot_male=False),
}