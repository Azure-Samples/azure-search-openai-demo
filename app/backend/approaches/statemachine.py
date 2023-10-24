import types
from approaches.statetypes.statetypeprint import StateTypePrint
from approaches.statetypes.statetypesaveinputtovar import StateTypeSaveInputToVar
from approaches.statetypes.statetypeopenai import StateTypeOpenAI

StateAskForName = "ASK_FOR_NAME"
StateWaitingForName = "WAITING_FOR_NAME"
StateAskForFeeling = "ASK_FOR_FEELING"
StateWaitingForFeeling = "WAITING_FOR_FEELING"
StateEmpathyToFeelings = "EMPATHY_TO_FEELINGS"

FirstState = StateAskForName

States = {}

States[StateAskForName] = StateTypePrint(
    next_state = StateWaitingForName,
    out = "שמי יואב, אני בוט מבוסס בינה מלאכותית שמומחה בעזרה פסיכולוגית מיידית למבוגרים שהיו חשופים לאירועי מלחמה או קרב, בנו אותי חוקרים ומפתחים שמומחים בנושא על סמך ידע מדעי ויכולת טכנולוגית עצומה במיוחד כדי לסייע לך. אמור לי בבקשה מה שמך"
)

States[StateWaitingForName] = StateTypeSaveInputToVar(next_state = StateAskForFeeling, var = "patientName")

States[StateAskForFeeling] = StateTypePrint(
    next_state = StateEmpathyToFeelings,
    out = """שלום {patientName}, ברוך הבא לתהליך ייצוב מיידי, שמטרתו להביא לרגיעה ולהקלה במצוקה פסיכולוגית. תהליך זה עזר לאנשים רבים בעולם. התהליך ייקח כ10-20 דקות, במהלכן אקח אותך דרך השלבים החשובים לעבור תהליך הרגעה ועיבוד. בכל שלב אתה יכול לכתוב לי אם יש לך שאלות או דבר מה שתרצה לשתף אותי בו
"אשמח לדעת ממש בקצרה מה מטריד אותך, ?אני רק צריך לשמוע תיאור קצר מאוד. אתה לא חייב לספר לי? """
)

States[StateEmpathyToFeelings] = StateTypeOpenAI(
    system_prompt = "תן תגובה ממנה הנבדק יבין שהבנת מה הוא אמר, תתייחס באופן אימפטי מאוד בקצרה אל תהיה נועז בתגובה אל תפרש אל תשייך לנבדק רגשות תחושות או מצבים שלא דיווח עליהם, השתדל להיות קשוב ומינימליסטי ולהצמד למה שאמר אבל לא לחזור בצורה טלגרפית",
)