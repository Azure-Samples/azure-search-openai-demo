import { ChatAppResponse } from "../../api";
import styles from "./FeedbackItem.module.css";
import { IconButton } from "@fluentui/react";

interface Props {
    id: number;
    feedback: string;
    question: string;
    answer: ChatAppResponse;
    comment: string;
    setActiveSample: (sample: number) => void;
}

const FeedbackItem = ({ id, feedback, question, answer, comment, setActiveSample }: Props) => {
    const choice = answer.choices[0];
    const index: number = choice.index;
    const message: string = choice.message.content;
    const context: string[] = choice.context.data_points;
    const session_state: any = choice.session_state;

    return (
        <section className={styles.feedbackItemContainer}>
            <div className={styles.feedbackItem}>
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
                <span>Comment</span>
                <p>{comment}</p>
                <span>Question</span>
                <p>{question}</p>
                <span>Answer</span>
                <p>{message}</p>
            </div>
            <button className={styles.detailsButton} onClick={() => setActiveSample(id)}>
                Details
            </button>
        </section>
    );
};
export default FeedbackItem;