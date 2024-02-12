import { ChatAppResponse } from "../../api";
import styles from "./FeedbackItem.module.css";
import { Icon } from "@fluentui/react/lib/Icon";

interface Props {
    id: string;
    feedback: string;
    question: string;
    answer: ChatAppResponse;
    comment: string;
    setActiveSample: (sample: string) => void;
}

const FeedbackItem = ({ id, feedback, question, answer, comment, setActiveSample }: Props) => {
    const choice = answer.choices[0];
    const index: number = choice.index;
    const message: string = choice.message.content;
    const context: string[] = choice.context.data_points;
    const session_state: any = choice.session_state;

    return (
        <section className={[styles.feedbackItemContainer, feedback === "good" ? styles.feedbackGood : styles.feedbackBad].join(" ")}>
            <div className={styles.feedbackItem}>
                <span>Feedback</span>
                <p>{feedback === "good" ? <Icon iconName="Like" /> : <Icon iconName="Dislike" />}</p>
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
