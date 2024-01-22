from approaches.flow.shared_states import ChatInputNotWait, ConditionedAction, State, StateExit, States, StateStartISP, StateStartPreperation, VariableDistressLevel, VariableFirstDistressLevel, VariableIspPath, chat_input_multiple_options, chat_input_numeric
from approaches.requestcontext import RequestContext

StateGetDistressLevel = "GET_DISTRESS_LEVEL"
StateAskIfToContinueOnLowDistress = "ASK_IF_TO_CONTINUE_ON_LOW_DISTRESS"
StateAskWhatAnnoying = "ASK_WHAT_ANNOYING"
StateGetAnnoyingReason = "GET_ANNOYING_REASON"

States[StateStartPreperation] = State(chat_input=ChatInputNotWait, conditioned_actions=[
    ConditionedAction(condition=None, output="howMuchDistress", next_state=StateGetDistressLevel, condition_description=None)
])

async def get_distress_level(request_context: RequestContext, input: str):
    distress = int(input)
    request_context.save_to_var(VariableDistressLevel, distress)
    request_context.save_to_var(VariableFirstDistressLevel, distress)
States[StateGetDistressLevel] = State(chat_input=chat_input_numeric(0, "0", 10, "10"), action_before=get_distress_level, conditioned_actions=[
    ConditionedAction(condition=lambda request_context, input: 0 <= request_context.get_var(VariableDistressLevel) <= 1, output="noDistressOnStart", next_state=StateAskIfToContinueOnLowDistress, condition_description="רמת המצוקה היא 0 או 1"),
    ConditionedAction(condition=lambda request_context, input: 2 <= request_context.get_var(VariableDistressLevel) <= 10, output=None, next_state=StateAskWhatAnnoying, condition_description="רמת המצוקה היא 2 עד 10"),
    ConditionedAction(condition=None, output="wrongDistressLevel", next_state=StateGetDistressLevel, condition_description=None)
])

States[StateAskIfToContinueOnLowDistress] = State(chat_input=chat_input_multiple_options(["כן", "לא"]), conditioned_actions=[
    ConditionedAction(condition=lambda request_context, input: input.strip() in ("fi", "כן"), output="exitNoDistress", next_state=StateExit, condition_description="המשתמש\ת הקליד\ה 'כן'"),
    ConditionedAction(condition=lambda request_context, input: input.strip() in ("kt", "לא"), output=None, next_state=StateAskWhatAnnoying, condition_description="המשתמש\ת הקליד\ה 'לא'"),
    ConditionedAction(condition=None, output="wrongInputYesNo", next_state=StateAskIfToContinueOnLowDistress, condition_description=None)
])

States[StateAskWhatAnnoying] = State(chat_input=ChatInputNotWait, conditioned_actions=[
    ConditionedAction(condition=lambda request_context, input: request_context.get_var(VariableDistressLevel) < 2, output="chooseAnnoyingReasonWithLowDistress", next_state=StateGetAnnoyingReason, condition_description="רמת מצוקה 0 או 1"),
    ConditionedAction(condition=lambda request_context, input: request_context.get_var(VariableDistressLevel) < 2, output="chooseAnnoyingReasonWithMediumDistress", next_state=StateGetAnnoyingReason, condition_description="רמת מצוקה 2 עד 4"),
    ConditionedAction(condition=None, output="chooseAnnoyingReasonWithHighDistress", next_state=StateGetAnnoyingReason, condition_description="רמת מצוקה גדולה מ-4")
])

async def get_annoying_reason(request_context: RequestContext, input: str):
    if input in ["1", "2", "3", "4", "5"]:
        request_context.save_to_var(VariableIspPath, input)
States[StateGetAnnoyingReason] = State(chat_input=chat_input_numeric(1, "1", 5, "5"), action_before=get_annoying_reason, conditioned_actions=[
    ConditionedAction(condition=lambda request_context, input: request_context.has_var(VariableIspPath), output=None, next_state=StateStartISP, condition_description="נקלטה תשובה בין 1 ל-5"),
    ConditionedAction(condition=None, output="wrongAnnoyingReason", next_state=StateGetAnnoyingReason, condition_description=None)
])
