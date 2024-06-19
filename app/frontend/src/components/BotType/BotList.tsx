import { BotType } from "./BotType";

import styles from "./BotType.module.css";
type BotTypePrompt = {
    type: string;
    prompt : string;
    num : number
}

const DEFAULT_EXAMPLES : BotTypePrompt[] = [
   {
    type : "IT Assistant",
    prompt : "You are an AI IT Assistant",
    num : 1
   } ,
   {
    type : "HR Assistant",
    prompt : "You are an AI HR Assistant",
    num : 2
   },
   {
    type : "Plant Assistant",
    prompt : "You are an AI Plant Assistant",
    num : 3
   } 

];

const GPT4V_EXAMPLES: string[] = [
    "Compare the impact of interest rates and GDP in financial markets.",
    "What is the expected trend for the S&P 500 index over the next five years? Compare it to the past S&P 500 performance",
    "Can you identify any correlation between oil prices and stock market trends?"
];

interface Props {
    onBotClicked: (example:string , id : number) => void;
    useGPT4V?: boolean;
    selected : number
}

export const BotList = ({ onBotClicked, useGPT4V , selected}: Props) => {
    return (
        <ul className={styles.examplesNavList}>
            {(DEFAULT_EXAMPLES).map((question,i) => (
                <li key={i}>
                    <BotType selectedNumber={question.num} selected={question.num==selected} text={question.type} value={question.prompt} onClick={onBotClicked} />
                </li>
            ))}
        </ul>
    );
};
