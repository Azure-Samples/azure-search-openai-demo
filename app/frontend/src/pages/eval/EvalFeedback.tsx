import { useState, useEffect } from "react";

import { v4 as uuidv4 } from "uuid";

import * as fb from "../../data/feedback.json";
import EvalSidebar from "../../components/EvalSidebar/EvalSidebar";
import FeedbackItem from "../../components/FeedbackItem/FeedbackItem";
import FeedbackItemDetailed from "../../components/FeedbackItem/FeedbackItemDetailed";

import styles from "./Eval.module.css";

const str: string = JSON.stringify(fb);
const evalItems: { default: any[] } = JSON.parse(str);

export function Component(): JSX.Element {
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [data, setData] = useState<any>({ evalItems });
    // const [data, setData] = useState<any>(null);
    const [activeSample, setActiveSample] = useState<any>(null);

    // useEffect(() => {
    //     const fetchData = async () => {
    //         try {
    //             console.log("Fetching Data");
    //             setIsLoading(true);
    //             const response = await fetch("../../data/feedback.jsonl");
    //             const text = await response.text();
    //             const lines = text.split("\n");

    //             const parsedData = lines.map((line: string) => JSON.parse(line));
    //             setData(parsedData);
    //             console.log(parsedData);
    //         } catch (e) {
    //             console.log(e);
    //         }
    //     };

    //     fetchData();
    // }, []);

    

    const setActiveSampleId = (id: string) => {
        const newActiveSample = data.evalItems.default.find((sample: any) => sample.id === id);
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
                    <p>Loading...</p>
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
                        {data.evalItems.default.map((evalItem: any) => (
                            <FeedbackItem
                                key={uuidv4()}
                                id={uuidv4()}
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
