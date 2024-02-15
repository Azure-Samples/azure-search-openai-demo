import { useState } from "react";
import { useQuery } from "react-query";

import styles from "./Eval.module.css";

import EvalSidebar from "../../components/EvalSidebar/EvalSidebar";
import FeedbackItem from "../../components/FeedbackItem/FeedbackItem";
import FeedbackItemDetailed from "../../components/FeedbackItem/FeedbackItemDetailed";
import { Feedback, getFeedbackApi } from "../../api";

export function Component(): JSX.Element {
    const [activeSample, setActiveSample] = useState<Feedback | undefined>(undefined);

    const [filter, setFilter] = useState<string>("all");

    const { data, isLoading, error, isError } = useQuery({
        queryKey: ["getFeedback"],
        queryFn: () => getFeedbackApi(undefined)
    });

    const setActiveSampleId = (id: string) => {
        const newActiveSample: Feedback | undefined = data?.feedbacks.find((sample: Feedback) => sample.id === id);
        setActiveSample(newActiveSample);
    };

    const removeActiveSample = () => {
        setActiveSample(undefined);
    };

    const filteredFeedback = data?.feedbacks.filter(evalItem => {
        if (filter === "all") {
            return true;
        } else if (filter === "good") {
            return evalItem.feedback === "good";
        } else if (filter === "bad") {
            return evalItem.feedback === "bad";
        }
        return false;
    });

    return (
        <div className={styles.layout}>
            <EvalSidebar />
            <section className={styles.mainContent}>
                {isError && <h1>Oh no, something went wrong!</h1>}
                {isLoading ? (
                    <h1>Loading Feedback...</h1>
                ) : activeSample ? (
                    <FeedbackItemDetailed
                        id={activeSample.id}
                        feedback={activeSample.feedback}
                        question={activeSample.question}
                        answer={activeSample.answer}
                        comment={activeSample.comment}
                        removeActiveSample={removeActiveSample}
                    />
                ) : (
                    <>
                        {/* Filter:
                        <label>
                            <select className={styles.feedbackLabel} value={filter} onChange={e => setFilter(e.target.value)}>
                                <option value="all">All</option>
                                <option value="good">Positive</option>
                                <option value="bad">Negative</option>
                            </select>
                        </label> */}
                        {filteredFeedback?.map((evalItem: any) => (
                            <FeedbackItem
                                key={evalItem.id}
                                id={evalItem.id}
                                feedback={evalItem.feedback}
                                question={evalItem.question}
                                answer={evalItem.answer}
                                comment={evalItem.comment}
                                setActiveSample={setActiveSampleId}
                            />
                        ))}
                    </>
                )}
            </section>
        </div>
    );
}
