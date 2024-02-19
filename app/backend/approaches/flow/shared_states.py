from azure.data.tables import UpdateMode
from typing import Callable

from approaches.requestcontext import RequestContext

StateStartIntro = "START_INTRO"
StateStartPreperation = "START_PREPERATION"
StateStartISP = "START_ISP"
StateStartPositiveCognition = "START_POSITIVE_COGNITION"

StateAskIfToExit = "ASK_IF_TO_EXIT"
StateChooseExitText = "CHOOSE_EXIT_TEXT"
StateExit = "EXIT"
StateEndInput = "END_INPUT"

States = {}

VariableClientId = "clientId"
VariableDistressLevel = "prefixByDistressLevel"
VariableExitText = "exitText"
VariableFirstDistressLevel = "firstDistressLevel"
VariableIsBotMale = "isBotMale"
VariableIsPatientMale = "isPatientMale"
VariableIspPath = "ispPath"
VariableIsUserExited = "isUserExited"
VariablePatientName = "patientName"
VariablePrevDistressLevel = "prevDistressLevel"
VariableShouldSaveClientStatus = "shouldSaveClientStatus"
VariableStringsId = "stringsId"
VariableSumDistressLevel = "sumDistressLevel"
VariableVideoIndex = "videoIndex"
VariableWasDistressLevelIncreased = "wasDistressLevelIncreased"
VariableWasDistressLevelIncreasedTwice = "wasDistressLevelIncreasedTwice"

PartitionKey = "DefaultPartition"
DemoClientId = "דמו"
MissingClientId = "כניסה ללא זיהוי משתמש"

ChatInputNotWait = "INTERNAL_PLACEHOLDER_NOT_WAIT"
ChatInputFreeText = { "inputType": "freeText" }
ChatInputDisabled = { "inputType": "disabled" }
def chat_input_multiple_options(options: list[str]):
    return { "inputType": "multiple", "options": options }
def chat_input_numeric(minValue, minLabel, maxValue, maxLabel):
    return { "inputType": "numeric", "control": "text", "minValue": minValue, "minLabel": minLabel, "maxValue": maxValue, "maxLabel": maxLabel }
def chat_input_slider(minValue, minLabel, maxValue, maxLabel):
    return { "inputType": "numeric", "control": "slider", "minValue": minValue, "minLabel": minLabel, "maxValue": maxValue, "maxLabel": maxLabel }

class ConditionedAction:
    def __init__(self, output: str, next_state: str, condition: Callable, condition_description: str, custom_action: Callable = None):
        self.output = output
        self.next_state = next_state
        self.condition = condition
        self.condition_description = condition_description
        self.custom_action = custom_action

class State:
    def __init__(self, conditioned_actions: list[ConditionedAction], chat_input = ChatInputFreeText, action_before: Callable = None):
        self.chat_input = chat_input
        self.conditioned_actions = conditioned_actions,
        self.action_before = action_before

def is_exit_after_distress_increased(request_context, input) -> bool:
    return (
        request_context.get_var(VariableWasDistressLevelIncreasedTwice) or
        (request_context.get_var(VariableWasDistressLevelIncreased) and request_context.get_var(VariableIsUserExited)) or
        request_context.get_var(VariableFirstDistressLevel) <= request_context.get_var(VariableDistressLevel))
def is_exit_after_improvement(request_context, input) -> bool:
    return request_context.get_var(VariableFirstDistressLevel) > request_context.get_var(VariableDistressLevel)
States[StateChooseExitText] = State(chat_input=ChatInputNotWait, conditioned_actions=[
    ConditionedAction(condition=is_exit_after_distress_increased, output="exitTextAfterDistressIncreased", next_state=StateExit, condition_description="שתי החרפות, או שהתמתמש\ת בחר\ה לצאת אחרי החרפה, או שהייתה החרפה בין רמת המצוקה בהתחלה לסוף"),
    ConditionedAction(condition=is_exit_after_improvement, output="exitAfterImprovement", next_state=StateExit, condition_description="המשתמש\ת סיימ\ה שמונה סרטונים וחל שיפור בין רמת המצוקה בהתחלה לסוף"),
    ConditionedAction(condition=None, output="exitNoClearImprovement", next_state=StateExit, condition_description=None)
])

async def update_table_entity(request_context: RequestContext, input):
    if request_context.get_var(VariableShouldSaveClientStatus):
        entity = {
            "PartitionKey": PartitionKey,
            "RowKey": request_context.get_var(VariableClientId),
            "Status": "finished"
        }
        await request_context.app_resources.table_client.update_entity(mode=UpdateMode.REPLACE, entity=entity)
States[StateExit] = State(chat_input=ChatInputNotWait, action_before=update_table_entity, conditioned_actions=[ConditionedAction(condition=None, output=None, next_state=StateEndInput, condition_description=None)])

States[StateEndInput] = State(chat_input=ChatInputDisabled, conditioned_actions=[])