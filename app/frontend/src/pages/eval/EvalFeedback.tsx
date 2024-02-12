import { useState, useEffect } from "react";
import axios from "axios";
import { v4 as uuidv4 } from "uuid";

import * as fb from "../../data/feedback.json";
import EvalSidebar from "../../components/EvalSidebar/EvalSidebar";
import FeedbackItem from "../../components/FeedbackItem/FeedbackItem";
import FeedbackItemDetailed from "../../components/FeedbackItem/FeedbackItemDetailed";

import styles from "./Eval.module.css";

export function Component(): JSX.Element {
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [data, setData] = useState<any>(null);
    const [activeSample, setActiveSample] = useState<any>(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                console.log("Fetching Feedback Data");
                const response = await axios.get("/feedback");
                const jsonData = await response.data;
                const updatedJsonData = await jsonData.feedbacks.map((feedback: any) => ({
                    id: uuidv4(),
                    ...feedback
                }));
                setData(updatedJsonData);
                setIsLoading(false);
            } catch (e) {
                console.log(e);
            }
        };

        fetchData();
    }, []);

    const setActiveSampleId = (id: string) => {
        const newActiveSample = data.find((sample: any) => sample.id === id);
        setActiveSample(newActiveSample);
    };

    const removeActiveSample = () => {
        setActiveSample(null);
    };

    return (
        <div className={styles.layout}>
            <EvalSidebar />
            <section className={styles.mainContent}>
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
                        {data.map((evalItem: any) => (
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
