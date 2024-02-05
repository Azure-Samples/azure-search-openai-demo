import { ChatAppResponse } from "../../api";
import styles from "./EvalItem.module.css";
import { IconButton } from "@fluentui/react";
import { SupportingContent } from "../SupportingContent";

interface Props {
    id: number;
    feedback: string;
    question: string;
    answer: ChatAppResponse;
    removeActiveSample: () => void;
}

const EvalItemDetailed = ({ id, feedback, question, answer, removeActiveSample }: Props) => {
    const choice = answer.choices[0];
    const index: number = choice.index;
    const message: string = choice.message.content;
    const context: string[] = choice.context.data_points;
    const session_state: any = choice.session_state;

    return (
        <section className={styles.evalItemContainer}>
            <IconButton
                style={{ color: "black" }}
                iconProps={{ iconName: "ChevronLeftMed" }}
                title="Show supporting content"
                ariaLabel="Show supporting content"
                disabled={!answer.choices[0].context.data_points}
                onClick={() => removeActiveSample()}
            />
            <div className={styles.evalItem}>
                <span>Feedback</span>
                <p>
                    {feedback === "good" ? (
                        <IconButton
                            style={{ color: "green" }}
                            iconProps={{ iconName: "CheckMark" }}
                            title="Show thought process"
                            ariaLabel="Show thought process"
                            disabled={!answer.choices[0].context.thoughts?.length}
                        />
                    ) : (
                        <IconButton
                            style={{ color: "red" }}
                            iconProps={{ iconName: "Cancel" }}
                            title="Show supporting content"
                            ariaLabel="Show supporting content"
                            disabled={!answer.choices[0].context.data_points}
                        />
                    )}
                </p>
                <span>Question</span>
                <p>{question}</p>
                <span>Answer</span>
                <p>{message}</p>
                {/* <h3>{context}</h3> */}
                <span>Context</span>
                <SupportingContent supportingContent={context} />
            </div>
        </section>
    );
};
export default EvalItemDetailed;
