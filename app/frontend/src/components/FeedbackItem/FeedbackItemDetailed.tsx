import { ChatAppResponse } from "../../api";
import styles from "./FeedbackItem.module.css";
import { IconButton } from "@fluentui/react";
import { SupportingContent } from "../SupportingContent";

interface Props {
    id: number;
    feedback: string;
    question: string;
    answer: ChatAppResponse;
    comment: string;
    removeActiveSample: () => void;
}

const FeedbackItemDetailed = ({ id, feedback, question, answer, comment, removeActiveSample }: Props) => {
    const choice = answer.choices[0];
    const index: number = choice.index;
    const message: string = choice.message.content;
    const context: string[] = choice.context.data_points;
    const session_state: any = choice.session_state;

    return (
        <section className={styles.feedbackItemContainer}>
            <IconButton
                style={{ color: "black" }}
                iconProps={{ iconName: "ChevronLeftMed" }}
                title="Back to overview"
                ariaLabel="Back to overview"
                disabled={!answer.choices[0].context.data_points}
                onClick={() => removeActiveSample()}
            />
            <div className={styles.feedbackItem}>
                <span>Feedback</span>
                <p>
                    {feedback === "good" ? (
                        <IconButton
                            style={{ color: "green" }}
                            iconProps={{ iconName: "CheckMark" }}
                            title="Good Feedback"
                            ariaLabel="Good Feedback"
                            disabled={!answer.choices[0].context.thoughts?.length}
                        />
                    ) : (
                        <IconButton
                            style={{ color: "red" }}
                            iconProps={{ iconName: "Cancel" }}
                            title="Bad Feedback"
                            ariaLabel="Bad Feedback"
                            disabled={!answer.choices[0].context.data_points}
                        />
                    )}
                </p>
                <span>Comment</span>
                <p>{comment}</p>
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
export default FeedbackItemDetailed;
